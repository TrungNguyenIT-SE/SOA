# Technology Baseline và Definition of Done

## 1. Trạng thái quyết định

- Baseline: v1.0, khóa ngày 2026-10-19.
- FastAPI và Django là ràng buộc bắt buộc từ giảng viên.
- Mục tiêu: kiến trúc đủ rõ để đạt rubric 10 nhưng vẫn có thể chạy/demo ổn định trên một máy bằng Docker Compose.

## 2. Technology baseline đã khóa

| Lớp | Quyết định | Vai trò | Không dùng/thay thế tùy tiện |
|---|---|---|---|
| Ngôn ngữ | Python 3.12 baseline | Tất cả backend/service/test Python | Không pha Java/Spring vào backend |
| Web + Identity | Django + Django REST Framework | Templates/UI, auth/profile, JWT, Admin demo | Admin không thay Web UI nghiệp vụ |
| Domain API | FastAPI + Pydantic | Account, Tuition, Payment/OTP, Notification API/worker | Không gom lại thành Django monolith |
| ORM | Django ORM cho Django; SQLAlchemy 2.x cho FastAPI | Persistence theo service | Không truy cập model/table của service khác |
| Migration | Django Migrations; Alembic | Schema versioning độc lập | Không sửa schema thủ công khi demo |
| Database | PostgreSQL | Nguồn dữ liệu bền vững | Không dùng SQLite cho production/concurrency test |
| Gateway | Traefik ưu tiên, Nginx là phương án dự phòng có ADR | Routing, entrypoint, headers/TLS dev | Frontend không gọi container nội bộ trực tiếp |
| Messaging | RabbitMQ | OTP/payment event, retry/DLQ | Email không gửi trực tiếp trong transaction tài chính |
| Email demo | Mailpit | SMTP + hộp thư quan sát | Không hard-code SMTP credential |
| UI enhancement | Django Templates + HTMX/Alpine.js + Bootstrap/Tailwind | Tương tác Web | Không thêm SPA nếu làm chậm đường găng |
| API docs | OpenAPI + Swagger/ReDoc | Contract và demo | Không duy trì tài liệu tay lệch implementation |
| Test | Pytest ecosystem, HTTPX, Playwright, testcontainers-python | Unit đến E2E/concurrency | Không dùng mock DB cho test khóa chính |
| Code quality | Ruff format/lint, mypy, djLint cho Django templates | Format, lint và type check thống nhất | Không format thủ công theo sở thích cá nhân |
| Observability | Python logging/structlog, correlation ID, OpenTelemetry/Jaeger | Log/trace xuyên service | Không log password/OTP/token |
| Container | Docker + Compose | One-command environment | Không yêu cầu cài DB/broker trực tiếp |
| Dependency | `uv` được ưu tiên, lockfile bắt buộc | Reproducible build | Không để dependency trôi không lock |

Phiên bản package cụ thể được pin trong lockfile khi bootstrap Giai đoạn 2. Nâng phiên bản major/minor sau đó cần ADR ngắn và chạy lại toàn bộ test liên quan.

## 3. Phân rã deployable đã khóa

1. `web-identity-service` - Django/DRF/Templates, database identity riêng.
2. `account-service` - FastAPI, database account/ledger riêng.
3. `tuition-service` - FastAPI, database student/invoice riêng.
4. `payment-service` - FastAPI, database payment/OTP/Saga/Outbox riêng.
5. `notification-service` - FastAPI worker/API, database delivery/Inbox riêng.
6. `api-gateway` - Traefik/Nginx, không chứa business logic.

Một PostgreSQL container vật lý được phép cho demo, nhưng mỗi service phải có database/schema credential riêng và không được query chéo.

## 4. Quyết định chất lượng đã khóa

- Payer và quyền truy cập lấy từ JWT, không tin client-supplied user/account.
- Amount lấy từ Tuition service, không nhận amount do client quyết định.
- Tiền dùng kiểu số nguyên VND hoặc decimal chính xác; không dùng float.
- OTP tối đa 5 phút, one-time, transaction-bound, không trùng trong tập đang hiệu lực và không lưu/log plaintext.
- Payment API có Idempotency-Key; internal command idempotent theo payment/step.
- Account debit và tuition reservation dùng atomic conditional update hoặc row lock trong local transaction.
- Giao dịch xuyên service dùng orchestration Saga, Transactional Outbox và Inbox/dedup.
- Email là hậu xử lý bất đồng bộ; lỗi email không rollback tài chính đã hoàn tất.
- Tất cả service truyền correlation ID; state change tài chính có audit log không chứa secret.
- CT-01 và CT-02 là release gate, không phải test tùy chọn.

