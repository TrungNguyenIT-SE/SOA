# KẾ HOẠCH A-Z DỰ ÁN GIỮA KỲ SOA

## Phân hệ đóng học phí của ứng dụng iBanking - Mục tiêu 10/10

> Tài liệu này là kế hoạch triển khai và checklist nghiệm thu. Mọi hạng mục đều được truy vết từ 3 trang đề bài và 3 trang rubric trong thư mục `ĐỀ`.
>
> Mục tiêu là bao phủ 100% yêu cầu được công bố và chuẩn bị đầy đủ minh chứng cho mức 10. Điểm thực tế vẫn phụ thuộc chất lượng hiện thực, demo và phần bảo vệ trước giảng viên.

---

## 1. Nguồn yêu cầu đã kiểm tra

- `ĐỀ/de1.png`: mô tả bài toán, đăng nhập, thông tin người dùng, phần đầu luồng tra cứu và thanh toán học phí.
- `ĐỀ/de2.png`: điều kiện giao dịch, OTP, xử lý giao dịch thành công.
- `ĐỀ/de3.png`: transaction/concurrency và 8 đầu việc bắt buộc.
- `ĐỀ/rubric-midterm.pdf`: 8 tiêu chí chấm, mức điểm mục tiêu và các điều kiện giới hạn điểm.
- Đã kiểm tra trực quan đủ 3 ảnh và đủ 3 trang PDF, đồng thời đối chiếu phần chữ được trích xuất từ PDF.
- Ghi chú tài liệu nguồn: rubric lặp nhãn `Họ và tên SV2` ở dòng sinh viên thứ ba. Đây là lỗi trình bày, không phải yêu cầu nghiệp vụ; khi điền nên hiểu dòng thứ ba là SV3.
- Trang 3 của rubric ghi rõ sinh viên không in và nộp kèm trang này khi báo cáo.

---

## 2. Mục tiêu và phạm vi

### 2.1. Mục tiêu sản phẩm

Xây dựng một Web Application mô phỏng phân hệ đóng học phí của iBanking. Người dùng đăng nhập bằng tài khoản ngân hàng và dùng số dư khả dụng để thanh toán toàn bộ một khoản học phí cho chính mình hoặc một sinh viên khác.

Sản phẩm phải:

- Chạy hoàn chỉnh từ giao diện đến các backend service và database.
- Là Microservices thực sự: nhiều service độc lập, giao tiếp qua API/event và có quyền sở hữu dữ liệu rõ ràng.
- Thực hiện đúng OTP qua email, thời hạn tối đa 5 phút và chỉ dùng thành công một lần.
- Đảm bảo nhất quán dữ liệu tài chính.
- Xử lý và demo được cả hai tình huống concurrency bắt buộc.
- Có sơ đồ, API documentation, automated test, Docker Compose, logging/tracing và kịch bản demo.

### 2.2. Ngoài phạm vi

- Không xây chức năng đăng ký tài khoản mới.
- Không cho thanh toán một phần học phí.
- Không mô phỏng đầy đủ hệ thống ngân hàng ngoài phạm vi tài khoản, số dư và lịch sử giao dịch cần cho đề bài.
- Không cần quản trị trường đại học phức tạp; dữ liệu sinh viên và học phí có thể được seed sẵn.
- Không lưu hoặc hiển thị OTP dạng rõ trong database/log.

### 2.3. Định nghĩa hoàn thành

Chỉ coi dự án hoàn thành khi:

- `docker compose up --build` khởi chạy được toàn bộ hệ thống theo README.
- Luồng chính chạy được trên UI: đăng nhập -> tra cứu MSSV -> xác nhận -> nhận/nhập OTP -> kết quả -> lịch sử.
- Email OTP và email xác nhận được gửi tới hộp thư demo thực hoặc Mailpit/MailHog trong môi trường demo.
- Tất cả API chính có OpenAPI/Swagger, validation, error model và status code đúng.
- Test tự động gồm unit, integration, E2E và hai concurrency test bắt buộc đều pass.
- Sau mọi test thành công/thất bại, số dư, trạng thái học phí, payment và ledger/history nhất quán.
- Có Use Case Diagram, ERD, Microservices Architecture Diagram, sequence diagram cho luồng thanh toán và tài liệu giải thích quyết định thiết kế.
- Có kịch bản demo dự phòng và dữ liệu mẫu có thể reset.

---

## 3. Yêu cầu nghiệp vụ chuẩn hóa

### BR-01 - Đăng nhập

- Người dùng đăng nhập bằng `username` và `password`.
- Không yêu cầu chức năng đăng ký.
- Mật khẩu phải được hash; không lưu plaintext.
- Đăng nhập thành công trả access token; API nghiệp vụ yêu cầu xác thực.

### BR-02 - Thông tin người dùng

Hệ thống quản lý tối thiểu:

- Họ và tên.
- Số điện thoại.
- Địa chỉ email.
- Số dư khả dụng.
- Lịch sử giao dịch đã thực hiện.

Sau đăng nhập, người dùng truy cập được chức năng thanh toán học phí.

### BR-03 - Thông tin người nộp tiền

- Họ tên, số điện thoại và email được lấy tự động từ tài khoản đang đăng nhập.
- Các trường này chỉ đọc trên màn hình thanh toán, người dùng không được chỉnh sửa.
- Tài khoản đang đăng nhập là tài khoản bị trừ tiền, kể cả khi trả học phí cho sinh viên khác.

### BR-04 - Tra cứu học phí

- Người dùng nhập MSSV.
- Hệ thống tự động tra cứu và hiển thị MSSV, họ tên sinh viên và số tiền còn phải thanh toán.
- Chỉ hiển thị/xử lý khoản học phí tồn tại và chưa thanh toán.
- Chỉ cho phép thanh toán toàn bộ số tiền, không có trường nhập số tiền tùy ý.

### BR-05 - Điều kiện được xác nhận

Nút xác nhận chỉ khả dụng khi:

- MSSV hợp lệ và có khoản học phí tồn tại.
- Khoản học phí chưa được thanh toán.
- Số dư khả dụng lớn hơn hoặc bằng số tiền học phí.
- Người dùng đã xem/chấp nhận thỏa thuận và điều khoản.
- Các dữ liệu bắt buộc đầy đủ và hợp lệ.

Backend luôn kiểm tra lại các điều kiện; không phụ thuộc vào việc nút trên UI có bị vô hiệu hóa hay không.

### BR-06 - Khởi tạo giao dịch và OTP

- Khi người dùng xác nhận, hệ thống tạo một payment cụ thể và gắn OTP với payment đó.
- OTP được gửi qua email của người nộp tiền.
- OTP không trùng với OTP đang có hiệu lực của giao dịch khác.
- OTP hết hạn không muộn hơn 5 phút sau khi phát hành.
- OTP chỉ được sử dụng thành công một lần.
- OTP sai, hết hạn, đã dùng hoặc không thuộc payment hiện tại đều bị từ chối và không tiếp tục thanh toán.

