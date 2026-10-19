"""Exercise the complete login -> lookup -> OTP -> payment -> history flow."""

from __future__ import annotations

import json
import time

from run_concurrency import account, create_payment, history, login, otp_for, request


if __name__ == "__main__":
    token = login("hoangthaidangkhoa")
    before = account(token)

    lookup_status, tuition = request("GET", "/api/v1/tuition-invoices/by-student/52400001", token=token)
    assert lookup_status == 200, tuition

    payment = create_payment(token, "52400001")
    otp = otp_for(payment["id"])
    verify_status, result = request(
        "POST",
        f"/api/v1/payments/{payment['id']}/otp/verify",
        token=token,
        idempotency=True,
        body={"otp": otp},
    )
    assert verify_status == 200, result
    assert result["status"] == "SUCCEEDED", result

    after = account(token)
    entries = history(token)
    assert before["available_balance"] - after["available_balance"] == tuition["amount"], (before, after, tuition)
    assert any(entry["payment_id"] == payment["id"] and entry["type"] == "DEBIT" for entry in entries), entries

    retry_status, retry = request(
        "POST",
        f"/api/v1/payments/{payment['id']}/otp/verify",
        token=token,
        idempotency=True,
        body={"otp": otp},
    )
    assert retry_status == 200 and retry["status"] == "SUCCEEDED", retry
    assert account(token)["available_balance"] == after["available_balance"], "OTP retry caused a second debit"

    time.sleep(2)
    report = {
        "login": "PASS",
        "lookup": "PASS",
        "otp_email": "PASS",
        "payment": result["status"],
        "balance_before": before["available_balance"],
        "balance_after": after["available_balance"],
        "history_entry": "PASS",
        "one_time_idempotent_retry": "PASS",
    }
    print(json.dumps(report, indent=2, ensure_ascii=True))

