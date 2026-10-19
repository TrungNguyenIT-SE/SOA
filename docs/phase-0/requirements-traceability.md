# Ma trận truy vết yêu cầu

## 1. Cách sử dụng

- Đây là bản đồ từ yêu cầu nguồn đến thiết kế, hiện thực, test và minh chứng demo.
- Trạng thái `PLANNED` ở Giai đoạn 0 nghĩa là đích truy vết đã xác định nhưng chưa được hiện thực.
- Khi tạo file/code thật, thay đường dẫn dự kiến bằng đường dẫn chính xác và chuyển trạng thái qua `IN_PROGRESS`, `VERIFIED`.
- Một yêu cầu chỉ `VERIFIED` khi test tự động pass và có bằng chứng demo/tài liệu tương ứng.

## 2. Truy vết yêu cầu nghiệp vụ

| Req | Nguồn | Service chịu trách nhiệm | API dự kiến | Dữ liệu/invariant | UI | Test bắt buộc | Demo | Rubric | Trạng thái |
|---|---|---|---|---|---|---|---|---|---|
| BR-01 | de1 trang 1 | Django Web/Identity | `POST /api/v1/auth/login` | users/password hash | Login | UT auth; API 200/401; E2E login | Demo 1 | 5,7 | PLANNED |
| BR-02 | de1 trang 1 | Django Identity + FastAPI Account | `GET /users/me`, `/accounts/me`, `/transactions` | users, accounts, ledger; auth ownership | Dashboard/history | authorization + persistence + E2E | Demo 1 | 4,5,7 | PLANNED |
| BR-03 | de1 trang 1 | Django Identity + FastAPI Payment | user/profile APIs; `POST /payments` | INV-07 payer từ token | Form payer read-only | tampered payer/account test | Demo 1 | 3,5,7 | PLANNED |
| BR-04 | de1 trang 1 và de2 trang 2 | FastAPI Tuition | `GET /tuition-invoices/by-student/{studentCode}` | students, invoices; amount server-owned | MSSV lookup | found/not-found/paid/no-partial tests | Demo 1/2 | 3,4,5,7 | PLANNED |
| BR-05 | de2 trang 2 | FastAPI Payment/Account/Tuition | `POST /payments` | invoice UNPAID; balance >= amount | Điều khoản + confirm state | invalid/missing/insufficient/already-paid | Demo 2 | 3,5 | PLANNED |
| BR-06 | de2 trang 2 | FastAPI Payment + Notification | create payment; `/otp/verify`, `/otp/resend` | OTP fingerprint, TTL, status; INV-06 | OTP/countdown/resend | wrong/expired/reuse/concurrent/resend/email | Demo 1/2 | 5 | PLANNED |
| BR-07 | de2 trang 2 | FastAPI Payment/Account/Tuition/Notification | verify + internal debit/reserve/paid | payments, ledger, invoices, outbox; INV-02..05 | Result/history | E2E happy path; retry; email | Demo 1 | 4,5,6,7 | PLANNED |
| BR-08 | de3 trang 3 | FastAPI Account/Tuition/Payment | internal debit/reserve/compensate | INV-01..09; locks/CAS/Saga | Processing/final result | CT-01, CT-02, recovery/fault tests | Demo 3/4/5 | 2,6,8 | PLANNED |

## 3. Truy vết yêu cầu phi chức năng