### BR-07 - Hoàn tất thanh toán

Sau khi OTP hợp lệ, hệ thống phải:

1. Đánh dấu OTP đã dùng theo cách nguyên tử để không thể xác nhận hai lần.
2. Kiểm tra lại trạng thái payment, khoản học phí và số dư khả dụng.
3. Trừ đúng số tiền khỏi tài khoản người nộp.
4. Đánh dấu đúng khoản học phí là đã thanh toán.
5. Ghi ledger/lịch sử giao dịch.
6. Gửi email xác nhận thành công.
7. Kết thúc payment và trả kết quả cho UI.

### BR-08 - Tính nhất quán và concurrency

- Nhiều giao dịch đồng thời trên cùng một tài khoản không được chi tiêu cùng một số dư dẫn đến âm/vượt số dư.
- Nhiều tài khoản đồng thời thanh toán cùng một khoản học phí chỉ được có một payment thành công.
- Kết quả cuối cùng của số dư, học phí, payment và lịch sử phải tương ứng với nhau.
- Retry do timeout, double-click hoặc mạng chập chờn không được tạo thanh toán lặp.

---

## 4. Kiến trúc mục tiêu

### 4.1. Công nghệ bắt buộc và đề xuất

- Web và Identity: Django, Django REST Framework, Django Templates, HTMX/Alpine.js và Bootstrap/Tailwind CSS.
- Các API nghiệp vụ: FastAPI, Pydantic, SQLAlchemy 2.x và Uvicorn.
- Authentication: Django authentication + Django REST Framework Simple JWT; FastAPI xác minh cùng JWT public key/secret và authorization claim.
- API Gateway: Traefik hoặc Nginx; ưu tiên Traefik trong Docker Compose để route theo path và gắn correlation ID.
- Database: PostgreSQL; mỗi service có database/schema riêng và không truy cập bảng của service khác.
- Messaging: RabbitMQ cho notification và domain event.
- Cache/coordination tùy chọn: Redis chỉ dùng rate limiting hoặc cache, không dùng làm nguồn dữ liệu tài chính chính.
- Email demo: Mailpit/MailHog trong Docker; hỗ trợ SMTP thật bằng biến môi trường nếu cần.
- API docs: OpenAPI 3; Swagger/ReDoc tự sinh từ FastAPI và schema OpenAPI của Django REST Framework.
- Test: Pytest, pytest-django, pytest-asyncio, HTTPX/FastAPI TestClient, testcontainers-python, Playwright và Locust hoặc test concurrency bằng `asyncio`/HTTPX.
- Quan sát: structured JSON log, correlation ID, Prometheus/Grafana tùy thời gian và OpenTelemetry/Jaeger để minh chứng tracing.
- Triển khai: Dockerfile cho từng thành phần và một `compose.yaml` duy nhất.

FastAPI và Django là ràng buộc bắt buộc của giảng viên, không được thay bằng framework backend khác. Cách phân vai dưới đây giúp cả hai framework tham gia trực tiếp vào sản phẩm, không dùng một framework chỉ để đối phó yêu cầu.

| Thành phần | Framework | Vai trò chính |
|---|---|---|
| Web + Identity | Django + Django REST Framework | Giao diện web, đăng nhập, hồ sơ, JWT và Django Admin |
| Account API | FastAPI | Số dư, atomic debit và ledger |
| Tuition API | FastAPI | Sinh viên, học phí và atomic reservation |
| Payment/OTP API | FastAPI | Payment state machine, OTP và Saga orchestration |
| Notification worker/API | FastAPI | Consumer RabbitMQ, email và delivery status |

Mỗi Python service phải có dependency lock riêng hoặc dùng một workspace lock thống nhất, cấu hình bằng environment variables và chạy độc lập trong container.

### 4.2. Các thành phần

#### 1. `web-identity-service` - Django

- Sở hữu thông tin đăng nhập và hồ sơ: username, password hash, họ tên, điện thoại, email.
- Cấp JWT khi đăng nhập thành công và trả thông tin người dùng hiện tại qua Django REST Framework.
- Dùng Django Templates + HTMX/Alpine.js để hiển thị đăng nhập, dashboard, form tra cứu/thanh toán, OTP, kết quả và lịch sử.
- Dùng Django Admin để quản lý dữ liệu người dùng demo, không dùng Admin thay cho giao diện nghiệp vụ.
- UI chỉ gọi API qua Gateway và không chứa logic quyết định số dư hay trạng thái học phí.

#### 2. `api-gateway`

- Điểm vào duy nhất của frontend.
- Route request tới các service.
- Xác minh token hoặc chuyển tiếp token để service xác minh.
- Thêm/lan truyền `X-Correlation-Id`.
- Có thể rate limit endpoint đăng nhập và OTP.

#### 3. `account-service` - FastAPI

- Sở hữu tài khoản ngân hàng, số dư khả dụng và immutable ledger.
- Cung cấp truy vấn số dư và lịch sử giao dịch.
- Thực hiện debit/compensating credit nguyên tử, có idempotency theo `paymentId`.
- Không cho service khác cập nhật trực tiếp database tài khoản.

#### 4. `tuition-service` - FastAPI

- Sở hữu sinh viên và khoản học phí.
- Tra cứu theo MSSV.
- Thực hiện reserve/mark-paid/release bằng conditional update và `paymentId`.
- Đảm bảo một khoản học phí chỉ có một payment thắng.

#### 5. `payment-service` - FastAPI

- Sở hữu payment, OTP và trạng thái Saga.
- Điều phối toàn bộ workflow thanh toán.
- Sinh OTP, lưu fingerprint/hash, quản lý hết hạn và one-time use.
- Thực hiện idempotency cho request từ client.
- Ghi Outbox event và điều phối retry/compensation/reconciliation.

#### 6. `notification-service` - FastAPI worker/API

- Nhận event gửi OTP hoặc xác nhận thanh toán.
- Gửi email qua SMTP.
- Retry có giới hạn, Dead Letter Queue và idempotency theo `eventId`.
- Không quyết định giao dịch thành công hay thất bại.

### 4.3. Quyền sở hữu dữ liệu

| Service | Dữ liệu sở hữu | Cấm |
|---|---|---|
| web-identity-service (Django) | users, credentials, user profile | Không lưu balance/payment |
| account-service | accounts, balances, ledger entries | Không sửa tuition invoice |
| tuition-service | students, tuition invoices | Không trừ tiền account |
| payment-service | payments, OTP records, saga steps, outbox | Không sửa trực tiếp DB service khác |
| notification-service | delivery attempts, inbox/dedup records | Không thay đổi trạng thái tài chính |

Có thể dùng một PostgreSQL container để giảm tài nguyên demo, nhưng phải tách database/schema, user kết nối và migration theo service. Tuyệt đối không join hoặc update chéo database.

