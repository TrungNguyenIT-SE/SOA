"""Run the two concurrency scenarios against the Docker Compose stack.

The stack must be freshly seeded because the fixtures are intentionally consumed.
"""

from __future__ import annotations

import concurrent.futures
import email
import imaplib
import json
import os
import re
import time
import urllib.error
import urllib.request
import uuid
from email import policy

BASE_URL = "http://localhost:8080"
IMAP_HOST = os.getenv("IMAP_HOST", "imap.gmail.com")
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
IMAP_USERNAME = os.getenv("IMAP_USERNAME", os.getenv("SMTP_USERNAME", ""))
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD", os.getenv("SMTP_PASSWORD", ""))


def request(method: str, path: str, *, token: str | None = None, body: dict | None = None, idempotency: bool | str = False, extra_headers: dict | None = None) -> tuple[int, dict]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if idempotency:
        headers["Idempotency-Key"] = idempotency if isinstance(idempotency, str) else str(uuid.uuid4())
    headers.update(extra_headers or {})
    payload = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE_URL + path, data=payload, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def login(username: str) -> str:
    status, body = request("POST", "/api/v1/auth/login", body={"username": username, "password": "Password123@"})
    assert status == 200, body
    return body["access"]


def create_payment(token: str, student_code: str) -> dict:
    status, body = request(
        "POST",
        "/api/v1/payments",
        token=token,
        idempotency=True,
        body={"student_code": student_code, "accepted_terms": True},
    )
    assert status == 201, body
    return body


def email_texts() -> list[str]:
    if not IMAP_USERNAME or not IMAP_PASSWORD:
        raise RuntimeError("Thiếu IMAP_USERNAME/IMAP_PASSWORD để kiểm tra email E2E thật")
    mailbox = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    try:
        mailbox.login(IMAP_USERNAME, IMAP_PASSWORD)
        mailbox.select("INBOX", readonly=True)
        status, data = mailbox.search(None, "ALL")
        if status != "OK":
            return []
        texts = []
        for message_id in reversed(data[0].split()[-50:]):
            status, parts = mailbox.fetch(message_id, "(RFC822)")
            if status != "OK" or not parts or not isinstance(parts[0], tuple):
                continue
            message = email.message_from_bytes(parts[0][1], policy=policy.default)
            body = message.get_body(preferencelist=("plain",))
            texts.append(body.get_content() if body else "")
        return texts
    finally:
        try:
            mailbox.logout()
        except imaplib.IMAP4.error:
            pass


def otp_for(payment_id: str) -> str:
    for _ in range(60):
        for text in email_texts():
            if payment_id in text:
                candidates = re.findall(r"\b\d{6}\b", text)
                if candidates:
                    return candidates[0]
        time.sleep(1)
    raise AssertionError(f"OTP email not found for {payment_id}")


def verify_at_barrier(barrier, token: str, payment: dict, otp: str) -> tuple[int, dict]:
    barrier.wait()
    return request(
        "POST",
        f"/api/v1/payments/{payment['id']}/otp/verify",
        token=token,
        idempotency=True,
        body={"otp": otp},
    )


def account(token: str) -> dict:
    status, body = request("GET", "/api/v1/accounts/me", token=token)
    assert status == 200, body
    return body


def history(token: str) -> list[dict]:
    status, body = request("GET", "/api/v1/accounts/me/transactions", token=token)
    assert status == 200, body
    return body["items"]


def run_pair(calls: list[tuple[str, dict, str]]) -> list[tuple[int, dict]]:
    import threading

    barrier = threading.Barrier(len(calls))
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(calls)) as pool:
        futures = [pool.submit(verify_at_barrier, barrier, token, payment, otp) for token, payment, otp in calls]
        return [future.result(timeout=30) for future in futures]


def same_account() -> dict:
    token = login("nguyentrungnguyen")
    starting_balance = account(token)["available_balance"]
    first = create_payment(token, "52400005")
    second = create_payment(token, "52400006")
    results = run_pair([(token, first, otp_for(first["id"])), (token, second, otp_for(second["id"]))])
    successes = [body for status, body in results if status == 200 and body.get("status") == "SUCCEEDED"]
    failures = [(status, body) for status, body in results if not (status == 200 and body.get("status") == "SUCCEEDED")]
    final_account = account(token)
    entries = history(token)
    assert len(successes) == 1, results
    assert len(failures) == 1, results
    relevant = [entry for entry in entries if entry["type"] == "DEBIT" and entry["payment_id"] in {first["id"], second["id"]}]
    assert final_account["available_balance"] == starting_balance - 1_000_000, final_account
    assert len(relevant) == 1, entries
    return {"scenario": "same-account", "results": results, "balance": final_account["available_balance"], "debits": len(relevant)}


def same_invoice() -> dict:
    first_token = login("hoangthaidangkhoa")
    second_token = login("dinhthanhphong")
    starting_total = account(first_token)["available_balance"] + account(second_token)["available_balance"]
    first = create_payment(first_token, "52400007")
    second = create_payment(second_token, "52400007")
    results = run_pair(
        [
            (first_token, first, otp_for(first["id"])),
            (second_token, second, otp_for(second["id"])),
        ]
    )
    successes = [body for status, body in results if status == 200 and body.get("status") == "SUCCEEDED"]
    failures = [(status, body) for status, body in results if not (status == 200 and body.get("status") == "SUCCEEDED")]
    first_account = account(first_token)
    second_account = account(second_token)
    payment_ids = {first["id"], second["id"]}
    debit_count = len([entry for entry in history(first_token) + history(second_token) if entry["type"] == "DEBIT" and entry["payment_id"] in payment_ids])
    assert len(successes) == 1, results
    assert len(failures) == 1, results
    assert first_account["available_balance"] + second_account["available_balance"] == starting_total - 1_000_000, (first_account, second_account)
    assert debit_count == 1, debit_count
    return {
        "scenario": "same-invoice",
        "results": results,
        "combined_balance": first_account["available_balance"] + second_account["available_balance"],
        "debits": debit_count,
    }


if __name__ == "__main__":
    report = {"same_account": same_account(), "same_invoice": same_invoice()}
    print(json.dumps(report, indent=2, ensure_ascii=True))

