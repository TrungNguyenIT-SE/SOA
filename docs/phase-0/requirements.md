# Đặc tả yêu cầu đã khóa - Giai đoạn 0

## 1. Thông tin tài liệu

- Dự án: Phân hệ đóng học phí của ứng dụng iBanking.
- Môn học: Kiến Trúc Hướng Dịch Vụ - 504070, HK1/2026-2027.
- Trạng thái: Baseline v1.0.
- Ngày khóa baseline: 2026-10-19.
- Nguồn chuẩn: `ĐỀ/de1.png`, `ĐỀ/de2.png`, `ĐỀ/de3.png`, `ĐỀ/rubric-midterm.pdf` và `plan.md`.
- Ràng buộc bổ sung từ giảng viên: backend phải sử dụng cả FastAPI và Django.

Nếu tài liệu triển khai khác với yêu cầu nguồn, yêu cầu nguồn và rubric được ưu tiên. Mọi thay đổi phạm vi sau baseline phải được ghi vào mục Change Control ở cuối tài liệu.

## 2. Tác nhân và hệ thống ngoài

| Mã | Tác nhân | Trách nhiệm/phạm vi |
|---|---|---|
| ACT-01 | Người dùng iBanking | Đăng nhập, tra cứu học phí, xác nhận giao dịch, nhập OTP, xem kết quả và lịch sử |
| ACT-02 | Dịch vụ email/SMTP | Nhận yêu cầu gửi OTP và email xác nhận |
| ACT-03 | Scheduler/Recovery Worker | Hết hạn OTP/reservation, retry Outbox và phục hồi Saga |
| ACT-04 | Giảng viên/người demo | Khởi chạy, quan sát và kiểm tra các kịch bản nghiệp vụ/concurrency |

Sinh viên được tra cứu không bắt buộc là người dùng đang đăng nhập. Người dùng có thể trả học phí cho chính mình hoặc sinh viên khác.

## 3. Thuật ngữ thống nhất

| Thuật ngữ | Định nghĩa |
|---|---|
| Người nộp tiền/payer | Người dùng iBanking đang đăng nhập; tài khoản của người này bị trừ tiền |
| Sinh viên/beneficiary | Sinh viên có MSSV và khoản học phí được thanh toán; có thể khác payer |
| Khoản học phí/invoice | Toàn bộ khoản học phí còn phải thanh toán được tra cứu theo MSSV |
| Payment | Bản ghi điều phối một lần thanh toán cụ thể |
| Ledger entry | Bút toán bất biến ghi debit hoặc compensating credit trên tài khoản |
| OTP challenge | Mã xác thực gắn với một payment, có hạn và chỉ dùng thành công một lần |
| Idempotency | Cùng một yêu cầu hợp lệ được gửi lại không tạo thêm tác dụng nghiệp vụ |
| Saga | Chuỗi local transaction xuyên service kèm retry/compensation |
| Thành công một lần | Chỉ một payment được phép hoàn tất cho một khoản học phí; chỉ một debit hiệu lực tương ứng |

## 4. Yêu cầu nghiệp vụ và tiêu chí chấp nhận

### BR-01 - Đăng nhập

Người dùng đăng nhập bằng username và password. Không xây chức năng đăng ký tài khoản mới.

- AC-01.1: Given thông tin đúng và tài khoản hoạt động, when đăng nhập, then hệ thống trả phiên/token hợp lệ và chuyển tới dashboard.
- AC-01.2: Given username hoặc password sai, when đăng nhập, then trả lỗi xác thực chung, không tiết lộ trường nào sai.
- AC-01.3: API nghiệp vụ từ chối request không có token hoặc token không hợp lệ/hết hạn.
- AC-01.4: Giao diện không có chức năng đăng ký.

### BR-02 - Thông tin người dùng

Hệ thống quản lý tối thiểu họ tên, số điện thoại, email, số dư khả dụng và lịch sử giao dịch.

- AC-02.1: Sau đăng nhập, dashboard hiển thị đúng thông tin người dùng và số dư từ service sở hữu dữ liệu.
- AC-02.2: Lịch sử chỉ trả các giao dịch thuộc tài khoản đang đăng nhập, có trạng thái, số tiền và thời gian.
- AC-02.3: Người dùng không thể đọc hồ sơ, số dư, payment hoặc lịch sử của người khác.

### BR-03 - Thông tin người nộp tiền

Thông tin người nộp tiền được lấy tự động từ tài khoản đăng nhập và không cho chỉnh sửa trong luồng thanh toán.

