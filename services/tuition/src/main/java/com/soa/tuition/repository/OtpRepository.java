package com.soa.tuition.repository;

import com.soa.tuition.entity.OtpRecord;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;
import java.util.UUID;

@Repository
public interface OtpRepository extends JpaRepository<OtpRecord, UUID> {
    Optional<OtpRecord> findFirstByOtpCodeAndUsedFalseOrderByCreatedAtDesc(String otpCode);
    Optional<OtpRecord> findFirstByEmailAndUsedFalseOrderByCreatedAtDesc(String email);
}
