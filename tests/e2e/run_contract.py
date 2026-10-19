"""Contract, validation, authorization and idempotency checks against Compose."""
from __future__ import annotations

import concurrent.futures
import json
import threading
import uuid

from run_concurrency import login, request


def assert_error(status, body, expected_status, code):
    assert status == expected_status, body
    assert body["code"] == code, body
    assert body["status"] == expected_status, body
    assert body["correlationId"], body
    assert "timestamp" in body and "fieldErrors" in body and "path" in body, body


if __name__ == "__main__":
    status, body = request("POST", "/api/v1/auth/login", body={"username": "hoangthaidangkhoa", "password": "wrong"})
    assert_error(status, body, 401, "INVALID_CREDENTIALS")

    status, body = request("GET", "/api/v1/accounts/me")
    assert_error(status, body, 401, "UNAUTHORIZED")

    token = login("hoangthaidangkhoa")
    other = login("dinhthanhphong")
    status, body = request("GET", "/api/v1/tuition-invoices/by-student/bad!", token=token)
    assert_error(status, body, 422, "VALIDATION_ERROR")
    status, body = request("GET", "/api/v1/tuition-invoices/by-student/52400004", token=token)
    assert_error(status, body, 409, "TUITION_ALREADY_PAID")

    key = str(uuid.uuid4())
    payload = {"student_code": "52400002", "accepted_terms": True}
    barrier = threading.Barrier(2)
    def create_once():
        barrier.wait()
        return request("POST", "/api/v1/payments", token=token, body=payload, idempotency=key)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        concurrent_results = [future.result() for future in [pool.submit(create_once), pool.submit(create_once)]]
    assert all(status == 201 for status, _ in concurrent_results), concurrent_results
    assert len({body["id"] for _, body in concurrent_results}) == 1, concurrent_results
    payment = concurrent_results[0][1]
    status, same = request("POST", "/api/v1/payments", token=token, body=payload, idempotency=key)
    assert status == 201 and same["id"] == payment["id"], same
    status, body = request("POST", "/api/v1/payments", token=token, body={"student_code": "52400003", "accepted_terms": True}, idempotency=key)
    assert_error(status, body, 409, "IDEMPOTENCY_KEY_REUSED")

    status, body = request("GET", f"/api/v1/payments/{payment['id']}", token=other)
    assert_error(status, body, 404, "PAYMENT_NOT_FOUND")
    status, body = request("POST", f"/api/v1/payments/{payment['id']}/otp/resend", token=token)
    assert_error(status, body, 429, "OTP_RESEND_COOLDOWN")

    verify_key = str(uuid.uuid4())
    status, body = request("POST", f"/api/v1/payments/{payment['id']}/otp/verify", token=token, body={"otp": "000000"}, idempotency=verify_key)
    assert_error(status, body, 422, "OTP_INVALID")
    status, body = request("POST", f"/api/v1/payments/{payment['id']}/otp/verify", token=token, body={"otp": "111111"}, idempotency=verify_key)
    assert_error(status, body, 409, "IDEMPOTENCY_KEY_REUSED")

    print(json.dumps({"error_model": "PASS", "authorization": "PASS", "create_idempotency": "PASS", "idempotency_conflict": "PASS", "resend_rate_limit": "PASS"}, indent=2))
