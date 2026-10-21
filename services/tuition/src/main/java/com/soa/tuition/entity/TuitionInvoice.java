package com.soa.tuition.entity;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "tuition_invoices", uniqueConstraints = {
        @UniqueConstraint(name = "uq_student_term", columnNames = {"student_id", "term"})
})
public class TuitionInvoice {

    @Id
    @GeneratedValue(strategy = GenerationType.AUTO)
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "student_id", nullable = false)
    private Student student;

    @Column(name = "term", nullable = false, length = 40)
    private String term;

    @Column(name = "amount", nullable = false)
    private Long amount;

    @Column(name = "status", nullable = false, length = 20)
    private String status = "UNPAID";

    @Column(name = "reserved_by_payment_id")
    private UUID reservedByPaymentId;

    @Column(name = "reservation_expires_at")
    private Instant reservationExpiresAt;

    @Column(name = "paid_by_payment_id")
    private UUID paidByPaymentId;

    @Column(name = "paid_at")
    private Instant paidAt;

    @Version
    @Column(name = "version")
    private Integer version = 0;

    public TuitionInvoice() {}

    public TuitionInvoice(Student student, String term, Long amount, String status) {
        this.student = student;
        this.term = term;
        this.amount = amount;
        this.status = status;
        if ("PAID".equalsIgnoreCase(status)) {
            this.paidAt = Instant.now();
        }
    }

    public UUID getId() {
        return id;
    }

    public void setId(UUID id) {
        this.id = id;
    }

    public Student getStudent() {
        return student;
    }

    public void setStudent(Student student) {
        this.student = student;
    }

    public String getTerm() {
        return term;
    }

    public void setTerm(String term) {
        this.term = term;
    }

    public Long getAmount() {
        return amount;
    }

    public void setAmount(Long amount) {
        this.amount = amount;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public UUID getReservedByPaymentId() {
        return reservedByPaymentId;
    }

    public void setReservedByPaymentId(UUID reservedByPaymentId) {
        this.reservedByPaymentId = reservedByPaymentId;
    }

    public Instant getReservationExpiresAt() {
        return reservationExpiresAt;
    }

    public void setReservationExpiresAt(Instant reservationExpiresAt) {
        this.reservationExpiresAt = reservationExpiresAt;
    }

    public UUID getPaidByPaymentId() {
        return paidByPaymentId;
    }

    public void setPaidByPaymentId(UUID paidByPaymentId) {
        this.paidByPaymentId = paidByPaymentId;
    }

    public Instant getPaidAt() {
        return paidAt;
    }

    public void setPaidAt(Instant paidAt) {
        this.paidAt = paidAt;
    }

    public Integer getVersion() {
        return version;
    }

    public void setVersion(Integer version) {
        this.version = version;
    }
}
