## Kết quả

<!-- Mô tả kết quả quan sát được, không chỉ liệt kê file đã sửa. -->

## Truy vết

- Backlog ID:
- BR/AC/NFR:
- Rubric:

## Phạm vi thay đổi

- Service/UI:
- API contract:
- Database/migration:
- State transition:

## Transaction, concurrency và idempotency

<!-- Nêu ảnh hưởng hoặc ghi N/A kèm lý do. -->

## Security và dữ liệu nhạy cảm

<!-- Authn/authz, validation, secret, OTP/token redaction. -->

## Kiểm thử

- [ ] Unit test
- [ ] Integration/contract test
- [ ] E2E test nếu ảnh hưởng luồng người dùng
- [ ] Concurrency/resilience test nếu ảnh hưởng payment/data consistency
- [ ] Test đã chạy trong container/PostgreSQL phù hợp

Lệnh và kết quả:

```text

```

## Tài liệu và minh chứng

- [ ] OpenAPI cập nhật hoặc không bị ảnh hưởng
- [ ] Diagram/ADR cập nhật hoặc không bị ảnh hưởng
- [ ] Traceability cập nhật
- [ ] UI có ảnh/video nếu thay đổi giao diện

## Checklist trước review

- [ ] Không commit secret, `.env`, OTP hoặc token
- [ ] Format/lint/type check pass
- [ ] Migration/seed an toàn
- [ ] Docker build/healthcheck không bị phá
- [ ] Definition of Done tương ứng đã đạt

