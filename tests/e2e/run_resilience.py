"""Prove Saga recovery and durable notification delivery after a worker outage."""
from __future__ import annotations
import json, subprocess, time
from run_concurrency import account, create_payment, email_texts, login, otp_for, request

if __name__ == "__main__":
    token = login("dinhthanhphong")
    before = account(token)["available_balance"]
    payment = create_payment(token, "52400003")
    otp = otp_for(payment["id"])
    subprocess.run(["docker", "compose", "stop", "notification"], check=True)
    try:
        status, body = request("POST", f"/api/v1/payments/{payment['id']}/otp/verify", token=token, idempotency=True, extra_headers={"X-Fault-Point":"after_debit"}, body={"otp": otp})
        assert status == 503 and body["code"] == "SAGA_RECOVERY_PENDING", body
        result = None
        for _ in range(20):
            time.sleep(1)
            status, result = request("GET", f"/api/v1/payments/{payment['id']}", token=token)
            if result.get("status") == "SUCCEEDED": break
        assert result and result["status"] == "SUCCEEDED", result
        assert account(token)["available_balance"] == before - payment["amount"]
    finally:
        subprocess.run(["docker", "compose", "start", "notification"], check=True)

    delivered = False
    for _ in range(60):
        for text in email_texts():
            if payment["id"] in text and "thành công" in text:
                delivered = True; break
        if delivered: break
        time.sleep(1)
    assert delivered, "Confirmation email was not delivered after notification worker restart"
    print(json.dumps({"fault_after_debit_recovery":"PASS","notification_outage_retry":"PASS","no_double_debit":"PASS"}, indent=2))
