package com.soa.tuition.service;

import com.soa.tuition.dto.StudentCreateRequest;
import com.soa.tuition.dto.StudentResponse;
import com.soa.tuition.dto.StudentUpdateRequest;
import com.soa.tuition.entity.Student;
import com.soa.tuition.entity.TuitionInvoice;
import com.soa.tuition.exception.AppException;
import com.soa.tuition.repository.StudentRepository;
import com.soa.tuition.repository.TuitionInvoiceRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;

import java.text.NumberFormat;
import java.time.Instant;
import java.util.*;

@Service
public class StudentService {

    private static final Logger log = LoggerFactory.getLogger(StudentService.class);

    private final StudentRepository studentRepository;
    private final TuitionInvoiceRepository invoiceRepository;
    private final RestTemplate restTemplate;

    @Value("${app.internal-token}")
    private String internalToken;

    @Value("${app.account-service-url}")
    private String accountServiceUrl;

    @Value("${app.payment-service-url}")
    private String paymentServiceUrl;

    public StudentService(StudentRepository studentRepository,
                          TuitionInvoiceRepository invoiceRepository,
                          RestTemplate restTemplate) {
        this.studentRepository = studentRepository;
        this.invoiceRepository = invoiceRepository;
        this.restTemplate = restTemplate;
    }

    public List<StudentResponse> listStudents() {
        List<TuitionInvoice> invoices = invoiceRepository.findAllWithStudent();
        List<StudentResponse> result = new ArrayList<>();
        for (TuitionInvoice inv : invoices) {
            result.add(StudentResponse.fromEntity(inv));
        }
        return result;
    }

    public StudentResponse getStudent(String studentCode) {
        String cleanCode = studentCode.trim().toUpperCase();
        TuitionInvoice invoice = invoiceRepository.findFirstByStudent_StudentCodeOrderByTermDesc(cleanCode)
                .orElseThrow(() -> new AppException(HttpStatus.NOT_FOUND, "STUDENT_NOT_FOUND", "Không tìm thấy sinh viên có mã: " + cleanCode));
        return StudentResponse.fromEntity(invoice);
    }

    @Transactional
    public StudentResponse createStudent(StudentCreateRequest req) {
        String cleanCode = req.getStudentCode().trim().toUpperCase();
        String term = req.getTerm().trim();

        Optional<Student> optStudent = studentRepository.findByStudentCode(cleanCode);
        Student student;

        if (optStudent.isPresent()) {
            student = optStudent.get();
            Optional<TuitionInvoice> existingInvoice = invoiceRepository.findByStudentAndTerm(student, term);
            if (existingInvoice.isPresent()) {
                throw new AppException(HttpStatus.CONFLICT, "STUDENT_TERM_ALREADY_EXISTS",
                        "Mã sinh viên " + cleanCode + " đã có học phí cho " + term + ". Không thể tạo trùng mã sinh viên cho cùng một học kỳ!");
            }
        } else {
            student = new Student(cleanCode, req.getStudentName().trim());
            studentRepository.save(student);
        }

        String status = (req.getStatus() != null && !req.getStatus().isBlank())
                ? req.getStatus().trim().toUpperCase() : "UNPAID";

        TuitionInvoice invoice = new TuitionInvoice(student, term, req.getAmount(), status);
        invoiceRepository.save(invoice);

        return StudentResponse.fromEntity(invoice);
    }