### 4.4. Giao tiếp

- Đồng bộ REST:
  - Django Web UI/Browser -> Gateway -> Django Identity hoặc các FastAPI service.
  - Payment service -> Account/Tuition để reserve, debit, complete hoặc compensate.
- Bất đồng bộ RabbitMQ:
  - `otp.requested` -> Notification service.
  - `payment.completed` -> Notification service.
  - Có thể thêm event audit/observability.
- Mọi request nội bộ có `paymentId`, `requestId`/`Idempotency-Key` và `correlationId`.
- Timeout, retry với backoff và circuit breaker chỉ áp dụng cho lỗi tạm thời; retry phải an toàn nhờ idempotency.

### 4.5. Lý do chọn Saga orchestration

- Account và tuition thuộc hai service/database khác nhau nên không giả vờ dùng một local transaction xuyên service.
- Payment service đóng vai trò orchestrator giúp trạng thái và compensation dễ giải thích, kiểm thử và demo.
- Mỗi bước là local ACID transaction; các command có idempotency.
- Transactional Outbox ngăn tình trạng database commit nhưng event không được phát.
- Recovery worker tiếp tục Saga đang dở sau khi service khởi động lại.
- Reconciliation job phát hiện trạng thái hiếm gặp cần sửa hoặc cảnh báo.

---

## 5. Luồng xử lý chi tiết

### 5.1. Đăng nhập

1. UI gửi username/password qua Gateway.
2. Identity service xác minh password hash.
3. Trả JWT và thông tin tối thiểu.
4. UI gọi `/users/me` và `/accounts/me` để hiển thị thông tin read-only, số dư.

### 5.2. Tra cứu học phí

1. UI validate định dạng MSSV.
2. Gọi Tuition service qua Gateway.
3. Tuition service trả MSSV, họ tên sinh viên, số tiền và trạng thái.
4. UI chỉ cho tiếp tục nếu trạng thái là `UNPAID` và số dư hiện tại đủ.
5. Backend vẫn kiểm tra lại khi tạo payment và khi hoàn tất payment.

### 5.3. Khởi tạo payment

1. UI gửi `POST /payments` với `tuitionInvoiceId`, chấp nhận điều khoản và header `Idempotency-Key`.
2. Payment service lấy `payerUserId` từ token, không nhận payer tùy ý từ client.
3. Payment service lấy snapshot người nộp, account và tuition từ service sở hữu.
4. Kiểm tra invoice tồn tại/chưa thanh toán và số dư tạm thời đủ.
5. Tạo payment `OTP_PENDING`, amount lấy từ Tuition service, không lấy từ số client gửi.
6. Sinh OTP bằng CSPRNG, bảo đảm fingerprint không trùng OTP đang hiệu lực.
7. Lưu OTP với `expiresAt <= issuedAt + 5 phút`, `usedAt = null`, giới hạn số lần nhập/resend.
8. Ghi Outbox `otp.requested`; worker phát event cho Notification service.
9. Trả `paymentId`, masked email và thời điểm hết hạn; không trả OTP.

### 5.4. Xác thực OTP và Saga thanh toán

1. UI gửi `POST /payments/{paymentId}/otp/verify` cùng OTP và `Idempotency-Key`.
2. Payment service khóa bản ghi payment/OTP hoặc conditional update để bảo đảm chỉ một request xác thực thắng.
3. Kiểm tra ownership, payment status, OTP fingerprint, expiry, `usedAt`, số lần thử.
4. Đánh dấu OTP đã dùng và payment `PROCESSING` trong cùng local transaction.
5. Bắt đầu Saga:
   - Bước A: Tuition service atomic reserve invoice nếu đang `UNPAID`; gắn `paymentId`.
   - Bước B: Account service atomic debit nếu `balance >= amount`; tạo ledger `DEBIT` duy nhất theo `paymentId`.
   - Bước C: Tuition service atomic chuyển `RESERVED -> PAID` nếu reservation thuộc đúng `paymentId`.
   - Bước D: Payment service chuyển `PROCESSING -> SUCCEEDED` và ghi Outbox `payment.completed`.
   - Bước E: Notification service gửi email xác nhận và lưu delivery result.
6. Nếu A thất bại: payment `FAILED_TUITION_UNAVAILABLE`, không debit.
7. Nếu B thất bại: release reservation, payment `FAILED_INSUFFICIENT_FUNDS`.
8. Nếu C lỗi tạm thời: retry idempotent. Nếu lỗi vĩnh viễn: compensating credit và release theo workflow có kiểm soát; ghi rõ trạng thái compensation.
9. Nếu gửi email lỗi: payment vẫn thành công; notification retry/DLQ, không rollback giao dịch tài chính.
10. Recovery worker xử lý Saga `PROCESSING` quá hạn; reconciliation xác nhận payment, ledger và invoice khớp nhau.

### 5.5. Trạng thái cần có

Payment:

`OTP_PENDING -> PROCESSING -> SUCCEEDED`

Nhánh lỗi:

`OTP_PENDING -> EXPIRED/CANCELLED`

`PROCESSING -> FAILED_TUITION_UNAVAILABLE/FAILED_INSUFFICIENT_FUNDS/COMPENSATING -> COMPENSATED`

Tuition invoice:

`UNPAID -> RESERVED -> PAID`, hoặc `RESERVED -> UNPAID` khi release hợp lệ.

OTP:

`ISSUED -> USED`, `ISSUED -> EXPIRED`, hoặc `ISSUED -> REVOKED` khi resend.

Không cho phép client tự ý truyền trạng thái mới.

---

## 6. Thiết kế dữ liệu và ràng buộc

### 6.1. Identity database

`users`

- `id UUID PK`
- `username VARCHAR UNIQUE NOT NULL`
- `password_hash VARCHAR NOT NULL`
- `full_name VARCHAR NOT NULL`
- `phone VARCHAR NOT NULL`
- `email VARCHAR UNIQUE NOT NULL`
- `status`, `created_at`, `updated_at`

### 6.2. Account database

`accounts`

- `id UUID PK`, `user_id UUID UNIQUE NOT NULL`
- `account_number VARCHAR UNIQUE NOT NULL`
- `currency CHAR(3)`, mặc định VND
- `available_balance NUMERIC(19,0) CHECK (available_balance >= 0)`
- `version BIGINT NOT NULL` cho optimistic locking nếu dùng.

`ledger_entries`

- `id UUID PK`, `account_id`, `payment_id`, `type`, `amount`, `balance_after`, `created_at`
- `UNIQUE(payment_id, type)` để debit/compensation idempotent.
- `amount > 0`; ledger không sửa/xóa.

### 6.3. Tuition database

`students`

- `id UUID PK`, `student_code VARCHAR UNIQUE NOT NULL`, `full_name VARCHAR NOT NULL`.

`tuition_invoices`

