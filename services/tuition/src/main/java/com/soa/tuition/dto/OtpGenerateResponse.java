package com.soa.tuition.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.Instant;

@Schema(name = "OtpGenerateResponse", description = "Kết quả sinh mã OTP — OTP đã được gửi qua email, KHÔNG xuất hiện trong response này vì lý do bảo mật")
public class OtpGenerateResponse {

    @Schema(description = "Trạng thái xử lý", example = "success")
    private String status = "success";

    @Schema(description = "Thông báo kết quả", example = "Mã OTP đã được tạo và gửi thành công tới dangkhoa040706@gmail.com")
    private String message;

    @Schema(description = "Email đã nhận OTP (để UI hiển thị xác nhận)", example = "dangkhoa040706@gmail.com")
    private String email;

    @JsonProperty("expires_at")
    @Schema(description = "Thời điểm OTP hết hạn (ISO-8601 UTC, hiệu lực 5 phút kể từ khi sinh)",
            example = "2026-10-23T03:11:00Z")
    private Instant expiresAt;

    public OtpGenerateResponse() {}

    public OtpGenerateResponse(String message, String email, String otpCode, Instant expiresAt) {
        this.status = "success";
        this.message = message;
        this.email = email;
        // otpCode intentionally NOT stored in response — only sent via email
        this.expiresAt = expiresAt;
    }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public String getMessage() { return message; }
    public void setMessage(String message) { this.message = message; }
    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }
    public Instant getExpiresAt() { return expiresAt; }
    public void setExpiresAt(Instant expiresAt) { this.expiresAt = expiresAt; }
}

