# Quy ước Git, Pull Request và Code Review

## 1. Mô hình làm việc

Áp dụng GitHub Flow đơn giản:

- `main` luôn ở trạng thái build được, test pass và có thể demo.
- Không commit trực tiếp vào `main` sau khi repository được đưa lên remote.
- Mỗi thay đổi đi qua branch ngắn hạn và Pull Request.
- Rebase/sync với `main` trước merge; ưu tiên squash merge để lịch sử gọn.

Repository chưa được khởi tạo ở Giai đoạn 0; tài liệu này là policy phải áp dụng khi bootstrap repository ở Giai đoạn 2.

## 2. Tên branch

Mẫu: `<type>/<backlog-id>-<mo-ta-ngan-kebab-case>`

Type hợp lệ:

- `feat`: chức năng mới.
- `fix`: sửa lỗi.
- `test`: thêm/sửa test.
- `docs`: tài liệu/sơ đồ.
- `refactor`: thay cấu trúc không đổi hành vi.
- `chore`: build/tooling/dependency.
- `hotfix`: lỗi nghiêm trọng trên `main`.

Ví dụ:

- `feat/otp-001-send-otp-email`
- `test/con-001-same-account-race`
- `docs/ana-003-microservices-diagram`

## 3. Commit message

Dùng Conventional Commits:

`<type>(<scope>): <mô tả mệnh lệnh ngắn>`

Scope khuyến nghị: `web`, `identity`, `account`, `tuition`, `payment`, `notification`, `gateway`, `infra`, `docs`, `test`.

Ví dụ:

- `feat(payment): create transaction-bound OTP challenge`
- `fix(account): make debit conditional on available balance`
- `test(tuition): cover concurrent invoice reservation`
- `docs(architecture): record saga orchestration decision`

Quy tắc:

- Một commit chỉ phục vụ một ý chính.
- Không commit secret, `.env`, OTP, token, dump production hoặc credential.
- Không dùng message chung chung như `update`, `fix bug`, `done`.
- Commit breaking change phải ghi `BREAKING CHANGE:` trong body và cập nhật API/ADR.

## 4. Pull Request

- Tiêu đề: `[BACKLOG-ID] Mô tả kết quả`, ví dụ `[CON-001] Prevent overspending under concurrent debit`.
- PR nhỏ, có thể review; mục tiêu dưới khoảng 500 dòng code logic thay đổi, trừ migration/generated file.
- Link BR/AC/NFR và rubric liên quan.
- Ghi rõ API/data/state transition, migration và rủi ro concurrency/security.
- Đính kèm test result; UI thay đổi có ảnh/video ngắn.
- Không merge khi CI đỏ, còn review comment unresolved hoặc thiếu migration/docs.
- Tối thiểu một approval từ thành viên không phải tác giả.
- Phần payment/concurrency cần reviewer hiểu Account/Tuition và test race condition.

## 4.1. Chuẩn format và kiểm tra tĩnh

- Encoding UTF-8, LF, có newline cuối file; quy tắc nền nằm trong `.editorconfig`.
- Python được format và lint bằng Ruff; không tranh luận style đã được formatter quyết định.
- Type check bằng mypy; phần domain/payment không dùng `Any` để né type error nếu không có giải thích.
- Django Templates được kiểm tra/format bằng djLint.
- Markdown/YAML/JSON dùng 2 spaces khi công cụ tương ứng yêu cầu; không để trailing whitespace.
- Lệnh chuẩn sẽ được gom vào `Makefile`/scripts ở Giai đoạn 2, tối thiểu gồm `format`, `lint`, `typecheck`, `test`.

## 5. Review checklist

Reviewer kiểm tra theo thứ tự:

1. Đúng requirement/acceptance criteria, không mở rộng phạm vi ngoài ý định.
2. Service/data ownership đúng, không query/update database chéo.
3. Authentication/authorization và input validation.
4. Transaction boundary, lock/CAS, idempotency, retry và compensation.
5. Error model/status code; không lộ dữ liệu nhạy cảm.
6. Test có chứng minh lỗi thất bại trước khi fix và pass sau fix; concurrency test thực sự đồng thời.
7. Migration/constraint/seed an toàn và tái lập.
8. OpenAPI, diagram, ADR, traceability và README đồng bộ.
9. Log/trace đủ điều tra nhưng không lộ password/OTP/token.
10. Container/healthcheck không bị phá.

## 6. Chính sách merge và release tag

- Squash merge vào `main`; xóa branch sau merge.
- Không force-push `main`.
- Tag các mốc demo: `v0.1-design`, `v0.2-vertical-slice`, `v0.3-payment`, `v0.4-concurrency`, `v1.0-midterm`.
- Tag release chỉ tạo khi gate tương ứng trong `technology-and-dod.md` pass.

## 7. Xử lý xung đột và thay đổi schema/API

- Không tự ý resolve xung đột trong migration của service khác; phối hợp owner.
- Thay đổi API breaking phải có versioning/migration plan và cập nhật consumer trong cùng milestone.
- Không sửa migration đã chạy trên shared environment; thêm migration mới.
- Thay đổi state machine hoặc business invariant bắt buộc có ADR và test regression.

