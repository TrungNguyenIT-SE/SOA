#!/usr/bin/env python3
"""
Test đồng bộ tương tác 2 chiều giữa Web Local (Gateway :8080) và Swagger của 3 thành viên:
- Khoa: Python FastAPI (:8001 / :8002)
- Nguyên: Java Spring Boot (:8003)
- Phong: C# .NET 8 (:8004)
"""

import json
import sys
import io
import time
import urllib.error
import urllib.request
import uuid

# Force UTF-8 on Windows terminal
if sys.platform.startswith("win"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

GATEWAY_URL = "http://localhost:8080"
KHOA_IDENTITY_URL = "http://localhost:8001"
KHOA_ACCOUNT_URL = "http://localhost:8002"
NGUYEN_TUITION_URL = "http://localhost:8003"
PHONG_PAYMENT_URL = "http://localhost:8004"


def http_request(method: str, url: str, data: dict = None, headers: dict = None):
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    payload = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=payload, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            content = resp.read().decode("utf-8")
            return resp.status, json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        err_content = e.read().decode("utf-8")
        try:
            return e.code, json.loads(err_content)
        except Exception:
            return e.code, {"error": err_content}
    except Exception as e:
        return 500, {"error": str(e)}


def print_test_result(test_name: str, passed: bool, detail: str = ""):
    status_str = "\033[92m[PASS]\033[0m" if passed else "\033[91m[FAIL]\033[0m"
    print(f" {status_str} {test_name}")
    if detail:
        print(f"        -> {detail}")


def main():
    print("=" * 70)
    print("  KIỂM THỬ ĐỒNG BỘ 2 CHIỀU: WEB LOCAL (:8080) <---> SWAGGER UI (:8001 - :8004)")
    print("=" * 70)

    results = []

    # =========================================================================
    # PHẦN 1: BẠN 1 - KHOA (Python FastAPI: Web-Identity :8001 & Account :8002)
    # =========================================================================
    print("\n--- [1] KIỂM THỬ BẠN 1: KHOA (Python FastAPI Identity :8001 & Account :8002) ---")
    test_username = f"sync_test_{int(time.time())}"
    test_email = f"{test_username}@example.com"
    created_user_id = None

    # 1.1 Web -> Swagger: Thêm user qua Web Gateway (:8080) -> Đọc tại Swagger (:8001)
    status, res = http_request(
        "POST",
        f"{GATEWAY_URL}/api/v1/users",
        data={
            "username": test_username,
            "password": "Password123@",
            "full_name": "Nguyen Van Test WebToSwagger",
            "phone": "0909999001",
            "email": test_email,
            "balance": 3500000,
        },
    )
    passed_1_1_create = status in [200, 201] and "id" in res
    if passed_1_1_create:
        created_user_id = res["id"]

    # Đọc trực tiếp từ Swagger Port :8001
    status_get, user_from_swagger = http_request("GET", f"{KHOA_IDENTITY_URL}/api/v1/users/{created_user_id}")
    passed_1_1 = passed_1_1_create and status_get == 200 and user_from_swagger.get("username") == test_username
    print_test_result(
        "1.1 [Web -> Swagger]: Tạo user trên Web (:8080) -> Đọc thấy ngay trên Swagger Khoa (:8001)",
        passed_1_1,
        f"User ID #{created_user_id}, Name: {user_from_swagger.get('full_name')}",
    )
    results.append(("Khoa 1.1 Web->Swagger", passed_1_1))

    # 1.2 Swagger -> Web: Sửa user trên Swagger Port (:8001) -> Đọc qua Web Gateway (:8080)
    updated_name = "Nguyen Van Da Sua Qua Swagger"
    status_put, _ = http_request(
        "PUT",
        f"{KHOA_IDENTITY_URL}/api/v1/users/{created_user_id}",
        data={"full_name": updated_name, "balance": 7200000},
    )
    # Đọc lại từ Web Gateway (:8080)
    status_web_get, user_from_web = http_request("GET", f"{GATEWAY_URL}/api/v1/users/{created_user_id}")
    passed_1_2 = (
        status_put == 200
        and status_web_get == 200
        and user_from_web.get("full_name") == updated_name
        and user_from_web.get("balance") == 7200000
    )
    print_test_result(
        "1.2 [Swagger -> Web]: Sửa họ tên & số dư trên Swagger (:8001) -> Web (:8080) cập nhật tức thì",
        passed_1_2,
        f"Tên mới: {user_from_web.get('full_name')}, Số dư mới: {(user_from_web.get('balance') or 0):,} đ",
    )
    results.append(("Khoa 1.2 Swagger->Web", passed_1_2))

    # Dọn dẹp user test
    if created_user_id:
        http_request("DELETE", f"{KHOA_IDENTITY_URL}/api/v1/users/{created_user_id}")

    # =========================================================================
    # PHẦN 2: BẠN 2 - NGUYÊN (Java 17 Spring Boot: Tuition & OTP :8003)
    # =========================================================================
    print("\n--- [2] KIỂM THỬ BẠN 2: NGUYÊN (Java Spring Boot Tuition & OTP :8003) ---")
    test_code_1 = f"SVW{int(time.time()) % 100000}"
    test_code_2 = f"SVS{int(time.time()) % 100000}"

    # 2.1 Web -> Swagger: Thêm sinh viên qua Web (:8080) -> Tra cứu trên Swagger Java (:8003)
    status_stu, _ = http_request(
        "POST",
        f"{GATEWAY_URL}/api/v1/students",
        data={
            "student_code": test_code_1,
            "student_name": "Sinh Vien Web To Java",
            "term": "HK1/2026-2027",
            "amount": 1600000,
            "status": "UNPAID",
        },
    )
    # Đọc trực tiếp từ Java Port :8003
    status_java, stu_from_java = http_request("GET", f"{NGUYEN_TUITION_URL}/api/v1/students/{test_code_1}")
    passed_2_1 = (
        status_stu in [200, 201]
        and status_java == 200
        and stu_from_java.get("student_code") == test_code_1
        and stu_from_java.get("amount") == 1600000
    )
    print_test_result(
        "2.1 [Web -> Swagger]: Tạo sinh viên trên Web (:8080) -> Tra cứu thấy ngay trên Swagger Java (:8003)",
        passed_2_1,
        f"MSSV: {test_code_1}, Tiền học phí: {stu_from_java.get('amount'):,} đ, Status: {stu_from_java.get('status')}",
    )
    results.append(("Nguyên 2.1 Web->Swagger", passed_2_1))

    # 2.2 Swagger -> Web: Tạo sinh viên trực tiếp trên Swagger Java (:8003) -> Tra cứu qua Web (:8080)
    status_create_java, _ = http_request(
        "POST",
        f"{NGUYEN_TUITION_URL}/api/v1/students",
        data={
            "student_code": test_code_2,
            "student_name": "Sinh Vien Tao Tu Swagger Java",
            "term": "HK1/2026-2027",
            "amount": 2100000,
            "status": "UNPAID",
        },
    )
    # Tra cứu hóa đơn học phí qua Web Gateway (:8080)
    status_inv_web, invoice_from_web = http_request(
        "GET", f"{GATEWAY_URL}/api/v1/tuition-invoices/by-student/{test_code_2}"
    )
    passed_2_2 = (
        status_create_java in [200, 201]
        and status_inv_web == 200
        and invoice_from_web.get("student_name") == "Sinh Vien Tao Tu Swagger Java"
        and invoice_from_web.get("amount") == 2100000
    )
    print_test_result(
        "2.2 [Swagger -> Web]: Tạo sinh viên trên Swagger Java (:8003) -> Web Gateway (:8080) tra cứu học phí tức thì",
        passed_2_2,
        f"Họ tên: {invoice_from_web.get('student_name')}, Số tiền: {invoice_from_web.get('amount'):,} đ",
    )
    results.append(("Nguyên 2.2 Swagger->Web", passed_2_2))

    # Dọn dẹp sinh viên test
    http_request("DELETE", f"{NGUYEN_TUITION_URL}/api/v1/students/{test_code_1}")
    http_request("DELETE", f"{NGUYEN_TUITION_URL}/api/v1/students/{test_code_2}")

    # =========================================================================
    # PHẦN 3: BẠN 3 - PHONG (C# .NET 8: Payment & Transactions :8004)
    # =========================================================================
    print("\n--- [3] KIỂM THỬ BẠN 3: PHONG (C# .NET 8 Payment & Transactions :8004) ---")
    test_tx_id = None

    # 3.1 Web -> Swagger: Tạo giao dịch trên Web Gateway (:8080) -> Đọc từ Swagger C# (:8004)
    status_tx, tx_res = http_request(
        "POST",
        f"{GATEWAY_URL}/api/v1/transactions",
        data={
            "payer_name": "Nguoi Nop Web Test",
            "payer_email": "payer_test@gmail.com",
            "student_code": "52400001",
            "student_name": "Nguyen Minh Anh",
            "term": "HK1/2026-2027",
            "amount": 1200000,
            "status": "SUCCEEDED",
        },
    )
    if status_tx in [200, 201] and "id" in tx_res:
        test_tx_id = tx_res["id"]

    # Đọc trực tiếp từ Swagger C# Port :8004
    status_csharp, tx_from_csharp = http_request("GET", f"{PHONG_PAYMENT_URL}/api/v1/transactions/{test_tx_id}")
    passed_3_1 = (
        test_tx_id is not None
        and status_csharp == 200
        and tx_from_csharp.get("payer_name") == "Nguoi Nop Web Test"
        and tx_from_csharp.get("status") == "SUCCEEDED"
    )
    print_test_result(
        "3.1 [Web -> Swagger]: Tạo giao dịch trên Web (:8080) -> Đọc thấy ngay trên Swagger C# (:8004)",
        passed_3_1,
        f"Mã GD: {test_tx_id[:8]}..., Người nộp: {tx_from_csharp.get('payer_name')}, Trạng thái: {tx_from_csharp.get('status')}",
    )
    results.append(("Phong 3.1 Web->Swagger", passed_3_1))

    # 3.2 Swagger -> Web: Sửa trạng thái thành COMPENSATED trên Swagger C# (:8004) -> Kiểm tra trên Web (:8080)
    status_update_csharp, _ = http_request(
        "PUT",
        f"{PHONG_PAYMENT_URL}/api/v1/admin/transactions/{test_tx_id}",
        data={
            "status": "COMPENSATED",
            "amount": 1200000,
            "student_name": "Nguyen Minh Anh",
            "term": "HK1/2026-2027",
        },
    )
    # Đọc lại từ Web Gateway (:8080)
    status_tx_web, tx_from_web = http_request("GET", f"{GATEWAY_URL}/api/v1/transactions/{test_tx_id}")
    passed_3_2 = status_update_csharp == 200 and status_tx_web == 200 and tx_from_web.get("status") == "COMPENSATED"
    print_test_result(
        "3.2 [Swagger -> Web]: Sửa trạng thái sang COMPENSATED trên Swagger C# (:8004) -> Web (:8080) nhận ngay",
        passed_3_2,
        f"Trạng thái mới đọc từ Web: {tx_from_web.get('status')}",
    )
    results.append(("Phong 3.2 Swagger->Web", passed_3_2))

    # Dọn dẹp giao dịch test
    if test_tx_id:
        http_request("DELETE", f"{PHONG_PAYMENT_URL}/api/v1/admin/transactions/{test_tx_id}")

    # =========================================================================
    # PHẦN 4: ĐỒNG BỘ LIÊN DỊCH VỤ SAGA (Khoa + Nguyên + Phong cùng phối hợp)
    # =========================================================================
    print("\n--- [4] KIỂM THỬ TỔNG HỢP LIÊN DỊCH VỤ SAGA (3-IN-1 INTEGRATION) ---")
    # 4.1 Đảm bảo user 2 có sẵn số dư để kiểm thử SAGA
    initial_deposit = 5000000
    http_request("PUT", f"{KHOA_IDENTITY_URL}/api/v1/users/2", data={"balance": initial_deposit})
    _, u2_before = http_request("GET", f"{KHOA_IDENTITY_URL}/api/v1/users/2")
    balance_before = u2_before.get("balance", 0)

    # Sinh viên test nộp học phí
    saga_code = f"SAGA{int(time.time()) % 10000}"
    tuition_amount = 500000
    http_request(
        "POST",
        f"{NGUYEN_TUITION_URL}/api/v1/students",
        data={
            "student_code": saga_code,
            "student_name": "Sinh Vien Test Saga Lien Dich Vu",
            "term": "HK1/2026-2027",
            "amount": tuition_amount,
            "status": "UNPAID",
        },
    )

    # Thực hiện đổi trạng thái sang PAID với payer_user_id = 2 (kích hoạt Java gọi Account trừ tiền & Payment ghi log)
    status_paid, _ = http_request(
        "PUT",
        f"{GATEWAY_URL}/api/v1/students/{saga_code}",
        data={"status": "PAID", "payer_user_id": 2},
    )

    # Đối soát lại cả 3 Swagger:
    _, u2_after = http_request("GET", f"{KHOA_IDENTITY_URL}/api/v1/users/2")
    balance_after = u2_after.get("balance", 0)
    _, saga_student = http_request("GET", f"{NGUYEN_TUITION_URL}/api/v1/students/{saga_code}")

    passed_saga_debit = (balance_before - balance_after) == tuition_amount
    passed_saga_status = saga_student.get("status") == "PAID"
    passed_saga = status_paid in [200, 204] and passed_saga_debit and passed_saga_status

    print_test_result(
        "4.1 [SAGA Liên Dịch Vụ]: Đóng học phí trên Web/Tuition -> Tự động trừ số dư Khoa & Đổi trạng thái Nguyên",
        passed_saga,
        f"Số dư trước: {balance_before:,} đ -> sau: {balance_after:,} đ (Trừ đúng {tuition_amount:,} đ), Trạng thái SV: {saga_student.get('status')}",
    )
    results.append(("SAGA 3 Dịch Vụ Phối Hợp", passed_saga))

    # Dọn dẹp & hoàn trả số dư test
    http_request("DELETE", f"{NGUYEN_TUITION_URL}/api/v1/students/{saga_code}")
    http_request("PUT", f"{KHOA_IDENTITY_URL}/api/v1/users/2", data={"balance": balance_before})

    # =========================================================================
    # TỔNG KẾT
    # =========================================================================
    print("\n" + "=" * 70)
    print("  KẾT QUẢ TỔNG HỢP KIỂM THỬ ĐỒNG BỘ 2 CHIỀU")
    print("=" * 70)
    all_passed = True
    for name, passed in results:
        status_text = "PASS" if passed else "FAIL"
        print(f"  • {name:<35}: {status_text}")
        if not passed:
            all_passed = False

    print("-" * 70)
    if all_passed:
        print(" => KẾT LUẬN: TẤT CẢ 3 DỊCH VỤ (KHOA, NGUYÊN, PHONG) ĐỒNG BỘ 2 CHIỀU 100%!")
    else:
        print(" => KẾT LUẬN: CÓ BƯỚC KIỂM THỬ CHƯA ĐẠT. VUI LÒNG KIỂM TRA LẠI.")
    print("=" * 70)


if __name__ == "__main__":
    main()
