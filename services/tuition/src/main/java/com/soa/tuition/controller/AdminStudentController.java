package com.soa.tuition.controller;

import com.soa.tuition.dto.StudentCreateRequest;
import com.soa.tuition.dto.StudentResponse;
import com.soa.tuition.dto.StudentUpdateRequest;
import com.soa.tuition.service.StudentService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.ExampleObject;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/admin/students")
@Tag(name = "Quản trị - Sinh viên & Học phí (Admin)", description = "Quản trị Hồ sơ Sinh viên và Học phí toàn trường (Nguyên)")
public class AdminStudentController {

    private final StudentService studentService;

    public AdminStudentController(StudentService studentService) {
        this.studentService = studentService;
    }

    @GetMapping
    @Operation(summary = "Xem danh sách toàn bộ sinh viên trong hệ thống",
               description = "Lấy danh sách tất cả các sinh viên kèm theo tình trạng học phí (PAID / UNPAID).")
    public List<StudentResponse> listStudents() {
        return studentService.listStudents();
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    @Operation(summary = "Thêm hồ sơ sinh viên mới & khởi tạo học phí",
               description = "Tạo sinh viên mới kèm một hóa đơn học phí ban đầu. Chặn trùng MSSV trong cùng một học kỳ.")
    @ApiResponses({
        @ApiResponse(responseCode = "201", description = "Tạo sinh viên thành công"),
        @ApiResponse(responseCode = "409", description = "MSSV đã có học phí cho học kỳ này (trùng lặp)",
            content = @Content(mediaType = MediaType.APPLICATION_JSON_VALUE,
                examples = @ExampleObject(value = "{\"status\":409,\"code\":\"STUDENT_TERM_ALREADY_EXISTS\",\"message\":\"Mã sinh viên 52400001 đã có học phí cho HK1/2026-2027. Không thể tạo trùng!\"}"))),
        @ApiResponse(responseCode = "422", description = "Dữ liệu đầu vào không hợp lệ")
    })
    public StudentResponse createStudent(@Valid @RequestBody StudentCreateRequest req) {
        return studentService.createStudent(req);
    }

    @GetMapping("/{student_code}")
    @Operation(summary = "Xem thông tin chi tiết hồ sơ sinh viên theo MSSV",
               description = "Tìm kiếm thông tin sinh viên và hóa đơn học phí mới nhất theo MSSV.")
    @ApiResponses({
        @ApiResponse(responseCode = "200", description = "Tìm thấy hồ sơ sinh viên"),
        @ApiResponse(responseCode = "404", description = "Không tìm thấy sinh viên",
            content = @Content(mediaType = MediaType.APPLICATION_JSON_VALUE,
                examples = @ExampleObject(value = "{\"status\":404,\"code\":\"STUDENT_NOT_FOUND\",\"message\":\"Không tìm thấy sinh viên có mã: 52400099\"}")))
    })
    public StudentResponse getStudent(@PathVariable("student_code") String studentCode) {
        return studentService.getStudent(studentCode);
    }

    @PutMapping("/{student_code}")
    @Operation(
        summary = "Cập nhật sinh viên hoặc thực hiện thanh toán học phí",
        description = """
            Cập nhật thông tin sinh viên hoặc chuyển trạng thái học phí sang `PAID` (Đã nộp):
            
            **Quy tắc kiểm tra logic nghiêm ngặt:**
            1. **Chặn thanh toán lại:** Nếu học phí của sinh viên đã ở trạng thái `PAID`, gọi lại với `status='PAID'` sẽ bị từ chối với lỗi `409 ALREADY_PAID`.
            2. **Chặn sửa số tiền khi đã nộp:** Nếu hóa đơn đã `PAID`, không thể thay đổi `amount` (trả về lỗi `400 CANNOT_MODIFY_PAID_INVOICE`).
            3. **Kiểm tra số dư & trừ tiền (Saga Debit):** Khi chuyển sang `PAID`, hệ thống tự động kiểm tra số dư của `payer_user_id`. Nếu không đủ số dư, trả về lỗi `422 INSUFFICIENT_FUNDS`.
            4. **Gửi email xác nhận:** Sau khi thanh toán thành công, hệ thống tự động gửi email biên nhận tới hộp thư người nộp tiền qua RabbitMQ.
            """
    )
    @ApiResponses({
        @ApiResponse(responseCode = "200", description = "Cập nhật / thanh toán thành công",
            content = @Content(mediaType = MediaType.APPLICATION_JSON_VALUE, schema = @Schema(implementation = StudentResponse.class))),
        @ApiResponse(responseCode = "400", description = "Không thể sửa số tiền của hóa đơn đã thanh toán",
            content = @Content(mediaType = MediaType.APPLICATION_JSON_VALUE,
                examples = @ExampleObject(value = "{\"status\":400,\"code\":\"CANNOT_MODIFY_PAID_INVOICE\",\"message\":\"Hóa đơn học phí của sinh viên 52400001 đã thanh toán hoàn tất. Không thể chỉnh sửa số tiền học phí!\"}"))),
        @ApiResponse(responseCode = "404", description = "Không tìm thấy sinh viên hoặc khoản học phí",
            content = @Content(mediaType = MediaType.APPLICATION_JSON_VALUE,
                examples = @ExampleObject(value = "{\"status\":404,\"code\":\"STUDENT_NOT_FOUND\",\"message\":\"Không tìm thấy sinh viên: 52400099\"}"))),
        @ApiResponse(responseCode = "409", description = "Sinh viên đã thanh toán học phí trước đó (chặn trùng lặp)",
            content = @Content(mediaType = MediaType.APPLICATION_JSON_VALUE,
                examples = @ExampleObject(value = "{\"status\":409,\"code\":\"ALREADY_PAID\",\"message\":\"Khoản học phí của sinh viên 52400001 (học kỳ HK1/2026-2027) đã được thanh toán trước đó. Không thể thanh toán lại!\"}"))),
        @ApiResponse(responseCode = "422", description = "Tài khoản người nộp không đủ số dư để thanh toán",
            content = @Content(mediaType = MediaType.APPLICATION_JSON_VALUE,
                examples = @ExampleObject(value = "{\"status\":422,\"code\":\"INSUFFICIENT_FUNDS\",\"message\":\"Tài khoản người nộp không đủ số dư để thanh toán học phí!\"}")))
    })
    public StudentResponse updateStudent(@PathVariable("student_code") String studentCode,
                                         @RequestBody StudentUpdateRequest req) {
        return studentService.updateStudent(studentCode, req);
    }

    @DeleteMapping("/{student_code}")
    @Operation(summary = "Xóa sinh viên và học phí khỏi hệ thống",
               description = "Xóa hoàn toàn sinh viên và các hóa đơn học phí liên quan khỏi cơ sở dữ liệu.")
    @ApiResponses({
        @ApiResponse(responseCode = "200", description = "Xóa thành công"),
        @ApiResponse(responseCode = "404", description = "Không tìm thấy sinh viên để xóa")
    })
    public ResponseEntity<Map<String, String>> deleteStudent(@PathVariable("student_code") String studentCode) {
        studentService.deleteStudent(studentCode);
        return ResponseEntity.ok(Map.of(
                "status", "success",
                "message", "Đã xóa sinh viên " + studentCode + " và các khoản học phí thành công."
        ));
    }
}
