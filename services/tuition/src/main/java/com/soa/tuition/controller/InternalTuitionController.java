package com.soa.tuition.controller;

import com.soa.tuition.dto.ReservationRequest;
import com.soa.tuition.dto.StudentResponse;
import com.soa.tuition.dto.SyncStatusRequest;
import com.soa.tuition.entity.TuitionInvoice;
import com.soa.tuition.exception.AppException;
import com.soa.tuition.repository.TuitionInvoiceRepository;
import com.soa.tuition.service.StudentService;
import io.swagger.v3.oas.annotations.Hidden;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;

import java.time.Duration;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;

@RestController
@Hidden
public class InternalTuitionController {

    private final StudentService studentService;
    private final TuitionInvoiceRepository invoiceRepository;

    public InternalTuitionController(StudentService studentService, TuitionInvoiceRepository invoiceRepository) {
        this.studentService = studentService;
        this.invoiceRepository = invoiceRepository;
    }

    @PostMapping("/internal/v1/students/{student_code}/sync-status")
    public ResponseEntity<Map<String, String>> syncStatus(
            @PathVariable("student_code") String studentCode,
            @RequestBody SyncStatusRequest req) {
        studentService.syncStatus(studentCode, req.getStatus());
        return ResponseEntity.ok(Map.of(
                "status", "success",
                "student_code", studentCode,
                "synced_status", req.getStatus()
        ));
    }

    @GetMapping("/internal/v1/tuition-invoices/{invoice_id}")
    public StudentResponse getInvoiceById(@PathVariable("invoice_id") UUID invoiceId) {
        TuitionInvoice inv = invoiceRepository.findById(invoiceId)
                .orElseThrow(() -> new AppException(HttpStatus.NOT_FOUND, "INVOICE_NOT_FOUND", "Không tìm thấy khoản học phí: " + invoiceId));
        return StudentResponse.fromEntity(inv);
    }

    @PostMapping("/internal/v1/tuition-invoices/{invoice_id}/reservations")
    @Transactional
    public StudentResponse reserveInvoice(@PathVariable("invoice_id") UUID invoiceId,
                                          @RequestBody ReservationRequest req) {
        TuitionInvoice inv = invoiceRepository.findById(invoiceId)
                .orElseThrow(() -> new AppException(HttpStatus.NOT_FOUND, "INVOICE_NOT_FOUND", "Không tìm thấy khoản học phí: " + invoiceId));

        if ("RESERVED".equals(inv.getStatus()) && req.getPaymentId().equals(inv.getReservedByPaymentId())) {
            return StudentResponse.fromEntity(inv);
        }
        if (!"UNPAID".equals(inv.getStatus())) {
            throw new AppException(HttpStatus.CONFLICT, "TUITION_UNAVAILABLE", "Khoản học phí đã được xử lý bởi giao dịch khác.");
        }

        inv.setStatus("RESERVED");
        inv.setReservedByPaymentId(req.getPaymentId());
        inv.setReservationExpiresAt(Instant.now().plus(Duration.ofMinutes(10)));
        inv.setVersion(inv.getVersion() + 1);
        invoiceRepository.save(inv);

        return StudentResponse.fromEntity(inv);
    }

    @PostMapping("/internal/v1/tuition-invoices/{invoice_id}/mark-paid")
    @Transactional
    public StudentResponse markPaid(@PathVariable("invoice_id") UUID invoiceId,
                                    @RequestBody ReservationRequest req) {
        TuitionInvoice inv = invoiceRepository.findById(invoiceId)
                .orElseThrow(() -> new AppException(HttpStatus.NOT_FOUND, "INVOICE_NOT_FOUND", "Không tìm thấy khoản học phí: " + invoiceId));

        if ("PAID".equals(inv.getStatus()) && req.getPaymentId().equals(inv.getPaidByPaymentId())) {
            return StudentResponse.fromEntity(inv);
        }

        inv.setStatus("PAID");
        inv.setPaidByPaymentId(req.getPaymentId());
        inv.setPaidAt(Instant.now());
        inv.setReservedByPaymentId(null);
        inv.setReservationExpiresAt(null);
        inv.setVersion(inv.getVersion() + 1);
        invoiceRepository.save(inv);

        return StudentResponse.fromEntity(inv);
    }

    @DeleteMapping("/internal/v1/tuition-invoices/{invoice_id}/reservations/{payment_id}")
    @Transactional
    public StudentResponse releaseReservation(@PathVariable("invoice_id") UUID invoiceId,
                                              @PathVariable("payment_id") UUID paymentId) {
        TuitionInvoice inv = invoiceRepository.findById(invoiceId)
                .orElseThrow(() -> new AppException(HttpStatus.NOT_FOUND, "INVOICE_NOT_FOUND", "Không tìm thấy khoản học phí: " + invoiceId));

        if ("RESERVED".equals(inv.getStatus()) && paymentId.equals(inv.getReservedByPaymentId())) {
            inv.setStatus("UNPAID");
            inv.setReservedByPaymentId(null);
            inv.setReservationExpiresAt(null);
            inv.setVersion(inv.getVersion() + 1);
            invoiceRepository.save(inv);
        }
        return StudentResponse.fromEntity(inv);
    }
}