- `id UUID PK`, `student_id`, `term`, `amount NUMERIC(19,0) CHECK(amount > 0)`.
- `status IN (UNPAID, RESERVED, PAID)`.
- `reserved_by_payment_id`, `reservation_expires_at`, `paid_by_payment_id`, `paid_at`, `version`.
- `UNIQUE(student_id, term)` nếu mỗi kỳ chỉ có một khoản tổng cần thanh toán.
- Conditional update/row lock bảo đảm chỉ một payment reserve/mark paid.

### 6.4. Payment database

`payments`

- `id UUID PK`, `payer_user_id`, `account_id`, `tuition_invoice_id`, `student_code`.
- `amount`, `status`, `failure_code`, `idempotency_key`, `correlation_id`.
- Snapshot cần cho audit: payer name/email và student name tại thời điểm tạo.
- `created_at`, `updated_at`, `completed_at`, `version`.
- `UNIQUE(payer_user_id, idempotency_key)`.

`otp_challenges`

- `id UUID PK`, `payment_id`, `code_fingerprint`, `status`, `issued_at`, `expires_at`, `used_at`, `attempt_count`.
- `UNIQUE(payment_id)` cho OTP đang dùng hoặc version theo từng lần resend.
- Unique index trên `code_fingerprint` đối với trạng thái `ISSUED`; job chuyển OTP hết hạn sang `EXPIRED`.
- Lưu fingerprint bằng HMAC với server secret để so khớp và kiểm tra uniqueness, không lưu OTP plaintext.
- Không log OTP; secret lấy từ environment/secret manager.

`saga_steps`, `outbox_events`, `idempotency_records`

- Có unique key phù hợp theo payment/step/event để retry không tạo tác dụng kép.

### 6.5. Notification database

`inbox_events` và `email_deliveries`

- `event_id UNIQUE` để consumer idempotent.
- Lưu template, recipient, status, attempt count, last error, timestamps; không lưu OTP rõ lâu dài.

### 6.6. Migration và dữ liệu mẫu

- Dùng Django Migrations cho `web-identity-service` và Alembic riêng cho từng FastAPI service.
- Seed tối thiểu 3 user/account và nhiều sinh viên/invoice:
  - Tài khoản đủ tiền.
  - Tài khoản không đủ tiền.
  - Invoice chưa thanh toán.
  - Invoice đã thanh toán.
  - Hai invoice phục vụ test cùng tài khoản.
  - Một invoice phục vụ test hai tài khoản cùng thanh toán.
- Có script/API reset dữ liệu demo an toàn, chỉ bật ở profile `demo`/`test`.

---

## 7. REST API dự kiến

Mọi API trả JSON, dùng thời gian ISO-8601 UTC, số tiền là integer VND hoặc decimal string; không dùng floating point.

### 7.1. Identity

| Method | URI | Mục đích | Thành công |
|---|---|---|---|
| POST | `/api/v1/auth/login` | Đăng nhập | 200 |
| GET | `/api/v1/users/me` | Hồ sơ người nộp | 200 |

### 7.2. Account

| Method | URI | Mục đích | Thành công |
|---|---|---|---|
| GET | `/api/v1/accounts/me` | Số dư khả dụng | 200 |
| GET | `/api/v1/accounts/me/transactions` | Lịch sử có phân trang | 200 |

Internal API tối thiểu:

- `POST /internal/v1/accounts/{id}/debits`.
- `POST /internal/v1/accounts/{id}/compensating-credits`.
- Mỗi command chứa `paymentId`, amount và idempotency key.

### 7.3. Tuition

| Method | URI | Mục đích | Thành công |
|---|---|---|---|
| GET | `/api/v1/tuition-invoices/by-student/{studentCode}` | Tra cứu học phí | 200 |

Internal API tối thiểu:

- `POST /internal/v1/tuition-invoices/{id}/reservations`.
- `POST /internal/v1/tuition-invoices/{id}/mark-paid`.
- `DELETE /internal/v1/tuition-invoices/{id}/reservations/{paymentId}`.

### 7.4. Payment và OTP

| Method | URI | Mục đích | Thành công |
|---|---|---|---|
| POST | `/api/v1/payments` | Tạo payment và gửi OTP | 201 |
| POST | `/api/v1/payments/{id}/otp/verify` | Xác thực OTP, khởi chạy thanh toán | 200/202 |
| POST | `/api/v1/payments/{id}/otp/resend` | Phát hành OTP mới có kiểm soát | 202 |
| GET | `/api/v1/payments/{id}` | Xem kết quả/trạng thái | 200 |
| GET | `/api/v1/payments` | Lịch sử payment của người dùng | 200 |

### 7.5. Error model chuẩn

```json
{
  "timestamp": "2026-10-19T08:00:00Z",
  "status": 409,
  "code": "TUITION_ALREADY_PAID",
  "message": "Khoản học phí đã được thanh toán.",
  "path": "/api/v1/payments/.../otp/verify",
  "correlationId": "...",
  "fieldErrors": []
}
```

Status code tối thiểu:

- `400`: JSON/định dạng không hợp lệ.
- `401`: sai đăng nhập/token thiếu hoặc hết hạn.
- `403`: truy cập payment của người khác.
- `404`: không tìm thấy MSSV/invoice/payment.
- `409`: đã thanh toán, payment sai trạng thái, idempotency conflict.
- `422`: nghiệp vụ không thỏa, ví dụ không đủ số dư hoặc OTP sai/hết hạn/đã dùng.
- `429`: quá nhiều lần đăng nhập/nhập hoặc gửi lại OTP.
- `500/503`: lỗi hệ thống/phụ thuộc tạm thời; không để lộ stack trace.

Mỗi endpoint phải có request/response example, validation, security requirement và danh sách status code trong OpenAPI.

---

## 8. Bảo mật và độ tin cậy

- Password hash bằng BCrypt/Argon2; JWT ký bằng secret/key ngoài source code.
- Payer lấy từ token, không tin `userId/accountId/email/amount` do client tự gửi.
- OTP sinh bằng `SecureRandom`, có TTL tối đa 5 phút, rate limit, giới hạn lần thử và resend cooldown.
- OTP không xuất hiện trong response, log, tracing hoặc source code.
- Authorization bảo đảm user chỉ xem payment/history của mình.
- Validate MSSV, UUID, email, phone, amount và state transition ở server.
- CORS theo origin cấu hình; security headers; không commit secret hoặc `.env` thật.
- Idempotency-Key bắt buộc cho tạo payment và verify OTP.
- Mọi command nội bộ xác thực service-to-service tối thiểu bằng shared internal token trong demo; tài liệu nêu hướng production dùng mTLS/OAuth2 client credentials.
- Audit log chứa actor, action, paymentId, correlationId và kết quả, nhưng không chứa dữ liệu nhạy cảm.
- Health check/readiness cho từng service.

---

## 9. Chiến lược transaction, concurrency và idempotency

### 9.1. Cùng một tài khoản, nhiều giao dịch

