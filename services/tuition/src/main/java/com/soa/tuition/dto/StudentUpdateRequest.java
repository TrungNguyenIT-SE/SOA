package com.soa.tuition.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public class StudentUpdateRequest {

    @JsonProperty("full_name")
    private String fullName;

    private String term;
    private Long amount;
    private String status;

    @JsonProperty("payer_user_id")
    private Integer payerUserId;

    public StudentUpdateRequest() {}

    public String getFullName() { return fullName; }
    public void setFullName(String fullName) { this.fullName = fullName; }
    public String getTerm() { return term; }
    public void setTerm(String term) { this.term = term; }
    public Long getAmount() { return amount; }
    public void setAmount(Long amount) { this.amount = amount; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public Integer getPayerUserId() { return payerUserId; }
    public void setPayerUserId(Integer payerUserId) { this.payerUserId = payerUserId; }
}
