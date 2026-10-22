package com.soa.tuition.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

@Schema(name = "OtpGenerateRequest", description = "Yêu cầu sinh mã OTP xác thực thanh toán học phí — OTP gửi qua email, KHÔNG trả về trong response")
public class OtpGenerateRequest {

    @NotBlank(message = "Email người nhận không được để trống")
    @Email(message = "Email không đúng định dạng")
    @Schema(description = "Email người nộp tiền (payer) để nhận OTP — phải là email hợp lệ",
            example = "dangkhoa040706@gmail.com", requiredMode = Schema.RequiredMode.REQUIRED)
    private String email;

    @JsonProperty("payer_name")
    @Schema(description = "Họ tên người nộp tiền — dùng để hiển thị trong email OTP",
            example = "Hoàng Thái Đăng Khoa")
    private String payerName;

    @NotBlank(message = "Mã số sinh viên (student_code) không được để trống")
    @JsonProperty("student_code")
    @Schema(description = "Mã số sinh viên (MSSV) cần nộp học phí — sinh viên phải tồn tại và chưa đóng học phí",
            example = "52400003", requiredMode = Schema.RequiredMode.REQUIRED)
    private String studentCode;

    @NotNull(message = "Số tiền học phí không được để trống")
    @Positive(message = "Số tiền phải lớn hơn 0")
    @Schema(description = "Số tiền học phí cần thanh toán (VND) — BẮT BUỘC phải khớp chính xác với số tiền học phí thực tế của sinh viên",
            example = "1000000", requiredMode = Schema.RequiredMode.REQUIRED)
    private Long amount;

    public OtpGenerateRequest() {}

    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }
    public String getPayerName() { return payerName; }
    public void setPayerName(String payerName) { this.payerName = payerName; }
    public String getStudentCode() { return studentCode; }
    public void setStudentCode(String studentCode) { this.studentCode = studentCode; }
    public Long getAmount() { return amount; }
    public void setAmount(Long amount) { this.amount = amount; }
}
