package com.soa.tuition.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

@Schema(name = "StudentCreateRequest", description = "Dữ liệu tạo mới hồ sơ sinh viên kèm khoản học phí khởi tạo")
public class StudentCreateRequest {

    @NotBlank(message = "Mã số sinh viên không được để trống")
    @JsonProperty("student_code")
    @Schema(description = "Mã số sinh viên (MSSV) — không được trùng lặp trong cùng một học kỳ", example = "52400099", requiredMode = Schema.RequiredMode.REQUIRED)
    private String studentCode;

    @NotBlank(message = "Họ và tên sinh viên không được để trống")
    @JsonProperty("student_name")
    @Schema(description = "Họ và tên đầy đủ của sinh viên", example = "Nguyễn Văn Mới", requiredMode = Schema.RequiredMode.REQUIRED)
    private String studentName;

    @Schema(description = "Học kỳ áp dụng học phí", example = "HK1/2026-2027", defaultValue = "HK1/2026-2027")
    private String term = "HK1/2026-2027";

    @NotNull(message = "Số tiền học phí không được để trống")
    @Min(value = 100000, message = "Số tiền học phí tối thiểu là 100,000 VND")
    @Schema(description = "Số tiền học phí cần thu (tối thiểu 100,000 VND)", example = "1000000", requiredMode = Schema.RequiredMode.REQUIRED)
    private Long amount;

    @Schema(description = "Trạng thái khởi tạo của học phí: 'UNPAID' (mặc định) hoặc 'PAID'", allowableValues = {"UNPAID", "PAID"}, defaultValue = "UNPAID")
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