Account service phải dùng một trong hai cách có minh chứng SQL:

- Ưu tiên: atomic conditional update
  `UPDATE accounts SET available_balance = available_balance - :amount WHERE id = :id AND available_balance >= :amount`.
- Hoặc `SELECT ... FOR UPDATE` trong local transaction.

Chỉ khi số dòng cập nhật bằng 1 mới ghi debit ledger và trả thành công. Unique constraint theo `paymentId` ngăn retry trừ tiền lần hai.

### 9.2. Nhiều tài khoản trả cùng một học phí

Tuition service dùng atomic conditional update hoặc row lock:

- Chỉ reserve khi `status = UNPAID`.
- Reservation gắn đúng `paymentId`.
- Chỉ payment sở hữu reservation mới được mark paid hoặc release.
- Một invoice không thể có hai `paid_by_payment_id`.

### 9.3. OTP và double submit

- Conditional update `ISSUED -> USED` kèm điều kiện chưa hết hạn.
- Hai request verify đồng thời: đúng một request cập nhật thành công.
- Request retry với cùng idempotency key nhận lại kết quả cũ.
- Request dùng cùng key nhưng body khác trả `409 IDEMPOTENCY_KEY_REUSED`.

### 9.4. Saga, Outbox và phục hồi

- Mỗi bước Saga lưu trước/sau khi gọi service và có số lần retry.
- Outbox được ghi cùng transaction với thay đổi trạng thái payment.
- Publisher đánh dấu event đã gửi; consumer có Inbox/dedup.
- Recovery worker quét payment `PROCESSING` quá ngưỡng và tiếp tục đúng bước.
- Reconciliation kiểm tra định kỳ:
  - `SUCCEEDED` phải có một debit ledger và invoice `PAID` bởi cùng payment.
  - `COMPENSATED` phải có debit và compensating credit cân bằng; invoice không được paid bởi payment đó.
- Có test fault injection mô phỏng service chết sau debit nhưng trước mark-paid.

---

## 10. Giao diện người dùng

### Màn hình 1 - Đăng nhập

- Username, password, validation và thông báo lỗi rõ ràng.
- Không có nút đăng ký.

### Màn hình 2 - Dashboard

- Họ tên, masked account number và số dư khả dụng.
- Lối vào thanh toán học phí và lịch sử.

### Màn hình 3 - Thanh toán học phí

- Người nộp: họ tên, điện thoại, email read-only.
- Nhập MSSV và nút tra cứu.
- Hiển thị MSSV, tên sinh viên, số tiền học phí.
- Hiển thị số dư, số tiền cần trả và điều khoản.
- Không có trường nhập số tiền.
- Nút xác nhận chỉ bật khi hợp lệ; backend vẫn kiểm tra lại.

### Màn hình 4 - OTP

- Hiển thị masked email, countdown tối đa 5 phút.
- Nhập OTP, xác nhận, resend có cooldown.
- Chặn double-click; hiển thị lỗi sai/hết hạn/đã dùng.

### Màn hình 5 - Kết quả

- Thành công: mã giao dịch, MSSV, tên sinh viên, số tiền, thời gian, số dư mới.
- Thất bại: mã lỗi dễ hiểu và hướng xử lý.
- Nếu đang xử lý: polling theo paymentId đến trạng thái cuối, có timeout hợp lý.

### Màn hình 6 - Lịch sử

- Danh sách giao dịch, trạng thái, số tiền, thời gian; có phân trang.
- Có trang chi tiết theo paymentId.

UI phải responsive, có loading/empty/error state, không lộ stack trace và không giả lập dữ liệu sau khi đã tích hợp API.

---

## 11. Sơ đồ và tài liệu bắt buộc

Lưu source sơ đồ trong `docs/diagrams/` và ảnh xuất trong `docs/images/`:

1. `use-case.puml`/`.drawio`
   - Actor: Người dùng iBanking, Email service; có thể thêm Scheduler/System.
   - Use case: đăng nhập, xem thông tin/số dư, tra cứu, tạo thanh toán, nhận/xác thực OTP, xem kết quả/lịch sử.
2. `erd-overview.puml`
   - Entity, thuộc tính chính, PK/FK/unique/check và quan hệ.
   - Dùng nét/khung chỉ rõ entity thuộc database/service nào; không thể hiện FK vật lý xuyên service.
3. `microservices-architecture.puml`
   - Web, Gateway, tất cả service, database riêng, RabbitMQ, SMTP/Mailpit, monitoring.
   - Gắn nhãn REST/event và chiều giao tiếp.
4. `payment-sequence.puml`
   - Từ tạo payment, gửi OTP, verify, reserve, debit, mark paid, outbox, email.
5. `concurrency-sequence.puml`
   - Hai request cùng account.
   - Hai payer cùng invoice.
6. `saga-state-machine.puml`
   - Happy path, retry và compensation.
7. `deployment-diagram.puml`
   - Các container, port nội bộ/công khai và volume.

Tài liệu giải thích rõ vì sao dùng Saga, database-per-service, conditional update/lock, idempotency và Outbox; đồng thời nêu trade-off eventual consistency ngắn hạn và cách recovery.

---

## 12. Kế hoạch kiểm thử

### 12.1. Unit test

- Login đúng/sai, user bị khóa.
- Validation MSSV và request.
- Payment state machine không cho transition sai.
- OTP đúng/sai/hết hạn/đã dùng/không đúng payment.
- OTP TTL không vượt 5 phút.
- Idempotency resolver.
- Saga decision và compensation.

### 12.2. Repository/database integration test

- Unique/check/not-null constraint.
- Conditional debit không làm âm số dư.
- Ledger không trùng `paymentId`.
- Conditional reserve chỉ có một winner.
- OTP conditional use chỉ có một winner.
- Outbox được commit cùng business state.
- Chạy bằng PostgreSQL thật trong container qua testcontainers-python; không dùng SQLite cho các test khóa/concurrency chính vì hành vi lock khác PostgreSQL.

### 12.3. API/contract test

- Happy path và toàn bộ 400/401/403/404/409/422/429.
- OpenAPI khớp implementation.
- Không user nào đọc payment/history của user khác.
- Retry cùng idempotency key không tạo bản ghi/tác dụng mới.

### 12.4. Integration và E2E test

- Login -> lookup -> create payment -> lấy OTP qua Mailpit test API -> verify -> xem kết quả/history.
- Thanh toán cho chính mình và cho sinh viên khác.
- Invoice không tồn tại/đã trả.
- Không đủ số dư.
- OTP sai, hết hạn, dùng lại, resend làm OTP cũ vô hiệu.
- Email OTP và email xác nhận có đúng recipient/payment/amount, không lộ secret.
- Double-click/create retry không tạo payment hoặc debit lặp.

### 12.5. Hai concurrency test bắt buộc

#### CT-01 - Nhiều giao dịch trên cùng tài khoản

