package com.soa.tuition.service;

import com.soa.tuition.config.RabbitMQConfig;
import com.soa.tuition.dto.OtpGenerateRequest;
import com.soa.tuition.dto.OtpGenerateResponse;
import com.soa.tuition.dto.OtpVerifyRequest;
import com.soa.tuition.dto.StudentResponse;
import com.soa.tuition.entity.OtpRecord;
import com.soa.tuition.entity.TuitionInvoice;
import com.soa.tuition.exception.AppException;
import com.soa.tuition.repository.OtpRepository;
import com.soa.tuition.repository.TuitionInvoiceRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.security.SecureRandom;
import java.text.NumberFormat;
import java.time.Duration;
import java.time.Instant;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;

@Service
public class OtpService {

    private static final Logger log = LoggerFactory.getLogger(OtpService.class);
    private final OtpRepository otpRepository;
    private final TuitionInvoiceRepository invoiceRepository;
    private final RabbitTemplate rabbitTemplate;
    private final StudentService studentService;
    private final SecureRandom random = new SecureRandom();

    public OtpService(OtpRepository otpRepository,
                      TuitionInvoiceRepository invoiceRepository,
                      RabbitTemplate rabbitTemplate,
                      StudentService studentService) {
        this.otpRepository = otpRepository;
        this.invoiceRepository = invoiceRepository;
        this.rabbitTemplate = rabbitTemplate;
        this.studentService = studentService;
    }

    @Transactional
    public OtpGenerateResponse generateOtp(OtpGenerateRequest req) {
        if (req.getStudentCode() == null || req.getStudentCode().trim().isBlank()) {
            throw new AppException(HttpStatus.BAD_REQUEST, "STUDENT_CODE_REQUIRED",
                    "Mã số sinh viên (student_code) không được để trống khi yêu cầu mã OTP thanh toán.");
        }
        if (req.getEmail() == null || req.getEmail().trim().isBlank()) {
            throw new AppException(HttpStatus.BAD_REQUEST, "EMAIL_REQUIRED",
                    "Email người nộp tiền (email) không được để trống khi yêu cầu mã OTP thanh toán.");
        }

        String cleanCode = req.getStudentCode().trim().toUpperCase();
        String cleanEmail = req.getEmail().trim();

        // 0. Xác thực người nộp tiền có tài khoản ngân hàng trong hệ thống hay không
        studentService.findUserIdByEmail(cleanEmail);

        // 1. Kiểm tra sinh viên và hóa đơn học phí có tồn tại hay không
        TuitionInvoice invoice = invoiceRepository.findFirstByStudent_StudentCodeOrderByTermDesc(cleanCode)
                .orElseThrow(() -> new AppException(HttpStatus.NOT_FOUND, "STUDENT_NOT_FOUND",
                        "Không tìm thấy sinh viên hoặc khoản học phí cho MSSV: " + cleanCode));

        // 2. Chặn tạo OTP nếu sinh viên đã đóng học phí rồi
        if ("PAID".equalsIgnoreCase(invoice.getStatus())) {
            throw new AppException(HttpStatus.CONFLICT, "ALREADY_PAID",
                    "Khoản học phí của sinh viên " + cleanCode + " (học kỳ " + invoice.getTerm() + ") đã được thanh toán hoàn tất. Không thể sinh mã OTP để thanh toán lại!");
        }

        // 3. Kiểm tra số tiền học phí nhập vào: Bắt buộc phải khớp chính xác với học phí cần nộp
        if (req.getAmount() == null || req.getAmount() <= 0) {
            throw new AppException(HttpStatus.BAD_REQUEST, "INVALID_AMOUNT",
                    "Số tiền học phí không hợp lệ.");
        }

        if (!Objects.equals(invoice.getAmount(), req.getAmount())) {
            NumberFormat formatter = NumberFormat.getInstance(new Locale("vi", "VN"));
            throw new AppException(HttpStatus.BAD_REQUEST, "AMOUNT_MISMATCH",
                    String.format("Số tiền thanh toán (%s đ) không khớp với số tiền học phí thực tế của sinh viên %s (%s đ)!",
                            formatter.format(req.getAmount()), cleanCode, formatter.format(invoice.getAmount())));
        }

        // 4. Sinh OTP 6 chữ số ngẫu nhiên
        int number = 100000 + random.nextInt(900000);
        String otpCode = String.valueOf(number);
        Instant expiresAt = Instant.now().plus(Duration.ofMinutes(5));

        OtpRecord record = new OtpRecord(
                req.getEmail().trim(),
                cleanCode,
                req.getAmount(),
                otpCode,
                expiresAt
        );
        otpRepository.save(record);

        log.info("[OTP GENERATED] Email: {}, StudentCode: {}, Amount: {}, Expires at: {}",
                req.getEmail(), cleanCode, req.getAmount(), expiresAt);

        // 5. Publish event lên RabbitMQ để Notification worker gửi email
        publishOtpRequestedEvent(req, invoice, otpCode, expiresAt);

        return new OtpGenerateResponse(
                "Mã OTP đã được tạo và gửi thành công tới " + req.getEmail().trim(),
                req.getEmail().trim(),
                otpCode,
                expiresAt
        );
    }

