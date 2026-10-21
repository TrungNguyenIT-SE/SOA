package com.soa.tuition.controller;

import com.soa.tuition.dto.StudentCreateRequest;
import com.soa.tuition.dto.StudentResponse;
import com.soa.tuition.dto.StudentUpdateRequest;
import com.soa.tuition.service.StudentService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
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
    @Operation(summary = "Xem danh sách toàn bộ sinh viên trong hệ thống")
    public List<StudentResponse> listStudents() {
        return studentService.listStudents();
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    @Operation(summary = "Thêm hồ sơ sinh viên mới & khởi tạo học phí (Chặn trùng MSSV cùng kỳ)")
    public StudentResponse createStudent(@Valid @RequestBody StudentCreateRequest req) {
        return studentService.createStudent(req);
    }

    @GetMapping("/{student_code}")
    @Operation(summary = "Xem thông tin chi tiết hồ sơ sinh viên theo MSSV")
    public StudentResponse getStudent(@PathVariable("student_code") String studentCode) {
        return studentService.getStudent(studentCode);
    }

    @PutMapping("/{student_code}")
    @Operation(summary = "Cập nhật sinh viên hoặc học phí (Kiểm tra số dư & trừ tiền khi chuyển sang Đã nộp)")
    public StudentResponse updateStudent(@PathVariable("student_code") String studentCode,
                                         @RequestBody StudentUpdateRequest req) {
        return studentService.updateStudent(studentCode, req);
    }

    @DeleteMapping("/{student_code}")
    @Operation(summary = "Xóa sinh viên và học phí khỏi hệ thống")
    public ResponseEntity<Map<String, String>> deleteStudent(@PathVariable("student_code") String studentCode) {
        studentService.deleteStudent(studentCode);
        return ResponseEntity.ok(Map.of(
                "status", "success",
                "message", "Đã xóa sinh viên " + studentCode + " và các khoản học phí thành công."
        ));
    }
}
