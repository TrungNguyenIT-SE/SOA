package com.soa.tuition.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

@Schema(name = "StudentUpdateRequest", description = "Dữ liệu cập nhật hồ sơ sinh viên hoặc thực hiện thanh toán học phí")
public class StudentUpdateRequest {

    @JsonProperty("full_name")
    @Schema(description = "Họ và tên sinh viên (chỉ Admin được phép sửa)", example = "Trần Quốc Bảo")
    private String fullName;

    @Schema(description = "Học kỳ áp dụng học phí (chỉ Admin được phép sửa khi chưa thanh toán)", example = "HK1/2026-2027")
    private String term;

    @Schema(description = "Số tiền học phí (VND) — chỉ được sửa khi chưa thanh toán", example = "1000000")
    private Long amount;

    @Schema(description = "Trạng thái học phí: 'PAID' (Đã nộp — hệ thống sẽ tự động trừ tiền) hoặc 'UNPAID' (Chưa nộp)",
            allowableValues = {"PAID", "UNPAID"}, example = "PAID")
    private String status;

    @JsonProperty("payer_user_id")
    @Schema(description = "ID người dùng nộp tiền (User ID trong bảng users) để trích xuất số dư tài khoản ngân hàng", example = "1")
    private Integer payerUserId;

    public StudentUpdateRequest() {}

    public String getFullName() { return fullName; }
    public void setFullName(String fullName) { this.fullName = fullName; }
    public String getTerm() { return term; }
    public void setTerm(String term) { this.term = term; }
    public Long getAmount() { return amount; }
    public void setAmount(Long amount) { this.amount = amount; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public Integer getPayerUserId() { return payerUserId; }
    public void setPayerUserId(Integer payerUserId) { this.payerUserId = payerUserId; }
}
