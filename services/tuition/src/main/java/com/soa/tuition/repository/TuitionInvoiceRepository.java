package com.soa.tuition.repository;

import com.soa.tuition.entity.Student;
import com.soa.tuition.entity.TuitionInvoice;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface TuitionInvoiceRepository extends JpaRepository<TuitionInvoice, UUID> {

    @Query("SELECT ti FROM TuitionInvoice ti JOIN FETCH ti.student ORDER BY ti.student.studentCode ASC")
    List<TuitionInvoice> findAllWithStudent();

    Optional<TuitionInvoice> findFirstByStudent_StudentCodeOrderByTermDesc(String studentCode);

    Optional<TuitionInvoice> findByStudentAndTerm(Student student, String term);

    Optional<TuitionInvoice> findByReservedByPaymentId(UUID paymentId);

    Optional<TuitionInvoice> findByPaidByPaymentId(UUID paymentId);
}