## 5. Definition of Ready cho một story

Story chỉ được bắt đầu khi:

- Có ID, priority, owner và liên kết BR/AC/NFR.
- Acceptance criteria kiểm thử được, không dùng từ mơ hồ như “hoạt động tốt”.
- API/data/state transition và dependency đã xác định.
- Security/concurrency/idempotency impact đã xem xét.
- Có test approach và dữ liệu fixture dự kiến.
- Không có câu hỏi nghiệp vụ làm thay đổi đáng kể kết quả.

## 6. Definition of Done cho một story

- Code đúng acceptance criteria và không chứa secret/TODO trên happy path.
- Unit test và test thích hợp pass; bug concurrency phải có regression test.
- Validation, authorization, error model và log redaction đã kiểm tra.
- Migration/seed/rollback hoặc forward-fix strategy có sẵn nếu đổi data.
- OpenAPI/diagram/ADR/traceability được cập nhật cùng PR nếu bị ảnh hưởng.
- Code format/lint/type check pass.
- Python tuân theo Ruff formatter/linter và mypy; Django template tuân theo djLint; cấu hình dùng chung được commit tại repository root.
- Ít nhất một thành viên khác review; tác giả đã self-review theo PR template.
- Chạy được trong container và không phá healthcheck.

## 7. Definition of Done cho một service

- Có Dockerfile, dependency lock, cấu hình environment và `.env.example` tương ứng.
- Có health/readiness endpoint.
- Database/migration/constraints/seed độc lập.
- OpenAPI mô tả mọi endpoint và error chính.
- Authorization và service-to-service authentication đã áp dụng.
- Structured log + correlation ID + metric/trace tối thiểu.
- Unit/integration/contract test pass với PostgreSQL thật khi cần.
- Không truy cập database của service khác.

## 8. Definition of Done cho payment workflow

- Happy path hoàn chỉnh qua UI/API/email.
- OTP đúng mọi AC-06.
- Balance, ledger, invoice, payment và email đúng AC-07.
- Double submit/retry không double effect.
- CT-01 và CT-02 chạy lặp ổn định.
- Saga retry, compensation, recovery và reconciliation có test.
- Một correlation ID truy được toàn bộ flow.
- E2E report và demo fixture có thể tái lập.

## 9. Definition of Done cho release/demo

- `docker compose up --build` trên máy sạch đưa mọi service về healthy.
- README đủ cài đặt, cấu hình, seed/reset, chạy test và troubleshooting.
- Unit/integration/contract/E2E/concurrency test pass.
- Use Case, ERD, Architecture, sequence/state/deployment diagram đồng bộ code.
- Swagger/ReDoc truy cập được.
- UI bao phủ login -> lookup -> payment -> OTP -> result/history.
- Mailpit có OTP và confirmation email đúng.
- Demo script happy path, lỗi, CT-01, CT-02 và resilience đã rehearsal.
- Không có điều kiện giới hạn điểm nào bị kích hoạt.
- Ba thành viên đều giải thích được service boundary, data ownership, Saga, idempotency và concurrency.

## 10. Quality gate tối thiểu

| Gate | Điều kiện pass |
|---|---|
| G0 Scope | BR-01..08, AC, NFR, invariant và rubric trace đủ |
| G1 Design | Diagram/API/data/state/ADR được review |
| G2 Build | Tất cả image build, service healthy, dependency locked |
| G3 Functional | Happy/error workflow pass |
| G4 Data | Migration/constraint/persistence pass |
| G5 Security | Authn/authz/secret/OTP redaction/rate limit pass |
| G6 Concurrency | CT-01 và CT-02 pass lặp lại, không flaky |
| G7 Resilience | Retry/event duplicate/restart/compensation pass |
| G8 Delivery | Máy sạch + README + demo rehearsal pass |

Không hạ gate để kịp demo. Nếu thiếu thời gian, bỏ P2 trước, sau đó P1 không liên quan cap; giữ toàn bộ P0.

