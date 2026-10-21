package com.soa.tuition.controller;

import com.soa.tuition.dto.StudentCreateRequest;
import com.soa.tuition.dto.StudentResponse;
import com.soa.tuition.dto.StudentUpdateRequest;
import com.soa.tuition.service.StudentService;
import io.swagger.v3.oas.annotations.Hidden;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/students")
@Tag(name = "Người dùng - Tra cứu học phí (User)", description = "Dịch vụ Tra cứu Học phí dành cho Sinh viên và Phụ huynh (Nguyên)")
public class StudentController {

    private final StudentService studentService;

    public StudentController(StudentService studentService) {
        this.studentService = studentService;
    }

    @GetMapping("/{student_code}")
    @Operation(summary = "Tra cứu thông tin sinh viên & học phí theo MSSV")
    public StudentResponse getStudent(@PathVariable("student_code") String studentCode) {
        return studentService.getStudent(studentCode);
    }

    @Hidden
    @GetMapping
    public List<StudentResponse> listStudents() {
        return studentService.listStudents();
    }

    @Hidden
    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public StudentResponse createStudent(@Valid @RequestBody StudentCreateRequest req) {
        return studentService.createStudent(req);
    }

    @Hidden
    @PutMapping("/{student_code}")
    public StudentResponse updateStudent(@PathVariable("student_code") String studentCode,
                                         @RequestBody StudentUpdateRequest req) {
        return studentService.updateStudent(studentCode, req);
    }

    @Hidden
    @DeleteMapping("/{student_code}")
    public ResponseEntity<Map<String, String>> deleteStudent(@PathVariable("student_code") String studentCode) {
        studentService.deleteStudent(studentCode);
        return ResponseEntity.ok(Map.of(
                "status", "success",
                "message", "Đã xóa sinh viên " + studentCode + " và các khoản học phí thành công."
        ));
    }
}
