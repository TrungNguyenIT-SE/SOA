package com.soa.tuition.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.UUID;

public class ReservationRequest {

    @JsonProperty("payment_id")
    private UUID paymentId;

    public ReservationRequest() {}
    public ReservationRequest(UUID paymentId) { this.paymentId = paymentId; }

    public UUID getPaymentId() { return paymentId; }
    public void setPaymentId(UUID paymentId) { this.paymentId = paymentId; }
}
