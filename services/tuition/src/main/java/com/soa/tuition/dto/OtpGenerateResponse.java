package com.soa.tuition.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.Instant;

public class OtpGenerateResponse {
    private String status = "success";
    private String message;
    private String email;

    @JsonProperty("otp_code")
    private String otpCode;

    @JsonProperty("expires_at")
    private Instant expiresAt;

    public OtpGenerateResponse() {}

    public OtpGenerateResponse(String message, String email, String otpCode, Instant expiresAt) {
        this.status = "success";
        this.message = message;
        this.email = email;
        this.otpCode = otpCode;
        this.expiresAt = expiresAt;
    }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public String getMessage() { return message; }
    public void setMessage(String message) { this.message = message; }
    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }
    public String getOtpCode() { return otpCode; }
    public void setOtpCode(String otpCode) { this.otpCode = otpCode; }
    public Instant getExpiresAt() { return expiresAt; }
    public void setExpiresAt(Instant expiresAt) { this.expiresAt = expiresAt; }
}
