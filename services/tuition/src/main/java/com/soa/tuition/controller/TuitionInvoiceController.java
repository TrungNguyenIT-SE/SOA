package com.soa.tuition.controller;

import com.soa.tuition.dto.StudentResponse;
import com.soa.tuition.service.StudentService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.ExampleObject;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/tuition-invoices")
@Tag(name = "Người dùng - Hóa đơn học phí (Invoices)", description = "Tra cứu hóa đơn học phí chi tiết theo MSSV (Nguyên)")
public class TuitionInvoiceController {

    private final StudentService studentService;

    public TuitionInvoiceController(StudentService studentService) {
        this.studentService = studentService;
    }

    @GetMapping("/by-student/{student_code}")
    @Operation(summary = "Tra cứu hóa đơn học phí theo MSSV",
               description = "Tra cứu thông tin sinh viên và hóa đơn học phí cần nộp theo mã số sinh viên.")
    @ApiResponses({
        @ApiResponse(responseCode = "200", description = "Tìm thấy hóa đơn học phí",
            content = @Content(mediaType = MediaType.APPLICATION_JSON_VALUE, schema = @Schema(implementation = StudentResponse.class))),
        @ApiResponse(responseCode = "404", description = "Không tìm thấy sinh viên hoặc hóa đơn",
            content = @Content(mediaType = MediaType.APPLICATION_JSON_VALUE,
                examples = @ExampleObject(value = "{\"status\":404,\"code\":\"STUDENT_NOT_FOUND\",\"message\":\"Không tìm thấy sinh viên có mã: 52400099\"}")))
    })
    public StudentResponse getInvoiceByStudent(@PathVariable("student_code") String studentCode) {
        return studentService.getStudent(studentCode);
    }
}
