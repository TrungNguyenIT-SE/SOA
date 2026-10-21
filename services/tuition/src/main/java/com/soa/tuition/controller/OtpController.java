package com.soa.tuition.controller;

import com.soa.tuition.dto.OtpGenerateRequest;
import com.soa.tuition.dto.OtpGenerateResponse;
import com.soa.tuition.dto.OtpVerifyRequest;
import com.soa.tuition.service.OtpService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/v1/otp")
@Tag(name = "Dịch vụ OTP", description = "Dịch vụ Sinh và Xác thực mã OTP thanh toán học phí (Nguyên)")
public class OtpController {

    private final OtpService otpService;

    public OtpController(OtpService otpService) {
        this.otpService = otpService;
    }

    @PostMapping("/generate")
    @Operation(summary = "Sinh mã OTP ngẫu nhiên 6 chữ số (Hiệu lực 5 phút)")
    public OtpGenerateResponse generateOtp(@Valid @RequestBody OtpGenerateRequest req) {
        return otpService.generateOtp(req);
    }

    @PostMapping("/verify")
    @Operation(summary = "Xác thực mã OTP thanh toán")
    public ResponseEntity<Map<String, Object>> verifyOtp(@Valid @RequestBody OtpVerifyRequest req) {
        otpService.verifyOtp(req);
        return ResponseEntity.ok(Map.of(
                "status", "success",
                "valid", true,
                "message", "Xác thực mã OTP thành công. Hợp lệ để hoàn tất thanh toán học phí."
        ));
    }
}
