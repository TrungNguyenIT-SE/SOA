# Product Backlog - Baseline Giai đoạn 0

## 1. Quy ước

- Priority `P0`: bắt buộc để không vi phạm đề/rubric hoặc giới hạn điểm.
- Priority `P1`: bắt buộc cho mục tiêu 9-10 và chất lượng demo.
- Priority `P2`: cải thiện nếu không làm ảnh hưởng P0/P1.
- Trạng thái ban đầu: `READY` nghĩa là yêu cầu đã đủ rõ để thiết kế/triển khai; không có nghĩa là đã code xong.
- Story chỉ được `DONE` khi đạt Definition of Done trong `technology-and-dod.md`.

## 2. Epic và thứ tự phụ thuộc

| Epic | Tên | Phụ thuộc | Kết quả |
|---|---|---|---|
| EP-00 | Governance và baseline | Không | Yêu cầu, traceability, stack, DoD, Git/rubric khóa |
| EP-01 | Phân tích và sơ đồ | EP-00 | Use Case, ERD, Architecture, sequence/state/deployment |
| EP-02 | Platform | EP-00, EP-01 phần kiến trúc | Repo, Compose, Gateway, DB, broker, observability |
| EP-03 | Identity và Account | EP-02 | Login/profile/balance/history/debit |
| EP-04 | Tuition | EP-02 | Lookup và reservation/mark-paid |
| EP-05 | Payment và OTP | EP-03, EP-04 | Workflow, OTP/email, Saga, idempotency |
| EP-06 | Web integration | EP-03..05 | Toàn bộ luồng UI tích hợp API thật |
| EP-07 | Concurrency và resilience | EP-05 | CT-01, CT-02, recovery/compensation |
| EP-08 | Documentation và demo | Tất cả | README, test report, demo, bảo vệ thiết kế |

## 3. Backlog chi tiết