- AC-03.1: Form hiển thị họ tên, số điện thoại, email ở chế độ read-only.
- AC-03.2: Backend lấy `payerUserId` từ token; bỏ qua/từ chối payer do client tự khai.
- AC-03.3: Account bị trừ là account của payer, kể cả khi MSSV thuộc người khác.

### BR-04 - Tra cứu khoản học phí

Người dùng nhập MSSV; hệ thống tự động trả MSSV, họ tên sinh viên và số tiền học phí còn phải thanh toán.

- AC-04.1: MSSV hợp lệ có khoản chưa trả trả đúng tên và số tiền.
- AC-04.2: MSSV không tồn tại hoặc không có khoản phù hợp trả lỗi rõ ràng.
- AC-04.3: Số tiền dùng khi tạo payment luôn lấy từ Tuition service, không tin giá trị do client gửi.
- AC-04.4: Không có chức năng nhập số tiền tùy ý; chỉ thanh toán toàn bộ khoản học phí.

### BR-05 - Điều kiện xác nhận giao dịch

Chỉ cho phép xác nhận khi khoản học phí tồn tại, chưa thanh toán, số dư khả dụng lớn hơn hoặc bằng số tiền cần trả và dữ liệu bắt buộc hợp lệ.

- AC-05.1: UI chỉ bật nút xác nhận khi dữ liệu đầy đủ, hợp lệ và điều khoản đã được chấp nhận.
- AC-05.2: Backend kiểm tra độc lập, không tin trạng thái nút/UI.
- AC-05.3: Nếu thiếu tiền, invoice đã trả hoặc dữ liệu sai, không tạo tác dụng tài chính.
- AC-05.4: Màn hình hiển thị số dư, số tiền cần thanh toán và điều khoản hệ thống trước khi xác nhận.

### BR-06 - OTP qua email

Sau khi xác nhận, hệ thống gửi OTP tới email payer. OTP gắn với một payment, không trùng OTP đang hiệu lực của giao dịch khác, hiệu lực tối đa 5 phút và chỉ dùng thành công một lần.

- AC-06.1: OTP được sinh bằng bộ sinh số ngẫu nhiên an toàn và không được trả trong API response/log.
- AC-06.2: OTP challenge tham chiếu đúng một payment và email đúng payer.
- AC-06.3: Hai payment không có cùng OTP đang ở trạng thái hiệu lực.
- AC-06.4: `expiresAt - issuedAt <= 5 phút`; OTP hết hạn bị từ chối.
- AC-06.5: OTP sai, đã dùng, bị thu hồi hoặc thuộc payment khác bị từ chối; workflow không tiếp tục.
- AC-06.6: Hai request đồng thời dùng cùng OTP chỉ có một request chuyển `ISSUED -> USED` thành công.
- AC-06.7: Resend tạo challenge mới và vô hiệu challenge cũ; có cooldown/rate limit.

### BR-07 - Xử lý giao dịch thành công

Sau OTP hợp lệ, hệ thống kiểm tra lại giao dịch/số dư, trừ tiền, cập nhật học phí đã thanh toán, lưu lịch sử, gửi email xác nhận và hiển thị kết quả.

- AC-07.1: Trước debit, hệ thống kiểm tra lại trạng thái invoice và số dư hiện tại.
- AC-07.2: Một payment thành công tạo đúng một debit ledger với đúng amount/account.
- AC-07.3: Invoice được đánh dấu `PAID` bởi đúng payment và có thời gian thanh toán.
- AC-07.4: Payment/history phản ánh đúng kết quả cuối; UI hiển thị mã giao dịch, MSSV, số tiền, thời gian và số dư mới.
- AC-07.5: Outbox phát yêu cầu email xác nhận; lỗi email được retry và không đảo ngược giao dịch tài chính đã hoàn tất.
- AC-07.6: Retry/double-click với cùng idempotency key không trừ tiền hoặc gạch nợ lần hai.

### BR-08 - Transaction và concurrency

Hệ thống bảo đảm nhất quán dữ liệu tài chính và xử lý đúng tối thiểu hai tình huống đồng thời do đề bài nêu.

- AC-08.1: Với balance 1.500.000 VND và hai invoice khác nhau mỗi invoice 1.000.000 VND được xử lý đồng thời, chính xác một payment thành công, balance cuối 500.000 VND và không âm.
- AC-08.2: Hai account đủ tiền cùng thanh toán một invoice đồng thời thì chính xác một payment thành công; invoice paid một lần và account thua không mất tiền sau trạng thái cuối.
- AC-08.3: Local update quan trọng là nguyên tử; mỗi command xuyên service idempotent theo payment/request key.
- AC-08.4: Saga đang dở có thể retry/recover; nhánh thất bại được release/compensate đúng.
- AC-08.5: Sau trạng thái cuối, payment, ledger, balance và invoice thỏa toàn bộ business invariant.
- AC-08.6: Hai concurrency test dùng barrier để tạo truy cập thật, chạy lặp và có assertion tự động.

