package com.soa.tuition.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

@Schema(name = "OtpVerifyRequest", description = "Yêu cầu xác thực mã OTP — một OTP chỉ dùng được một lần và phải dùng trước khi hết hạn 5 phút")
public class OtpVerifyRequest {

    @NotBlank(message = "Mã OTP không được để trống")
    @Pattern(regexp = "^[0-9]{6}$", message = "Mã OTP phải là 6 chữ số")
    @Schema(description = "Mã OTP 6 chữ số nhận được qua email — chỉ dùng được một lần, hết hạn sau 5 phút",
            example = "847291", requiredMode = Schema.RequiredMode.REQUIRED,
            pattern = "^[0-9]{6}$", minLength = 6, maxLength = 6)
    private String otp;

    @Schema(description = "Email người nộp tiền (tuỳ chọn, dùng để đối chiếu thêm nếu cần)",
            example = "dangkhoa040706@gmail.com")
    private String email;

    public OtpVerifyRequest() {}

    public String getOtp() { return otp; }
    public void setOtp(String otp) { this.otp = otp; }
    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }
}
