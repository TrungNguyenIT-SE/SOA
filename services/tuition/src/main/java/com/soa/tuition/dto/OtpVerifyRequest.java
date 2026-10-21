package com.soa.tuition.dto;

import jakarta.validation.constraints.NotBlank;

public class OtpVerifyRequest {

    @NotBlank(message = "Mã OTP không được để trống")
    private String otp;

    private String email;

    public OtpVerifyRequest() {}

    public String getOtp() { return otp; }
    public void setOtp(String otp) { this.otp = otp; }
    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }
}
