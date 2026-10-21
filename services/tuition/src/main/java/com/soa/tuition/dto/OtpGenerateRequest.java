package com.soa.tuition.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotBlank;

public class OtpGenerateRequest {

    @NotBlank(message = "Email người nhận không được để trống")
    private String email;

    @JsonProperty("student_code")
    private String studentCode;

    private Long amount;

    public OtpGenerateRequest() {}

    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }
    public String getStudentCode() { return studentCode; }
    public void setStudentCode(String studentCode) { this.studentCode = studentCode; }
    public Long getAmount() { return amount; }
    public void setAmount(Long amount) { this.amount = amount; }
}
