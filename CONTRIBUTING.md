# Contributing

Đọc trước khi phát triển:

1. `plan.md`
2. `docs/phase-0/requirements.md`
3. `docs/phase-0/backlog.md`
4. `docs/phase-0/requirements-traceability.md`
5. `docs/phase-0/technology-and-dod.md`
6. `docs/phase-0/git-workflow.md`

## Luồng đóng góp

1. Chọn một backlog item ở trạng thái `READY` và xác định owner.
2. Tạo branch theo `<type>/<backlog-id>-<description>`.
3. Code, test và cập nhật tài liệu/traceability trong cùng thay đổi.
4. Tự kiểm tra Definition of Done và điền đầy đủ PR template.
5. Yêu cầu ít nhất một review; không tự merge khi CI hoặc gate liên quan chưa pass.

FastAPI và Django đều là công nghệ bắt buộc. Không thay đổi service boundary, data ownership, OTP, Saga hoặc concurrency strategy nếu chưa có ADR và review của cả nhóm.

Không bao giờ commit password, OTP, access token, SMTP credential, private key hoặc `.env` thật.