    private void publishOtpRequestedEvent(OtpGenerateRequest req, TuitionInvoice invoice, String otpCode, Instant expiresAt) {
        try {
            String payerName = (req.getPayerName() != null && !req.getPayerName().isBlank())
                    ? req.getPayerName().trim()
                    : req.getEmail().split("@")[0];

            Map<String, Object> event = new HashMap<>();
            event.put("event_id", UUID.randomUUID().toString());
            event.put("type", "otp.requested");
            event.put("to", req.getEmail().trim());
            event.put("payer_name", payerName);
            event.put("student_name", invoice.getStudent().getFullName());
            event.put("student_code", invoice.getStudent().getStudentCode());
            event.put("term", invoice.getTerm());
            event.put("amount", invoice.getAmount());
            event.put("otp", otpCode);
            event.put("payment_id", UUID.randomUUID().toString());
            event.put("expires_at", expiresAt.toString());

            rabbitTemplate.convertAndSend(RabbitMQConfig.NOTIFICATIONS_QUEUE, event);
            log.info("[OTP EVENT PUBLISHED] Queue={} Email={} StudentCode={}",
                    RabbitMQConfig.NOTIFICATIONS_QUEUE, req.getEmail(), invoice.getStudent().getStudentCode());
        } catch (Exception e) {
            // Không để lỗi RabbitMQ chặn việc tạo OTP thành công
            log.warn("[OTP EVENT PUBLISH FAILED] Email={} Error={}", req.getEmail(), e.getMessage());
        }
    }

    @Transactional
    public StudentResponse verifyOtp(OtpVerifyRequest req) {
        String cleanOtp = req.getOtp().trim();
        OtpRecord record = otpRepository.findFirstByOtpCodeAndUsedFalseOrderByCreatedAtDesc(cleanOtp)
                .orElseThrow(() -> new AppException(HttpStatus.UNPROCESSABLE_ENTITY, "INVALID_OTP", "Mã OTP không chính xác hoặc đã được sử dụng."));

        if (Instant.now().isAfter(record.getExpiresAt())) {
            throw new AppException(HttpStatus.UNPROCESSABLE_ENTITY, "OTP_EXPIRED", "Mã OTP đã hết hạn (chỉ có hiệu lực trong 5 phút).");
        }

        if (req.getEmail() != null && !req.getEmail().isBlank()) {
            if (!record.getEmail().equalsIgnoreCase(req.getEmail().trim())) {
                throw new AppException(HttpStatus.UNPROCESSABLE_ENTITY, "EMAIL_MISMATCH",
                        "Mã OTP không khớp với địa chỉ email xác thực.");
            }
        }

        record.setUsed(true);
        otpRepository.save(record);
        log.info("[OTP VERIFIED SUCCESS] Email: {}, Code: {}", record.getEmail(), cleanOtp);

        // TỰ ĐỘNG HOÀN TẤT THANH TOÁN HỌC PHÍ CHO SINH VIÊN
        if (record.getStudentCode() != null && !record.getStudentCode().isBlank()) {
            return studentService.payTuitionByStudentCodeAndEmail(record.getStudentCode(), record.getEmail());
        }
        return null;
    }
}