| ID | Epic | User story/technical story | Priority | BR/NFR | Phụ thuộc | Acceptance chính | Trạng thái |
|---|---|---|---|---|---|---|---|
| GOV-001 | EP-00 | Khóa yêu cầu nguồn và thuật ngữ | P0 | BR-01..08 | - | `requirements.md` có AC và invariant | DONE |
| GOV-002 | EP-00 | Tạo ma trận truy vết end-to-end | P0 | NFR-12 | GOV-001 | Mỗi BR có API/data/UI/test/demo/rubric | DONE |
| GOV-003 | EP-00 | Khóa FastAPI/Django stack và DoD | P0 | NFR-02 | GOV-001 | Không còn công nghệ backend mâu thuẫn | DONE |
| GOV-004 | EP-00 | Khóa Git/PR/code review | P1 | NFR-12 | - | Có CONTRIBUTING và PR template | DONE |
| GOV-005 | EP-00 | Lập baseline rubric và cap gate | P0 | Rubric 1-8 | GOV-001 | Đủ 10 điểm và 5 điều kiện giới hạn | DONE |
| ANA-001 | EP-01 | Là người dùng, tôi cần Use Case Diagram đúng actor/chức năng | P0 | BR-01..08 | GOV-001 | Diagram + mô tả include/extend phù hợp | READY |
| ANA-002 | EP-01 | Là nhóm, tôi cần ERD đầy đủ và data ownership rõ | P0 | NFR-01,07 | GOV-001 | Entity/attribute/key/relation/constraint | READY |
| ANA-003 | EP-01 | Là giảng viên, tôi cần Architecture Diagram rõ ràng | P0 | NFR-01,02 | GOV-003 | Có UI/Gateway/services/DB/broker/email | READY |
| ANA-004 | EP-01 | Là nhóm, tôi cần sequence/state/deployment diagrams | P1 | BR-06..08 | ANA-003 | Happy/failure/concurrency/Saga rõ | READY |
| ANA-005 | EP-01 | Là developer, tôi cần OpenAPI-first contract | P1 | NFR-06 | GOV-001 | Public/internal API và errors được review | READY |
| PLT-001 | EP-02 | Khởi tạo monorepo Python và dependency lock | P0 | NFR-02 | GOV-003 | Cấu trúc đúng plan, build sạch | READY |
| PLT-002 | EP-02 | Dựng Traefik Gateway và routing | P1 | NFR-01 | PLT-001 | Một public entrypoint, correlation ID | READY |
| PLT-003 | EP-02 | Dựng PostgreSQL database/schema per service | P0 | NFR-01,07 | PLT-001 | User/migration riêng, không bảng chéo | READY |
| PLT-004 | EP-02 | Dựng RabbitMQ và Mailpit | P0 | BR-06,07 | PLT-001 | Event và email demo hoạt động | READY |
| PLT-005 | EP-02 | Dựng structured logging/tracing/health | P1 | NFR-05 | PLT-001 | Correlation ID xuyên service | READY |
| IDN-001 | EP-03 | Là người dùng, tôi đăng nhập bằng username/password | P0 | BR-01 | PLT-001,003 | AC-01.1..04 | READY |
| IDN-002 | EP-03 | Là người dùng, tôi xem hồ sơ payer | P0 | BR-02,03 | IDN-001 | AC-02.1,03.1..02 | READY |
| ACC-001 | EP-03 | Là người dùng, tôi xem số dư khả dụng | P0 | BR-02 | PLT-003 | AC-02.1 | READY |
| ACC-002 | EP-03 | Là người dùng, tôi xem lịch sử của mình | P0 | BR-02 | ACC-001 | AC-02.2..03 | READY |
| ACC-003 | EP-03 | Là Payment service, tôi debit nguyên tử/idempotent | P0 | BR-07,08 | ACC-001 | INV-01,02,08,09 | READY |
| ACC-004 | EP-03 | Là Payment service, tôi compensating-credit idempotent | P1 | BR-08 | ACC-003 | INV-05,08,09 | READY |
| TUI-001 | EP-04 | Là người dùng, tôi tra cứu học phí theo MSSV | P0 | BR-04 | PLT-003 | AC-04.1..04 | READY |
| TUI-002 | EP-04 | Là Payment service, tôi reserve invoice nguyên tử | P0 | BR-08 | TUI-001 | Một payment thắng trên một invoice | READY |
| TUI-003 | EP-04 | Là Payment service, tôi mark-paid/release idempotent | P0 | BR-07,08 | TUI-002 | INV-03..05,09 | READY |
| PAY-001 | EP-05 | Là payer, tôi tạo payment hợp lệ | P0 | BR-03..05 | IDN-002,ACC-001,TUI-001 | AC-03..05 và Idempotency-Key | READY |
| OTP-001 | EP-05 | Là payer, tôi nhận OTP qua email | P0 | BR-06 | PAY-001,PLT-004 | AC-06.1..04 | READY |
| OTP-002 | EP-05 | Là payer, tôi verify/resend OTP an toàn | P0 | BR-06 | OTP-001 | AC-06.5..07 | READY |
| PAY-002 | EP-05 | Là hệ thống, tôi hoàn tất payment bằng Saga | P0 | BR-07,08 | ACC-003,TUI-003,OTP-002 | AC-07, INV-01..09 | READY |
| PAY-003 | EP-05 | Là hệ thống, tôi dùng Outbox/Inbox cho event | P1 | NFR-04,11 | PAY-002,PLT-004 | Không mất/nhân đôi tác dụng event | READY |
| PAY-004 | EP-05 | Là hệ thống, tôi retry/recover/compensate Saga | P1 | BR-08 | PAY-002,ACC-004 | AC-08.3..05 | READY |
| NOT-001 | EP-05 | Là payer, tôi nhận email xác nhận | P0 | BR-07 | PAY-002,PLT-004 | AC-07.5 | READY |
| WEB-001 | EP-06 | Là người dùng, tôi dùng màn hình login/dashboard | P0 | BR-01,02 | IDN-001,002,ACC-001 | UI gọi API thật | READY |
| WEB-002 | EP-06 | Là payer, tôi tra cứu/xác nhận trên form read-only | P0 | BR-03..05 | TUI-001,PAY-001 | Điều kiện nút + backend validation | READY |
| WEB-003 | EP-06 | Là payer, tôi nhập OTP và xem kết quả/lịch sử | P0 | BR-06,07 | OTP-002,PAY-002,ACC-002 | Luồng UI hoàn chỉnh | READY |
| CON-001 | EP-07 | Kiểm thử nhiều payment cùng account | P0 | BR-08 | PAY-002 | AC-08.1,03,05,06 | READY |
| CON-002 | EP-07 | Kiểm thử nhiều account cùng invoice | P0 | BR-08 | PAY-002 | AC-08.2,03,05,06 | READY |
| RES-001 | EP-07 | Kiểm thử crash/retry/event trùng | P1 | NFR-11 | PAY-003,004 | Không corrupt/double effect | READY |
| TST-001 | EP-07 | Unit/integration/contract test | P1 | NFR-09 | EP-03..05 | Test report pass | READY |
| TST-002 | EP-07 | E2E Web/API/email | P1 | NFR-09 | EP-06 | Happy/error flow tự động | READY |
| DOC-001 | EP-08 | README one-command và troubleshooting | P0 | NFR-08,12 | EP-02..07 | Máy sạch chạy đúng hướng dẫn | READY |
| DOC-002 | EP-08 | Hoàn thiện API docs/ADR/test report | P1 | NFR-06,09,12 | EP-01..07 | Link và evidence đầy đủ | READY |
| DEM-001 | EP-08 | Script demo nghiệp vụ và hai concurrency case | P0 | BR-01..08 | Tất cả P0 | Demo lặp lại, dữ liệu reset được | READY |
| DEM-002 | EP-08 | Rehearsal và phân vai bảo vệ | P1 | Rubric 8 | DEM-001 | Mỗi thành viên giải thích được kiến trúc | READY |

## 4. Coverage BR trong backlog

| BR | Backlog chịu trách nhiệm | Coverage |
|---|---|---|
| BR-01 | IDN-001, WEB-001, TST-001/002 | Đủ |
| BR-02 | IDN-002, ACC-001/002, WEB-001/003 | Đủ |
| BR-03 | IDN-002, PAY-001, WEB-002 | Đủ |
| BR-04 | TUI-001, WEB-002 | Đủ |
| BR-05 | PAY-001, WEB-002 | Đủ |
| BR-06 | OTP-001/002, WEB-003 | Đủ |
| BR-07 | PAY-002, NOT-001, WEB-003 | Đủ |
| BR-08 | ACC-003/004, TUI-002/003, PAY-003/004, CON-001/002, RES-001 | Đủ |

## 5. Quy tắc ưu tiên

1. Không bắt đầu P2 khi P0 còn blocker.
2. Không đánh đổi Microservices, OTP, transaction/concurrency hoặc Architecture Diagram để lấy UI polish.
3. Vertical slice chạy sớm hơn tối ưu cục bộ từng service.
4. Mỗi story transaction/concurrency phải có test trước khi merge.
5. Khi thay đổi API/data/state machine, cập nhật traceability và diagram trong cùng PR.

