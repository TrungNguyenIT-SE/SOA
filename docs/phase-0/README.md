# Giai đoạn 0 - Scope and Governance Baseline

## Kết quả

Giai đoạn 0 đã hoàn thành ở mức tài liệu và governance. Chưa có tuyên bố nào rằng chức năng đã được code hoặc rubric implementation đã đạt điểm.

| Đầu việc trong `plan.md` | Hiện vật | Kết quả |
|---|---|---|
| Đưa BR-01..08 vào backlog | `requirements.md`, `backlog.md` | DONE |
| Ma trận yêu cầu - API - data - test - UI - demo | `requirements-traceability.md` | DONE |
| Chốt stack và Definition of Done | `technology-and-dod.md` | DONE |
| Chốt Git/branch/commit/review/format | `git-workflow.md`, `CONTRIBUTING.md`, `.editorconfig`, PR template | DONE |
| Baseline rubric và bảo vệ cap | `rubric-baseline.md` | DONE |

## Index

- [Đặc tả yêu cầu](requirements.md)
- [Product backlog](backlog.md)
- [Ma trận truy vết](requirements-traceability.md)
- [Technology baseline và Definition of Done](technology-and-dod.md)
- [Git workflow và code review](git-workflow.md)
- [Rubric baseline](rubric-baseline.md)
- [Kế hoạch tổng thể](../../plan.md)
- [Hướng dẫn đóng góp](../../CONTRIBUTING.md)
- [Pull Request template](../../.github/pull_request_template.md)
- [EditorConfig](../../.editorconfig)

## Các quyết định đã khóa

- Dùng cả Django và FastAPI với vai trò thực tế.
- Django đảm nhận Web/Identity; FastAPI đảm nhận Account/Tuition/Payment/Notification.
- PostgreSQL với data ownership riêng theo service.
- Saga orchestration + Outbox/Inbox + idempotency cho workflow xuyên service.
- Atomic debit và atomic tuition reservation cho hai concurrency scenario.
- RabbitMQ + Mailpit cho email bất đồng bộ trong môi trường demo.
- Docker Compose, OpenAPI, automated E2E/concurrency tests và logging/tracing là phạm vi release.

## Gate G0

| Kiểm tra | Kết quả |
|---|---|
| BR-01..08 đều có acceptance criteria | PASS |
| BR-01..08 đều xuất hiện trong backlog | PASS |
| Mỗi BR có đường truy vết API/data/UI/test/demo/rubric | PASS |
| 8 tiêu chí rubric tổng đúng 10.0 | PASS |
| 5 điều kiện giới hạn điểm được ghi và có prevention gate | PASS |
| FastAPI và Django được phân vai, không còn Java/Spring | PASS |
| DoD và quality gate được định nghĩa | PASS |
| Git/PR/review policy và template tồn tại | PASS |

## Điều kiện để bắt đầu Giai đoạn 1

- Nhóm đọc và xác nhận baseline.
- Gán tên thật cho owner backlog sau khi biết thành viên.
- Mọi thay đổi yêu cầu mới từ giảng viên phải thêm vào Change Control và traceability trước khi thiết kế.
- Giai đoạn 1 phải tạo tối thiểu Use Case, ERD và Microservices Architecture Diagram; không được bắt đầu code payment khi state/data/API chưa được review.