- Given: balance 1.500.000 VND, hai invoice khác nhau mỗi invoice 1.000.000 VND.
- Dùng barrier để gửi hai lệnh hoàn tất gần như đồng thời, không test tuần tự giả concurrency.
- Expected:
  - Chính xác một payment thành công.
  - Payment còn lại thất bại do không đủ số dư hoặc được xử lý/compensate đúng.
  - Balance cuối 500.000 VND, không âm.
  - Chính xác một debit hiệu lực 1.000.000 VND.
  - Chỉ invoice của payment thắng là `PAID`.

#### CT-02 - Nhiều tài khoản trả cùng khoản học phí

- Given: hai account đều đủ tiền, cùng nhắm tới một invoice 1.000.000 VND.
- Gửi hai lệnh hoàn tất đồng thời bằng barrier.
- Expected:
  - Chính xác một payment thành công.
  - Invoice chỉ `PAID` một lần và gắn một `paymentId`.
  - Chỉ account thắng bị trừ tiền; account thua không bị trừ hoặc đã được compensation đầy đủ.
  - Chỉ có một lịch sử debit thành công ứng với invoice.

Chạy mỗi concurrency test nhiều vòng, ví dụ 50-100 vòng trong CI/profile test, để tránh kết quả pass ngẫu nhiên. Lưu log và báo cáo test làm minh chứng demo.

### 12.6. Resilience/failure test cho mức 10

- Notification service tắt: payment vẫn đúng, email được retry sau khi service lên.
- Timeout sau debit: retry không debit lần hai.
- Payment service restart ở từng Saga step: recovery tiếp tục đúng.
- RabbitMQ giao event trùng: consumer chỉ gửi/ghi nhận một lần theo event id hoặc xử lý an toàn.
- Database/service phụ thuộc không sẵn sàng: trả lỗi kiểm soát, không corrupt dữ liệu.

### 12.7. Quality gate

- Tất cả test bắt buộc pass.
- Không có lỗi mức critical/high từ dependency/security scan nếu triển khai scan.
- Không commit secret.
- Không có TODO ở đường đi nghiệp vụ chính.
- Coverage tập trung vào payment/OTP/concurrency, mục tiêu tối thiểu 80% line cho domain/service layer; coverage không thay thế test chất lượng.

---

## 13. Cấu trúc repository dự kiến

```text
.
|-- README.md
|-- CONTRIBUTING.md
|-- compose.yaml
|-- .env.example
|-- .editorconfig
|-- .github/
|   `-- pull_request_template.md
|-- Makefile hoặc scripts/
|-- gateway/
|-- services/
|   |-- web-identity-service/       # Django + DRF + Templates
|   |-- account-service/            # FastAPI
|   |-- tuition-service/            # FastAPI
|   |-- payment-service/            # FastAPI
|   `-- notification-service/       # FastAPI worker/API
|-- docs/
|   |-- phase-0/
|   |   |-- requirements.md
|   |   |-- backlog.md
|   |   |-- requirements-traceability.md
|   |   |-- technology-and-dod.md
|   |   |-- git-workflow.md
|   |   `-- rubric-baseline.md
|   |-- api/
|   |-- diagrams/
|   |-- images/
|   |-- test-report/
|   |-- demo-script.md
|   `-- design-decisions/
|-- tests/
|   |-- e2e/
|   |-- concurrency/
|   `-- performance/
`-- ĐỀ/
```

Mỗi service có README ngắn, Dockerfile, migration, test và health check. README gốc là tài liệu chạy toàn hệ thống.

---

## 14. Kế hoạch thực hiện theo giai đoạn

### Giai đoạn 0 - Khóa yêu cầu và tiêu chí

- [x] Đưa BR-01 đến BR-08 vào issue/backlog - xem `docs/phase-0/requirements.md` và `docs/phase-0/backlog.md`.
- [x] Tạo ma trận truy vết yêu cầu - API - bảng dữ liệu - test - màn hình - demo - xem `docs/phase-0/requirements-traceability.md`.
- [x] Chốt stack và Definition of Done - xem `docs/phase-0/technology-and-dod.md`.
- [x] Chốt quy ước Git, branch, commit, code review và format - xem `docs/phase-0/git-workflow.md`, `CONTRIBUTING.md` và `.github/pull_request_template.md`.
- [x] Chụp baseline rubric/checklist; không tự ý cắt OTP, concurrency hoặc architecture diagram - xem `docs/phase-0/rubric-baseline.md`.

### Giai đoạn 1 - Phân tích và thiết kế

- [ ] Hoàn thiện Use Case Diagram.
- [ ] Hoàn thiện ERD và data ownership.
- [ ] Hoàn thiện Microservices Architecture Diagram.
- [ ] Hoàn thiện sequence/state/deployment diagrams.
- [ ] Viết OpenAPI trước cho các public API chính.
- [ ] Viết ADR: service boundaries, Saga, Outbox, locking/conditional update, idempotency.
- [ ] Review thiết kế bằng hai concurrency scenario và các failure point.

### Giai đoạn 2 - Nền tảng chạy được

- [ ] Khởi tạo monorepo và CI.
- [ ] Tạo Django `web-identity-service` với DRF, Templates, authentication, database/migration và health endpoint.
- [ ] Tạo từng FastAPI service độc lập với Pydantic, SQLAlchemy, Alembic, database/schema và health endpoint.
- [ ] Tạo Traefik/Nginx Gateway và Django Web skeleton.
- [ ] Tạo RabbitMQ, Mailpit, database trong Compose.
- [ ] Thiết lập correlation ID, error model, structured logging và OpenAPI.
- [ ] Chứng minh các service gọi nhau thật qua network/container.

### Giai đoạn 3 - Vertical slice cơ bản

- [ ] Login và `/users/me`.
- [ ] Account balance/history.
- [ ] Tuition lookup.
- [ ] UI login/dashboard/payment lookup tích hợp API thật.
- [ ] Seed data và reset demo.

### Giai đoạn 4 - OTP và payment workflow

- [ ] Create payment với Idempotency-Key.
- [ ] OTP generation/fingerprint/TTL/one-time use/resend/rate limit.
- [ ] Outbox -> RabbitMQ -> Notification -> Mailpit.
- [ ] Verify OTP.
- [ ] Saga reserve -> debit -> mark paid -> complete.
- [ ] Compensation/retry/recovery.
- [ ] UI OTP/result/history.

### Giai đoạn 5 - Concurrency và độ tin cậy

- [ ] Atomic debit và unique ledger.
- [ ] Atomic tuition reservation/mark-paid.
- [ ] Atomic OTP use và double-submit protection.
- [ ] CT-01 và CT-02 chạy lặp ổn định.
- [ ] Failure injection, recovery và reconciliation.
- [ ] Thu thập log/ảnh/report làm bằng chứng.

### Giai đoạn 6 - Chất lượng mức 10