## 5. Business invariant không được vi phạm

- INV-01: `available_balance >= 0` mọi thời điểm commit.
- INV-02: Một `paymentId` có tối đa một debit ledger hiệu lực.
- INV-03: Một tuition invoice có tối đa một payment thành công.
- INV-04: Payment `SUCCEEDED` phải có debit đúng amount và invoice `PAID` bởi cùng payment.
- INV-05: Payment `COMPENSATED` phải có debit và compensating credit cân bằng; invoice không được paid bởi payment đó.
- INV-06: OTP chỉ chuyển thành `USED` một lần, bởi đúng payment, trước hoặc tại thời điểm hết hạn theo quy ước thời gian đã chốt.
- INV-07: Client không được quyết định payer, amount hoặc trạng thái nghiệp vụ.
- INV-08: Ledger đã ghi không sửa/xóa; điều chỉnh dùng bút toán bù.
- INV-09: Mọi request retry không được tạo tác dụng kép.

## 6. Yêu cầu phi chức năng

| Mã | Yêu cầu | Tiêu chí kiểm chứng |
|---|---|---|
| NFR-01 | Microservices thật | Nhiều process/container độc lập giao tiếp REST/event; không truy cập bảng chéo |
| NFR-02 | Framework bắt buộc | Django đảm nhận Web/Identity; FastAPI đảm nhận các domain service |
| NFR-03 | Bảo mật | Password hash, JWT, authorization, secret ngoài source, OTP không lộ |
| NFR-04 | Nhất quán | Local ACID + Saga + idempotency + Outbox/Inbox + recovery |
| NFR-05 | Quan sát | Structured log, correlation ID xuyên service, trace cho payment |
| NFR-06 | API quality | OpenAPI, request/response example, validation, error model và HTTP status phù hợp |
| NFR-07 | Persistence | PostgreSQL, migration, constraints, seed và dữ liệu tồn tại sau restart |
| NFR-08 | Triển khai | Một lệnh Docker Compose khởi chạy toàn hệ thống có healthcheck |
| NFR-09 | Testability | Unit, integration, contract, E2E, concurrency và resilience test tự động |
| NFR-10 | Usability | Web responsive, loading/empty/error state và toàn bộ luồng chính |
| NFR-11 | Khả năng phục hồi | Retry có backoff, DLQ, Saga recovery/reconciliation; không double effect |
| NFR-12 | Tài liệu | README, diagrams, ADR, API docs, test report và demo script đầy đủ |

## 7. Phạm vi loại trừ đã khóa

- Không đăng ký tài khoản.
- Không thanh toán một phần.
- Không triển khai đầy đủ nghiệp vụ ngân hàng ngoài phạm vi cần cho bài.
- Không bắt buộc quản trị học phí production; dữ liệu demo có thể seed/reset trong profile riêng.
- Không dùng Django Admin thay cho Web UI nghiệp vụ.
- Không dùng shared database/table access để né giao tiếp Microservices.
- Không tuyên bố distributed ACID transaction nếu chỉ có local transaction; giải pháp chuẩn là Saga đã tài liệu hóa.

## 8. Quyết định thiết kế khác với yêu cầu bắt buộc

Các mục sau là quyết định của nhóm để đạt chất lượng cao, không phải câu chữ bắt buộc của đề:

- OTP dạng số 6 chữ số.
- JWT cho xác thực API.
- PostgreSQL, RabbitMQ, Traefik, Mailpit, Outbox/Inbox và Saga orchestration.
- Django Templates + HTMX/Alpine.js cho UI.
- Reservation trước debit và compensation khi bước sau thất bại.

Nếu thay đổi các quyết định này, giải pháp mới vẫn phải đáp ứng BR, invariant, rubric và test đã khóa.

## 9. Change Control

Mọi thay đổi phải ghi:

| Ngày | Yêu cầu/Quyết định | Lý do | Ảnh hưởng API/Data/Test/Docs | Người duyệt |
|---|---|---|---|---|
| 2026-10-19 | Baseline v1.0; bắt buộc FastAPI + Django | Yêu cầu đề và giảng viên | Khóa kiến trúc/kế hoạch Giai đoạn 0 | Nhóm |

