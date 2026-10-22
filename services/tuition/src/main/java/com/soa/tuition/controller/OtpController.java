package com.soa.tuition.controller;

import com.soa.tuition.dto.OtpGenerateRequest;
import com.soa.tuition.dto.OtpGenerateResponse;
import com.soa.tuition.dto.OtpVerifyRequest;
import com.soa.tuition.service.OtpService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.ExampleObject;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/v1/otp")
@Tag(name = "Người dùng - Xác thực OTP (User)",
     description = "Dịch vụ Sinh và Xác thực mã OTP thanh toán học phí (Nguyên). " +
                   "OTP gồm 6 chữ số ngẫu nhiên, hiệu lực 5 phút, chỉ dùng một lần. " +
                   "Mã OTP KHÔNG xuất hiện trong API response — chỉ gửi qua email.")
public class OtpController {

    private final OtpService otpService;

    public OtpController(OtpService otpService) {
        this.otpService = otpService;
    }

    @PostMapping("/generate")
    @Operation(
        summary = "Sinh mã OTP ngẫu nhiên 6 chữ số (Hiệu lực 5 phút)",
        description = """
            Tạo một mã OTP bảo mật gồm 6 chữ số và gửi tới **email** của người nộp tiền.
            
            **Quy tắc kiểm tra logic nghiêm ngặt:**
            1. **Kiểm tra sinh viên:** MSSV (`student_code`) phải tồn tại trong hệ thống. Nếu không tìm thấy, trả về lỗi `404 STUDENT_NOT_FOUND`.
            2. **Chặn tạo OTP khi đã nộp:** Nếu sinh viên đã hoàn thành học phí (`status='PAID'`), hệ thống từ chối cấp OTP với lỗi `409 ALREADY_PAID`.
            3. **Khớp chính xác số tiền:** Số tiền `amount` bắt buộc phải khớp chính xác với học phí cần nộp của sinh viên. Nếu nhập sai số tiền, trả về lỗi `400 AMOUNT_MISMATCH`.
            4. **Bảo mật:** OTP KHÔNG được trả về trong response body — chỉ gửi qua email.
            5. **Hiệu lực:** OTP chỉ hợp lệ trong 5 phút, chỉ dùng được 1 lần duy nhất.
            """
    )
    @ApiResponses({
        @ApiResponse(responseCode = "200", description = "OTP đã sinh và gửi thành công qua email",
            content = @Content(mediaType = MediaType.APPLICATION_JSON_VALUE,
                schema = @Schema(implementation = OtpGenerateResponse.class),
                examples = @ExampleObject(name = "Thành công", value = """
                    {
                      "status": "success",
                      "message": "Mã OTP đã được tạo và gửi thành công tới dangkhoa040706@gmail.com",
                      "email": "dangkhoa040706@gmail.com",
                      "expires_at": "2026-10-23T03:11:00Z"
                    }
                    """))),
        @ApiResponse(responseCode = "400", description = "Số tiền không khớp với học phí thực tế hoặc thiếu MSSV",
            content = @Content(mediaType = MediaType.APPLICATION_JSON_VALUE,
                examples = @ExampleObject(name = "Sai số tiền", value = """
                    {
                      "status": 400,
                      "code": "AMOUNT_MISMATCH",
                      "message": "Số tiền thanh toán (500.000 đ) không khớp với số tiền học phí thực tế của sinh viên 52400003 (1.000.000 đ)!"
                    }
                    """))),
        @ApiResponse(responseCode = "404", description = "Không tìm thấy sinh viên hoặc khoản học phí",
            content = @Content(mediaType = MediaType.APPLICATION_JSON_VALUE,
                examples = @ExampleObject(value = """
                    {
                      "status": 404,
                      "code": "STUDENT_NOT_FOUND",
                      "message": "Không tìm thấy sinh viên hoặc khoản học phí cho MSSV: 52400099"
                    }
                    """))),
        @ApiResponse(responseCode = "409", description = "Học phí của sinh viên đã được thanh toán trước đó (chặn trùng lặp)",
            content = @Content(mediaType = MediaType.APPLICATION_JSON_VALUE,
                examples = @ExampleObject(value = """
                    {
                      "status": 409,
                      "code": "ALREADY_PAID",
                      "message": "Khoản học phí của sinh viên 52400001 (học kỳ HK1/2026-2027) đã được thanh toán hoàn tất. Không thể sinh mã OTP để thanh toán lại!"
                    }
                    """))),
        @ApiResponse(responseCode = "422", description = "Dữ liệu đầu vào không hợp lệ (email rỗng, amount <= 0, ...)",
            content = @Content(mediaType = MediaType.APPLICATION_JSON_VALUE,
                examples = @ExampleObject(value = """
                    {
                      "status": 422,
                      "code": "VALIDATION_ERROR",
                      "message": "Dữ liệu đầu vào không hợp lệ.",
                      "fieldErrors": [
                        { "field": "email", "message": "Email không đúng định dạng" },
                        { "field": "studentCode", "message": "Mã số sinh viên không được để trống" },
                        { "field": "amount", "message": "Số tiền phải lớn hơn 0" }
                      ]
                    }
                    """))),
        @ApiResponse(responseCode = "500", description = "Lỗi nội bộ hệ thống")
    })
    public OtpGenerateResponse generateOtp(@Valid @RequestBody OtpGenerateRequest req) {
        return otpService.generateOtp(req);
    }