- [ ] Unit, integration, contract, E2E test.
- [ ] API Gateway hoàn chỉnh.
- [ ] Swagger/OpenAPI cho từng service.
- [ ] Logging/tracing xuyên service bằng correlation ID.
- [ ] Security/rate limiting/secret configuration.
- [ ] Docker Compose one-command startup.
- [ ] UI polish và accessibility cơ bản.
- [ ] Không còn dữ liệu mock trong production flow.

### Giai đoạn 7 - Tài liệu và rehearsal

- [ ] README cài đặt, cấu hình, chạy, reset và troubleshooting.
- [ ] Xuất sơ đồ rõ nét, chữ đọc được.
- [ ] Hoàn thiện ma trận rubric và test report.
- [ ] Viết demo script và phân vai.
- [ ] Rehearsal từ máy sạch bằng đúng README.
- [ ] Rehearsal hai concurrency test và tình huống email lỗi.
- [ ] Chuẩn bị video/ảnh/log dự phòng nhưng ưu tiên demo trực tiếp.
- [ ] Kiểm tra quy định nộp: không in/nộp trang 3 rubric kèm báo cáo.

---

## 15. Gợi ý phân công nhóm 3 người

Mọi thành viên phải hiểu toàn bộ kiến trúc và luồng; phân công chỉ xác định người chịu trách nhiệm chính.

### Thành viên 1 - Django Web/Identity và bảo mật

- Django Templates/HTMX, Django REST Framework, authentication, JWT và user profile.
- Django Admin cho dữ liệu người dùng demo.
- Security integration giữa JWT do Django cấp và các FastAPI service.
- Phối hợp Saga/idempotency với thành viên 2.

### Thành viên 2 - FastAPI Account, Payment, OTP và Saga

- FastAPI Account service, atomic debit, ledger, history và concurrency cùng tài khoản.
- FastAPI Payment service, OTP, Outbox, Saga/recovery/compensation.
- Test hai tài khoản cùng invoice.
- OpenAPI và error model nghiệp vụ.

### Thành viên 3 - FastAPI Tuition/Notification, Gateway và DevOps

- FastAPI Tuition service và conditional reservation.
- FastAPI Notification service, RabbitMQ, Mailpit/SMTP.
- Traefik/Nginx Gateway và tích hợp UI Django.
- Docker Compose, CI, logging/tracing.
- E2E tests, tài liệu và demo assets.

### Công việc chung

- Review ERD/architecture/API.
- Pair-review code transaction/concurrency.
- Chạy test và demo chéo: người không viết chức năng phải tự chạy được chức năng đó.
- Mỗi người chuẩn bị phần bảo vệ nhưng phải trả lời được lý do chọn Saga, idempotency và locking.

---

## 16. Kịch bản demo chấm điểm

### Demo 1 - Happy path đầy đủ

1. Chạy hệ thống bằng một lệnh.
2. Mở health/Swagger nhanh để chứng minh các service độc lập.
3. Đăng nhập.
4. Chỉ ra thông tin người nộp read-only và số dư.
5. Nhập MSSV, hiển thị tên và toàn bộ số học phí.
6. Xác nhận điều khoản, tạo payment.
7. Mở Mailpit để lấy email OTP; chỉ ra thời hạn tối đa 5 phút.
8. Nhập OTP, hoàn tất.
9. Chỉ ra số dư giảm, học phí `PAID`, payment/history/ledger và email xác nhận.
10. Dùng lại OTP hoặc refresh/retry để chứng minh không trừ tiền lần hai.

### Demo 2 - Validation và lỗi

- MSSV không tồn tại.
- Khoản học phí đã thanh toán.
- Không đủ số dư.
- OTP sai/hết hạn/đã dùng.
- Chỉ ra HTTP status và error model trên Swagger/UI.

### Demo 3 - Concurrency cùng tài khoản

- Reset fixture CT-01.
- Chạy script/test đồng thời.
- Chứng minh một winner, balance không âm, đúng một debit và dữ liệu invoice nhất quán.

### Demo 4 - Concurrency cùng khoản học phí

- Reset fixture CT-02.
- Chạy script/test đồng thời.
- Chứng minh đúng một payment thành công, invoice paid một lần và account thua không mất tiền.

### Demo 5 - Engineering quality

- Chỉ Microservices Architecture Diagram và data ownership.
- Chỉ trace/correlation ID xuyên Gateway -> Payment -> Tuition/Account -> Notification.
- Chỉ OpenAPI, automated test report, E2E/concurrency test.
- Dừng Notification service, hoàn tất payment, bật lại và chứng minh email retry.
- Giải thích Saga, Outbox, idempotency, recovery và trade-off.

Demo phải dùng script ngắn, dữ liệu xác định trước, không sửa database thủ công giữa chừng ngoài cơ chế reset đã tài liệu hóa.

---

## 17. Ma trận truy vết rubric 10 điểm

| Rubric | Điểm | Hiện vật/hiện thực bắt buộc | Bằng chứng nghiệm thu |
|---|---:|---|---|
| 1. Phân tích nghiệp vụ & UML | 1.0 | Use Case đúng actor/chức năng; ERD đủ entity, thuộc tính, khóa, quan hệ | Source + ảnh sơ đồ; review với BR-01..08 |
| 2. Kiến trúc Microservices | 1.5 | Architecture Diagram; service boundary/trách nhiệm; DB riêng; REST/event/external email; giải thích lựa chọn | Chạy nhiều container; diagram + ADR + trace |
| 3. REST API | 1.0 | URI/method đầy đủ; request/response/status; validation/error handling | Swagger + API test report |
| 4. Database & Persistence | 1.0 | Migration, constraints, seed data, persistence đúng | testcontainers-python + migration/seed + constraint tests |
| 5. Chức năng & Payment Workflow | 2.0 | Login/profile/lookup; create/payment; OTP/email; update balance/tuition/history/email | E2E happy path + DB/API/UI evidence |
| 6. Transaction & Concurrency | 1.5 | Consistency; cùng account không vượt số dư; cùng invoice chỉ một success | CT-01, CT-02 chạy lặp + log/assertions |
| 7. UI & Integration | 0.5 | Đủ login -> lookup -> payment -> OTP -> result/history; gọi backend thật | Live UI demo + E2E |
| 8. Documentation, Deployment & Demo | 1.5 | README; toàn hệ thống chạy; Docker Compose; demo và giải thích | Máy sạch `docker compose up`; demo script; docs |

### Điều kiện giới hạn điểm phải loại bỏ hoàn toàn

- [ ] Có sản phẩm khởi chạy và demo được, tránh trần 4.0.
- [ ] Có nhiều microservice thực sự giao tiếp, tránh trần 6.5.
- [ ] Có quy trình OTP hoàn chỉnh, tránh trần 7.0.
- [ ] Có transaction/concurrency thật và test, tránh trần 7.5.
- [ ] Có Microservices Architecture Diagram rõ ràng, tránh trần 8.0.

### Phần nâng cao để nhắm 10

