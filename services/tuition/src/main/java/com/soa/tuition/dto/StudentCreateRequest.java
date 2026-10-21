package com.soa.tuition.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

public class StudentCreateRequest {

    @NotBlank(message = "Mã số sinh viên không được để trống")
    @JsonProperty("student_code")
    private String studentCode;

    @NotBlank(message = "Họ và tên sinh viên không được để trống")
    @JsonProperty("student_name")
    private String studentName;

    private String term = "HK1/2026-2027";

    @NotNull(message = "Số tiền học phí không được để trống")
    @Min(value = 100000, message = "Số tiền học phí tối thiểu là 100,000 VND")
    private Long amount;

    private String status = "UNPAID";

    public StudentCreateRequest() {}

    public String getStudentCode() { return studentCode; }
    public void setStudentCode(String studentCode) { this.studentCode = studentCode; }
    public String getStudentName() { return studentName; }
    public void setStudentName(String studentName) { this.studentName = studentName; }
    public String getTerm() { return term; }
    public void setTerm(String term) { this.term = term; }
    public Long getAmount() { return amount; }
    public void setAmount(Long amount) { this.amount = amount; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
}
