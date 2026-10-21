package com.soa.tuition.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.soa.tuition.entity.TuitionInvoice;

import java.util.UUID;

public class StudentResponse {
    private UUID id;

    @JsonProperty("student_code")
    private String studentCode;

    @JsonProperty("student_name")
    private String studentName;

    private String term;
    private Long amount;
    private String status;

    @JsonProperty("reserved_by_payment_id")
    private UUID reservedByPaymentId;

    @JsonProperty("paid_by_payment_id")
    private UUID paidByPaymentId;

    public StudentResponse() {}

    public static StudentResponse fromEntity(TuitionInvoice invoice) {
        StudentResponse res = new StudentResponse();
        res.setId(invoice.getId());
        res.setStudentCode(invoice.getStudent().getStudentCode());
        res.setStudentName(invoice.getStudent().getFullName());
        res.setTerm(invoice.getTerm());
        res.setAmount(invoice.getAmount());
        res.setStatus(invoice.getStatus());
        res.setReservedByPaymentId(invoice.getReservedByPaymentId());
        res.setPaidByPaymentId(invoice.getPaidByPaymentId());
        return res;
    }

    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }
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
    public UUID getReservedByPaymentId() { return reservedByPaymentId; }
    public void setReservedByPaymentId(UUID reservedByPaymentId) { this.reservedByPaymentId = reservedByPaymentId; }
    public UUID getPaidByPaymentId() { return paidByPaymentId; }
    public void setPaidByPaymentId(UUID paidByPaymentId) { this.paidByPaymentId = paidByPaymentId; }
}
