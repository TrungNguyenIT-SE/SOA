package com.soa.tuition.entity;

import jakarta.persistence.*;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@Entity
@Table(name = "students")
public class Student {

    @Id
    @GeneratedValue(strategy = GenerationType.AUTO)
    private UUID id;

    @Column(name = "student_code", unique = true, nullable = false, length = 20)
    private String studentCode;

    @Column(name = "full_name", nullable = false, length = 160)
    private String fullName;

    @OneToMany(mappedBy = "student", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<TuitionInvoice> invoices = new ArrayList<>();

    public Student() {}

    public Student(String studentCode, String fullName) {
        this.studentCode = studentCode;
        this.fullName = fullName;
    }

    public UUID getId() {
        return id;
    }

    public void setId(UUID id) {
        this.id = id;
    }

    public String getStudentCode() {
        return studentCode;
    }

    public void setStudentCode(String studentCode) {
        this.studentCode = studentCode;
    }

    public String getFullName() {
        return fullName;
    }

    public void setFullName(String fullName) {
        this.fullName = fullName;
    }

    public List<TuitionInvoice> getInvoices() {
        return invoices;
    }

    public void setInvoices(List<TuitionInvoice> invoices) {
        this.invoices = invoices;
    }
}
