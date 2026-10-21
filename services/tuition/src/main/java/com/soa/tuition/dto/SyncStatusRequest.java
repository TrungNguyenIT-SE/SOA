package com.soa.tuition.dto;

public class SyncStatusRequest {
    private String status;

    public SyncStatusRequest() {}
    public SyncStatusRequest(String status) { this.status = status; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
}