    @Transactional
    public StudentResponse updateStudent(String studentCode, StudentUpdateRequest req) {
        String cleanCode = studentCode.trim().toUpperCase();
        Student student = studentRepository.findByStudentCode(cleanCode)
                .orElseThrow(() -> new AppException(HttpStatus.NOT_FOUND, "STUDENT_NOT_FOUND", "Không tìm thấy sinh viên: " + cleanCode));

        if (req.getFullName() != null && !req.getFullName().isBlank()) {
            student.setFullName(req.getFullName().trim());
            studentRepository.save(student);
        }

        TuitionInvoice invoice = invoiceRepository.findFirstByStudent_StudentCodeOrderByTermDesc(cleanCode)
                .orElseThrow(() -> new AppException(HttpStatus.NOT_FOUND, "INVOICE_NOT_FOUND", "Không tìm thấy khoản học phí của sinh viên: " + cleanCode));

        if (req.getTerm() != null && !req.getTerm().isBlank()) {
            invoice.setTerm(req.getTerm().trim());
        }
        if (req.getAmount() != null) {
            invoice.setAmount(req.getAmount());
        }

        if (req.getStatus() != null && !req.getStatus().isBlank()) {
            String targetStatus = req.getStatus().trim().toUpperCase();

            // Nếu chuyển từ CHƯA NỘP sang ĐÃ NỘP -> KIỂM TRA SỐ DƯ & TRỪ TIỀN
            if ("PAID".equals(targetStatus) && !"PAID".equals(invoice.getStatus())) {
                processPaymentDebit(student, invoice, req.getPayerUserId());
            } else if ("UNPAID".equals(targetStatus)) {
                invoice.setStatus("UNPAID");
                invoice.setPaidAt(null);
                invoice.setPaidByPaymentId(null);
                invoice.setReservedByPaymentId(null);
                invoice.setReservationExpiresAt(null);
            }
        }

        invoiceRepository.save(invoice);
        return StudentResponse.fromEntity(invoice);
    }

    private void processPaymentDebit(Student student, TuitionInvoice invoice, Integer payerUserId) {
        int userId = (payerUserId != null && payerUserId > 0) ? payerUserId : 1; // Mặc định admin nếu không truyền
        log.info("[CHECK BALANCE & DEBIT] Processing tuition payment for student: {}, amount: {}, payerUserId: {}",
                student.getStudentCode(), invoice.getAmount(), userId);

        HttpHeaders headers = new HttpHeaders();
        headers.set("X-Internal-Token", internalToken);
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<Void> entity = new HttpEntity<>(headers);

        // 1. Lấy thông tin tài khoản & số dư của người nộp
        String accountUrl = accountServiceUrl + "/internal/v1/accounts/by-user/" + userId;
        Map<String, Object> accountData;
        try {
            ResponseEntity<Map> resp = restTemplate.exchange(accountUrl, HttpMethod.GET, entity, Map.class);
            accountData = resp.getBody();
        } catch (Exception e) {
            log.error("Failed to query account balance: {}", e.getMessage());
            throw new AppException(HttpStatus.BAD_GATEWAY, "ACCOUNT_SERVICE_UNAVAILABLE", "Không thể kết nối đến Dịch vụ Tài khoản (Account Service): " + e.getMessage());
        }

        if (accountData == null || !accountData.containsKey("available_balance")) {
            throw new AppException(HttpStatus.NOT_FOUND, "ACCOUNT_NOT_FOUND", "Không tìm thấy tài khoản ngân hàng của người dùng ID: " + userId);
        }

        long availableBalance = ((Number) accountData.get("available_balance")).longValue();
        UUID accountId = UUID.fromString((String) accountData.get("id"));

        NumberFormat formatter = NumberFormat.getInstance(new Locale("vi", "VN"));
        if (availableBalance < invoice.getAmount()) {
            long missing = invoice.getAmount() - availableBalance;
            throw new AppException(HttpStatus.UNPROCESSABLE_ENTITY, "INSUFFICIENT_FUNDS",
                    String.format("Tài khoản người nộp không đủ số dư để thanh toán học phí! (Số dư hiện có: %s đ, Học phí: %s đ, Còn thiếu: %s đ). Không thể chuyển sang Đã nộp!",
                            formatter.format(availableBalance), formatter.format(invoice.getAmount()), formatter.format(missing)));
        }

        // 2. Trừ tiền tài khoản (Debit)
        UUID paymentId = UUID.randomUUID();
        Map<String, Object> debitPayload = new HashMap<>();
        debitPayload.put("payment_id", paymentId.toString());
        debitPayload.put("amount", invoice.getAmount());
        HttpEntity<Map<String, Object>> debitEntity = new HttpEntity<>(debitPayload, headers);

        String debitUrl = accountServiceUrl + "/internal/v1/accounts/" + accountId + "/debits";
        try {
            restTemplate.exchange(debitUrl, HttpMethod.POST, debitEntity, Map.class);
        } catch (Exception e) {
            log.error("Failed to debit account: {}", e.getMessage());
            throw new AppException(HttpStatus.UNPROCESSABLE_ENTITY, "DEBIT_FAILED", "Không thể trừ tiền tài khoản người nộp: " + e.getMessage());
        }

        // 3. Lấy thông tin người nộp từ Identity service & Ghi nhận sang C# Payment Service
        String payerName = "Người dùng ID: " + userId;
        String payerEmail = "user" + userId + "@example.com";
        try {
            String identityUrl = "http://web-identity:8000/internal/v1/users/" + userId;
            ResponseEntity<Map> userResp = restTemplate.exchange(identityUrl, HttpMethod.GET, entity, Map.class);
            if (userResp.getBody() != null) {
                if (userResp.getBody().get("full_name") != null) payerName = (String) userResp.getBody().get("full_name");
                if (userResp.getBody().get("email") != null) payerEmail = (String) userResp.getBody().get("email");
            }
        } catch (Exception ex) {
            log.warn("Could not fetch user details from identity: {}", ex.getMessage());
        }

        try {
            Map<String, Object> txPayload = new HashMap<>();
            txPayload.put("id", paymentId.toString());
            txPayload.put("payer_user_id", userId);
            txPayload.put("account_id", accountId.toString());
            txPayload.put("payer_name", payerName);
            txPayload.put("payer_email", payerEmail);
            txPayload.put("student_code", student.getStudentCode());
            txPayload.put("student_name", student.getFullName());
            txPayload.put("term", invoice.getTerm());
            txPayload.put("amount", invoice.getAmount());
            txPayload.put("status", "SUCCEEDED");
            HttpEntity<Map<String, Object>> txEntity = new HttpEntity<>(txPayload, headers);

            restTemplate.exchange(paymentServiceUrl + "/internal/v1/transactions/record", HttpMethod.POST, txEntity, Map.class);
        } catch (Exception e) {
            log.warn("Could not notify C# Payment service: {}", e.getMessage());
        }

        invoice.setStatus("PAID");
        invoice.setPaidAt(Instant.now());
        invoice.setPaidByPaymentId(paymentId);
    }

