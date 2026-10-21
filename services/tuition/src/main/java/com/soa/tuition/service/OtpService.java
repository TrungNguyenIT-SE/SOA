package com.soa.tuition.service;

import com.soa.tuition.dto.OtpGenerateRequest;
import com.soa.tuition.dto.OtpGenerateResponse;
import com.soa.tuition.dto.OtpVerifyRequest;
import com.soa.tuition.entity.OtpRecord;
import com.soa.tuition.exception.AppException;
import com.soa.tuition.repository.OtpRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.security.SecureRandom;
import java.time.Duration;
import java.time.Instant;

@Service
public class OtpService {

    private static final Logger log = LoggerFactory.getLogger(OtpService.class);
    private final OtpRepository otpRepository;
    private final SecureRandom random = new SecureRandom();

    public OtpService(OtpRepository otpRepository) {
        this.otpRepository = otpRepository;
    }

    @Transactional
    public OtpGenerateResponse generateOtp(OtpGenerateRequest req) {
        int number = 100000 + random.nextInt(900000);
        String otpCode = String.valueOf(number);
        Instant expiresAt = Instant.now().plus(Duration.ofMinutes(5));

        OtpRecord record = new OtpRecord(
                req.getEmail().trim(),
                req.getStudentCode() != null ? req.getStudentCode().trim() : null,
                req.getAmount(),
                otpCode,
                expiresAt
        );
        otpRepository.save(record);

        log.info("[OTP GENERATED] Email: {}, Code: {}, Expires at: {}", req.getEmail(), otpCode, expiresAt);

        return new OtpGenerateResponse(
                "Mã OTP đã được tạo và gửi thành công tới " + req.getEmail(),
                req.getEmail(),
                otpCode,
                expiresAt
        );
    }

    @Transactional
    public boolean verifyOtp(OtpVerifyRequest req) {
        String cleanOtp = req.getOtp().trim();
        OtpRecord record = otpRepository.findFirstByOtpCodeAndUsedFalseOrderByCreatedAtDesc(cleanOtp)
                .orElseThrow(() -> new AppException(HttpStatus.UNPROCESSABLE_ENTITY, "INVALID_OTP", "Mã OTP không chính xác hoặc đã được sử dụng."));

        if (Instant.now().isAfter(record.getExpiresAt())) {
            throw new AppException(HttpStatus.UNPROCESSABLE_ENTITY, "OTP_EXPIRED", "Mã OTP đã hết hạn (chỉ có hiệu lực trong 5 phút).");
        }

        record.setUsed(true);
        otpRepository.save(record);
        log.info("[OTP VERIFIED SUCCESS] Email: {}, Code: {}", record.getEmail(), cleanOtp);
        return true;
    }
}
