# Rubric Baseline và Score Protection Gates

## 1. Mục đích

Tài liệu này sao chép có kiểm soát cấu trúc chấm điểm từ rubric và biến từng tiêu chí thành gate có bằng chứng. Đây không phải bảng tự chấm điểm. Ở Giai đoạn 0, các mục implementation vẫn là `NOT_STARTED`.

## 2. Tổng điểm chính thức

| # | Tiêu chí | Chi tiết chính thức | Điểm tối đa | Evidence bắt buộc của nhóm | Trạng thái GĐ0 |
|---|---|---|---:|---|---|
| 1 | Phân tích nghiệp vụ & UML | Use Case đúng actor/chức năng: 0.5; ERD hợp lý entity/attribute/key/relation: 0.5 | 1.0 | Use Case source/image; ERD source/image; review với BR/AC | PLANNED |
| 2 | Kiến trúc Microservices | Diagram: 0.5; phân rã/trách nhiệm: 0.5; giao tiếp service/DB/external và giải thích: 0.5 | 1.5 | Architecture/deployment diagram, ADR, container/network/trace evidence | PLANNED |
| 3 | Thiết kế REST API | Đủ API, URI/method: 0.5; model/status/validation/error: 0.5 | 1.0 | OpenAPI FastAPI/DRF, examples, error catalog, contract tests | PLANNED |
| 4 | Database & Data Persistence | DB đúng thiết kế/đủ dữ liệu: 0.5; constraint/validation/seed/persistence: 0.5 | 1.0 | Django Migration/Alembic, constraints, seed, PostgreSQL integration report | PLANNED |
| 5 | Hiện thực chức năng & Payment Workflow | Login/profile/lookup: 0.5; create/payment/check balance/status: 0.5; OTP email/TTL/one-time: 0.5; success updates/history/email: 0.5 | 2.0 | E2E UI/API/email và DB assertions | PLANNED |
| 6 | Transaction & Concurrency | Consistency: 0.5; concurrent same account: 0.5; concurrent same tuition: 0.5 | 1.5 | Saga/Outbox/idempotency evidence; CT-01 và CT-02 report | PLANNED |
| 7 | User Interface & Integration | Toàn bộ login -> lookup -> payment -> OTP -> result/history, backend thật | 0.5 | Django Web live demo + Playwright E2E | PLANNED |
| 8 | Documentation, Deployment & Demonstration | README: 0.5; deploy/integrate hoàn chỉnh, khuyến khích Compose: 0.5; demo/giải thích: 0.5 | 1.5 | README, Compose clean run, demo script/rehearsal | PLANNED |
| | **Tổng** | | **10.0** | | |

Kiểm tra tổng: `1.0 + 1.5 + 1.0 + 1.0 + 2.0 + 1.5 + 0.5 + 1.5 = 10.0`.

## 3. Mức điểm mục tiêu theo rubric

| Mức | Điều kiện tóm tắt | Quyết định của nhóm |
|---|---|---|
| < 5.0 | Thiếu nhiều chức năng hoặc không demo đầy đủ | Không chấp nhận |
| 5.0-5.9 | Chạy cơ bản, DB/API/UI; thiếu Microservices/OTP/concurrency | Không chấp nhận |
| 6.0-6.9 | Phần lớn nghiệp vụ; payment cơ bản; yêu cầu nâng cao chưa đủ | Không chấp nhận |
| 7.0-7.9 | Đủ nghiệp vụ chính, OTP/email, service giao tiếp, validation/error | Chỉ là baseline chức năng |
| 8.0-8.9 | Đủ mức 7, Microservices/REST tốt, consistency và hai concurrency case | Release gate bắt buộc |
| 9.0-9.5 | Đủ mức 8, code/kiến trúc tốt, ownership, API docs, automated test, deployment thuận tiện | Release gate bắt buộc |
| 10.0 | Engineering quality nổi bật; integration/E2E, concurrency test, idempotency, Gateway, logging/tracing; demo/bảo vệ xuất sắc | Mục tiêu chính thức |

## 4. Năm điều kiện giới hạn điểm

| Cap ID | Trường hợp | Điểm tối đa | Prevention gate | Evidence trước demo | Trạng thái GĐ0 |
|---|---|---:|---|---|---|
| CAP-01 | Không có sản phẩm khởi chạy và demo | 4.0 | G8 clean-machine run | Compose log + rehearsal checklist | RISK OPEN |
| CAP-02 | Chỉ là Monolithic Application, không có service thực sự giao tiếp | 6.5 | G1/G2 architecture/runtime | Container list + network trace + DB ownership | RISK OPEN |
| CAP-03 | Không hiện thực OTP | 7.0 | G3 OTP E2E | OTP email, TTL, one-time tests | RISK OPEN |
| CAP-04 | Không có giải pháp Transaction/Concurrency | 7.5 | G6/G7 | CT-01, CT-02, Saga/recovery report | RISK OPEN |
| CAP-05 | Không có Microservices Architecture Diagram | 8.0 | G1 diagram review | Source + exported image readable | RISK OPEN |

`RISK OPEN` tại Giai đoạn 0 chỉ có nghĩa là implementation/evidence chưa tồn tại. Không cap nào được phép còn `RISK OPEN` trước release demo.

## 5. Rubric evidence register

| Evidence ID | Dự kiến đường dẫn/URL | Chủ sở hữu | Gate |
|---|---|---|---|
| EV-01 | `docs/diagrams/use-case.*` | EP-01 owner | G1 |
| EV-02 | `docs/diagrams/erd-overview.*` | EP-01 owner | G1 |
| EV-03 | `docs/diagrams/microservices-architecture.*` | EP-01 owner | G1/CAP-05 |
| EV-04 | `docs/decisions/*.md` | Architecture owner | G1 |
| EV-05 | FastAPI Swagger + DRF OpenAPI | Service owners | G3 |
| EV-06 | `services/*/migrations` | Service owners | G4 |
| EV-07 | `docs/test-report/e2e.*` | Test owner | G3 |
| EV-08 | `docs/test-report/concurrency.*` | Payment/data owners | G6/CAP-04 |
| EV-09 | `compose.yaml` + clean-run log | DevOps owner | G2/G8/CAP-01/02 |
| EV-10 | Trace/log một payment xuyên service | Observability owner | G7 |
| EV-11 | `README.md` | Cả nhóm | G8 |
| EV-12 | `docs/demo-script.md` | Demo owner | G8 |

## 6. Stop-the-line rules

- Không merge thiết kế nếu thiếu Architecture Diagram hoặc data ownership.
- Không tuyên bố workflow hoàn thành nếu chưa có OTP email, revalidation, debit, mark-paid, history và confirmation email.
- Không tuyên bố concurrency hoàn thành bằng test tuần tự hoặc demo mắt thường.
- Không release nếu CT-01/CT-02 flaky, balance có thể âm, invoice có thể paid hai lần hoặc compensation chưa nhất quán.
- Không release nếu Compose không chạy được trên môi trường sạch theo README.
- Không hy sinh bất kỳ P0 nào để làm thêm tính năng ngoài đề.

## 7. Kiểm tra trước mỗi milestone

Tại cuối mỗi giai đoạn, cập nhật:

- Trạng thái từng dòng rubric: `PLANNED -> IN_PROGRESS -> VERIFIED`.
- Trạng thái từng cap: `RISK OPEN -> MITIGATED -> VERIFIED CLOSED`.
- Link evidence thực tế, test command, commit/tag và người xác minh.
- Gap còn lại và owner/ngày xử lý.