| NFR | Thiết kế/hiện thực dự kiến | Test/kiểm tra | Bằng chứng | Trạng thái |
|---|---|---|---|---|
| NFR-01 Microservices | Gateway; 5 deployable service; DB ownership | Compose inspection; gọi qua network; cấm DB user chéo | Architecture/deployment diagram + container list | PLANNED |
| NFR-02 FastAPI + Django | Django Web/Identity; FastAPI Account/Tuition/Payment/Notification | Build/import/start từng app | Source tree + runtime logs | PLANNED |
| NFR-03 Security | Django auth/JWT; authorization; OTP HMAC; rate limit | authz, secret scan, OTP redaction tests | Security checklist/test report | PLANNED |
| NFR-04 Consistency | Local ACID, Saga, Outbox/Inbox, idempotency | integration/concurrency/failure tests | ADR + test logs | PLANNED |
| NFR-05 Observability | JSON log, correlation ID, OpenTelemetry | One request trace xuyên service | Trace screenshot/log query | PLANNED |
| NFR-06 API quality | FastAPI OpenAPI + DRF schema + common errors | schema validation/contract tests | Swagger/ReDoc | PLANNED |
| NFR-07 Persistence | PostgreSQL + Django Migration/Alembic | migration up; restart persistence; constraints | Migration/test output | PLANNED |
| NFR-08 Deployment | Dockerfiles + Compose + healthcheck | máy sạch `docker compose up --build` | README/rehearsal log | PLANNED |
| NFR-09 Testing | Pytest, pytest-django, HTTPX, Playwright, concurrency | CI quality gate | Test reports | PLANNED |
| NFR-10 Usability | Django Templates + HTMX/Alpine; responsive states | E2E + manual viewport check | UI screenshots/demo | PLANNED |
| NFR-11 Resilience | retry/backoff, DLQ, recovery/reconciliation | stop/restart dependency; duplicate event | Failure demo/report | PLANNED |
| NFR-12 Documentation | README, diagrams, ADR, API, test/demo docs | link/file audit; clean-machine run | docs index | PLANNED |

## 4. Truy vết hai concurrency scenario bắt buộc

| Scenario | Fixture | Điểm tranh chấp | Cơ chế dự kiến | Assertion cuối | Evidence |
|---|---|---|---|---|---|
| CT-01 - cùng account | Balance 1.500.000; hai invoice 1.000.000 | account row/balance | Atomic conditional debit hoặc row lock; unique debit by payment | 1 success; balance 500.000; 1 debit; không âm; chỉ invoice thắng paid | `tests/concurrency/test_same_account.py` + report/log |
| CT-02 - cùng invoice | Hai account đủ tiền; một invoice 1.000.000 | tuition invoice row/status | Atomic conditional reservation; reservation owner paymentId; compensation nếu cần | 1 success; invoice paid 1 lần; account thua không mất tiền | `tests/concurrency/test_same_invoice.py` + report/log |

## 5. Truy vết rubric sang hiện vật

| Tiêu chí | Điểm | Hiện vật dự kiến | Test/demo chứng minh | Gate |
|---|---:|---|---|---|
| 1. Phân tích nghiệp vụ & UML | 1.0 | `docs/diagrams/use-case.*`, `erd-overview.*` | Diagram review với BR/AC | Không merge thiết kế nếu thiếu |
| 2. Kiến trúc Microservices | 1.5 | architecture/deployment diagrams + ADR | containers, network calls, trace | Cap 6.5 nếu chỉ monolith; cap 8 nếu thiếu architecture diagram |
| 3. REST API | 1.0 | OpenAPI/Swagger/ReDoc + error catalog | contract/API tests | API review gate |
| 4. Database & Persistence | 1.0 | migrations, constraints, seed | PostgreSQL integration tests | migration/constraint gate |
| 5. Chức năng & Payment Workflow | 2.0 | services + Web UI + email | E2E happy/error/OTP | Cap 7 nếu thiếu OTP |
| 6. Transaction & Concurrency | 1.5 | Saga/Outbox/idempotency/locks | CT-01, CT-02, failure tests | Cap 7.5 nếu thiếu giải pháp |
| 7. UI & Integration | 0.5 | Django Web hoàn chỉnh | Playwright/live demo | E2E gate |
| 8. Docs/Deployment/Demo | 1.5 | README, Compose, docs, demo script | clean-machine rehearsal | Cap 4 nếu không chạy/demo |

## 6. Traceability gate cho Pull Request

PR thay đổi nghiệp vụ chỉ được duyệt khi:

1. Ghi mã BR/AC/NFR/backlog liên quan.
2. Chỉ rõ API/data/state bị ảnh hưởng.
3. Thêm/cập nhật test tương ứng.
4. Cập nhật diagram/OpenAPI/ADR nếu contract hoặc kiến trúc đổi.
5. Cập nhật cột trạng thái và đường dẫn bằng chứng trong ma trận này khi hạng mục được xác minh.