- [ ] Kiến trúc, code, test và deployment nhất quán.
- [ ] Service/data ownership rõ ràng.
- [ ] API documentation đầy đủ.
- [ ] Unit/integration/E2E/concurrency/resilience tests tự động.
- [ ] Docker Compose thuận tiện.
- [ ] Idempotency ở client API và inter-service command.
- [ ] API Gateway.
- [ ] Structured logging, correlation ID và distributed tracing.
- [ ] Outbox/Inbox, retry/DLQ, Saga recovery và reconciliation.
- [ ] Demo và phần giải thích quyết định thiết kế mạch lạc.

---

## 18. README cuối cùng phải trả lời được

- Dự án giải quyết bài toán gì?
- Kiến trúc gồm những service nào và vì sao phân rã như vậy?
- Yêu cầu phần mềm: Docker; Python và công cụ quản lý dependency như `uv`/Poetry/pip nếu chạy local không qua container.
- Cách cấu hình `.env` từ `.env.example`.
- Cách chạy toàn bộ hệ thống bằng Docker Compose.
- URL của UI, Gateway, Swagger, Mailpit và monitoring.
- Tài khoản/MSSV demo.
- Cách chạy migration/seed/reset.
- Cách chạy unit, integration, E2E và concurrency tests.
- Cách tái hiện CT-01 và CT-02, expected result cụ thể.
- Cách cấu hình SMTP thật mà không commit secret.
- Cách dừng/xóa container và xử lý lỗi thường gặp.
- Link đến diagrams, API docs, ADR và test report.

---

## 19. Rủi ro và biện pháp

| Rủi ro | Tác động | Biện pháp |
|---|---|---|
| Tách quá nhiều service nhưng không tích hợp kịp | Không demo được | Làm vertical slice sớm; ưu tiên 5 business service đã nêu, không thêm service vô ích |
| Dùng transaction local nhưng tuyên bố bảo đảm xuyên DB | Mất điểm kiến trúc/consistency | Saga + Outbox + idempotency + recovery, giải thích đúng giới hạn |
| Race condition chỉ test thủ công | Không chứng minh concurrency | Automated test có barrier, lặp nhiều lần, assertion DB |
| Trừ tiền trước rồi service chết | Dữ liệu lệch | Idempotent Saga, retry, compensation, recovery/reconciliation |
| OTP lộ trong log hoặc dùng lại | Lỗi bảo mật/nghiệp vụ | CSPRNG, HMAC fingerprint, one-time CAS, TTL/rate limit, redact log |
| Email lỗi làm rollback tài chính | Workflow dễ hỏng | Event + Outbox + retry/DLQ; email là hậu xử lý sau commit |
| UI hiển thị đúng nhưng backend thiếu validation | Có thể bypass | Mọi quy tắc kiểm tra lại tại service sở hữu dữ liệu |
| Docker chạy trên máy dev nhưng không chạy máy khác | Mất điểm demo | Test máy sạch, pin version, healthcheck, `.env.example`, seed tự động |
| Demo dài hoặc dữ liệu không ổn định | Không trình bày đủ | Script, fixture reset, phân vai, rehearsal và ảnh/video dự phòng |

---

## 20. Checklist nghiệm thu cuối trước khi nộp

### Chức năng

- [ ] Đăng nhập username/password; không có đăng ký.
- [ ] Hiển thị đúng họ tên, điện thoại, email, số dư và lịch sử.
- [ ] Payer info tự động và read-only.
- [ ] Tra cứu MSSV ra tên và toàn bộ học phí.
- [ ] Không thanh toán một phần.
- [ ] Chặn invoice không tồn tại/đã trả và account thiếu tiền.
- [ ] OTP đúng payment, không trùng khi đang hiệu lực, TTL <= 5 phút, one-time.
- [ ] OTP sai/hết hạn không chạy giao dịch.
- [ ] Thành công cập nhật balance, tuition, history và gửi email.

### Transaction/concurrency

- [ ] Kiểm tra lại số dư và invoice sau OTP.
- [ ] Cùng account không overspend.
- [ ] Cùng invoice chỉ một success.
- [ ] Double submit/retry không double debit.
- [ ] Saga retry/compensation/recovery đã test.
- [ ] Trạng thái cuối reconciliation không có sai lệch.

### Kiến trúc/API/data

- [ ] Service độc lập và có giao tiếp thật.
- [ ] Database ownership rõ, không truy cập bảng chéo.
- [ ] Architecture Diagram đầy đủ service/database/external service.
- [ ] Use Case và ERD chính xác.
- [ ] API đầy đủ URI/method/model/status/validation/error.
- [ ] Constraint, migration, seed và persistence hoạt động.

### Chất lượng và trình bày

- [ ] UI bao phủ toàn bộ luồng và gọi backend thật.
- [ ] Swagger/API docs.
- [ ] Automated tests pass, đặc biệt CT-01/CT-02.
- [ ] Docker Compose one-command.
- [ ] README chạy được trên máy sạch.
- [ ] Log/tracing minh họa được một payment xuyên hệ thống.
- [ ] Demo script và phân vai đã rehearsal.
- [ ] Không commit password, OTP, SMTP credential hoặc secret.
- [ ] Không nộp/in trang 3 rubric theo ghi chú của đề.

---

## 21. Thứ tự ưu tiên nếu thời gian bị thiếu

Không được bỏ các hạng mục gây giới hạn điểm. Thứ tự bảo vệ phạm vi:

1. Hệ thống chạy và demo được.
2. Microservices thực sự giao tiếp + Architecture Diagram.
3. Luồng chính đầy đủ gồm OTP/email.
4. Transaction/Saga và hai concurrency scenario.
5. Database/API/UI/tài liệu đúng toàn bộ rubric.
6. Automated integration/E2E/concurrency tests.
7. Docker Compose, API docs, idempotency, logging/tracing.
8. Resilience nâng cao, dashboard quan sát và UI polish.

Không dùng thiếu thời gian làm lý do chuyển thành monolith, bỏ OTP, bỏ concurrency hoặc bỏ Architecture Diagram vì các mục này trực tiếp kích hoạt trần điểm.

---

## 22. Kết luận thực thi

Đường găng của dự án là:

`Thiết kế data ownership -> dựng vertical slice -> OTP -> Saga thanh toán -> khóa/conditional update -> automated concurrency tests -> E2E -> Docker/README/demo`.

Mọi pull request phải trả lời ba câu hỏi:

1. Hạng mục này đáp ứng yêu cầu/rubric nào?
2. Test nào chứng minh nó đúng, kể cả khi retry hoặc chạy đồng thời?
3. Minh chứng nào sẽ được trình bày trong buổi demo?

Nếu toàn bộ checklist trong tài liệu này được hiện thực và chứng minh đúng, sản phẩm sẽ bao phủ đầy đủ yêu cầu công bố và có các yếu tố engineering quality mà rubric mô tả cho mức 10.