    @PostMapping("/verify")
    @Operation(
        summary = "Xác thực mã OTP thanh toán",
        description = """
            Xác thực mã OTP 6 chữ số mà người dùng nhận được qua email.
            
            **Quy tắc xác thực:**
            - OTP phải đúng 6 chữ số.
            - OTP chưa được sử dụng trước đó.
            - OTP chưa hết hạn (sinh trong vòng 5 phút).
            - Nếu truyền `email`: Hệ thống đối chiếu OTP có đúng được cấp cho email này hay không.
            
            **Sau khi verify thành công**, hệ thống sẽ đánh dấu OTP là đã dùng (`used=true`).
            Gọi lại với cùng OTP sẽ trả về lỗi `INVALID_OTP`.
            """
    )
    @ApiResponses({
        @ApiResponse(responseCode = "200", description = "OTP hợp lệ — giao dịch được phép tiếp tục",
            content = @Content(mediaType = MediaType.APPLICATION_JSON_VALUE,
                examples = @ExampleObject(name = "Thành công", value = """
                    {
                      "status": "success",
                      "valid": true,
                      "message": "Xác thực mã OTP thành công. Hợp lệ để hoàn tất thanh toán học phí."
                    }
                    """))),
        @ApiResponse(responseCode = "422", description = "OTP sai, đã dùng, hết hạn hoặc không khớp email",
            content = @Content(mediaType = MediaType.APPLICATION_JSON_VALUE,
                examples = {
                    @ExampleObject(name = "OTP sai hoặc đã dùng", value = """
                        {
                          "status": 422,
                          "code": "INVALID_OTP",
                          "message": "Mã OTP không chính xác hoặc đã được sử dụng."
                        }
                        """),
                    @ExampleObject(name = "OTP hết hạn", value = """
                        {
                          "status": 422,
                          "code": "OTP_EXPIRED",
                          "message": "Mã OTP đã hết hạn (chỉ có hiệu lực trong 5 phút)."
                        }
                        """),
                    @ExampleObject(name = "Email không khớp", value = """
                        {
                          "status": 422,
                          "code": "EMAIL_MISMATCH",
                          "message": "Mã OTP không khớp với địa chỉ email xác thực."
                        }
                        """)
                }))
    })
    public ResponseEntity<Map<String, Object>> verifyOtp(@Valid @RequestBody OtpVerifyRequest req) {
        com.soa.tuition.dto.StudentResponse studentResp = otpService.verifyOtp(req);
        Map<String, Object> response = new java.util.HashMap<>();
        response.put("status", "success");
        response.put("valid", true);
        response.put("message", "Xác thực mã OTP thành công. Khoản học phí đã được thanh toán hoàn tất!");
        if (studentResp != null) {
            response.put("student_code", studentResp.getStudentCode());
            response.put("student_name", studentResp.getStudentName());
            response.put("term", studentResp.getTerm());
            response.put("amount", studentResp.getAmount());
            response.put("payment_status", studentResp.getStatus());
        }
        return ResponseEntity.ok(response);
    }
}