    @Transactional
    public void deleteStudent(String studentCode) {
        String cleanCode = studentCode.trim().toUpperCase();
        Student student = studentRepository.findByStudentCode(cleanCode)
                .orElseThrow(() -> new AppException(HttpStatus.NOT_FOUND, "STUDENT_NOT_FOUND", "Không tìm thấy sinh viên: " + cleanCode));
        studentRepository.delete(student);
    }

    @Transactional
    public void syncStatus(String studentCode, String newStatus) {
        String cleanCode = studentCode.trim().toUpperCase();
        Student student = studentRepository.findByStudentCode(cleanCode)
                .orElseThrow(() -> new AppException(HttpStatus.NOT_FOUND, "STUDENT_NOT_FOUND", "Không tìm thấy sinh viên: " + cleanCode));

        TuitionInvoice invoice = invoiceRepository.findFirstByStudent_StudentCodeOrderByTermDesc(cleanCode)
                .orElseThrow(() -> new AppException(HttpStatus.NOT_FOUND, "INVOICE_NOT_FOUND", "Không tìm thấy khoản học phí của sinh viên: " + cleanCode));

        String st = newStatus.trim().toUpperCase();
        invoice.setStatus(st);
        if ("UNPAID".equals(st)) {
            invoice.setPaidAt(null);
            invoice.setPaidByPaymentId(null);
            invoice.setReservedByPaymentId(null);
            invoice.setReservationExpiresAt(null);
        } else if ("PAID".equals(st)) {
            invoice.setPaidAt(Instant.now());
        }
        invoiceRepository.save(invoice);
        log.info("[SYNC STATUS SUCCESS] Student: {} status set to {}", cleanCode, st);
    }
}
