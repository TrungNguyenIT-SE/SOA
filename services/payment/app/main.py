import asyncio
import base64
import hashlib
import hmac
import json
import os
import secrets
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Annotated

import httpx
import jwt
import pika
from cryptography.fernet import Fernet
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint, create_engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from app.platform import correlation_id_var, install_platform

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://soa:soa_dev_password@postgres:5432/payment_db")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-jwt-secret-change-me")
INTERNAL_API_TOKEN = os.getenv("INTERNAL_API_TOKEN", "dev-only-internal-token")
OTP_PEPPER = os.getenv("OTP_PEPPER", "dev-only-otp-pepper")
OTP_TTL_SECONDS = min(int(os.getenv("OTP_TTL_SECONDS", "300")), 300)
OTP_RESEND_COOLDOWN_SECONDS = max(int(os.getenv("OTP_RESEND_COOLDOWN_SECONDS", "60")), 10)
ACCOUNT_URL = os.getenv("ACCOUNT_SERVICE_URL", "http://account:8000")
TUITION_URL = os.getenv("TUITION_SERVICE_URL", "http://tuition:8000")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/%2F")
ENABLE_FAULT_INJECTION = os.getenv("ENABLE_FAULT_INJECTION", "false").lower() == "true"
INTERNAL_HEADERS = {"X-Internal-Token": INTERNAL_API_TOKEN}


class Base(DeclarativeBase):
    pass


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("payer_user_id", "idempotency_key", name="uq_payment_payer_idempotency"),
        CheckConstraint("amount > 0", name="ck_payment_positive_amount"),
        CheckConstraint("status IN ('OTP_PENDING','PROCESSING','SUCCEEDED','EXPIRED','CANCELLED','FAILED_TUITION_UNAVAILABLE','FAILED_INSUFFICIENT_FUNDS','COMPENSATED')", name="ck_payment_status"),
        CheckConstraint("saga_step IN ('CREATED','TUITION_RESERVED','ACCOUNT_DEBITED','COMPLETED')", name="ck_payment_saga_step"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    payer_user_id: Mapped[int] = mapped_column(index=True)
    payer_name: Mapped[str] = mapped_column(String(160))
    payer_email: Mapped[str] = mapped_column(String(254))
    account_id: Mapped[uuid.UUID]
    tuition_invoice_id: Mapped[uuid.UUID] = mapped_column(index=True)
    student_code: Mapped[str] = mapped_column(String(20))
    student_name: Mapped[str] = mapped_column(String(160))
    term: Mapped[str] = mapped_column(String(40))
    amount: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(40), default="OTP_PENDING", index=True)
    failure_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(120))
    request_hash: Mapped[str] = mapped_column(String(64))
    correlation_id: Mapped[str] = mapped_column(String(128), default="-")
    saga_step: Mapped[str] = mapped_column(String(32), default="CREATED")
    recovery_attempts: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    otp: Mapped["OtpChallenge"] = relationship(back_populates="payment", uselist=False)


class OtpChallenge(Base):
    __tablename__ = "otp_challenges"
    __table_args__ = (
        CheckConstraint("status IN ('ISSUED','USED','EXPIRED','REVOKED')", name="ck_otp_status"),
        CheckConstraint("attempt_count >= 0 AND resend_count >= 0", name="ck_otp_counters"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    payment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("payments.id"), unique=True)
    code_fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="ISSUED", index=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempt_count: Mapped[int] = mapped_column(default=0)
    resend_count: Mapped[int] = mapped_column(default=0)
    payment: Mapped[Payment] = relationship(back_populates="otp")


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    __table_args__ = (UniqueConstraint("event_type", "aggregate_id", name="uq_outbox_type_aggregate"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    aggregate_id: Mapped[uuid.UUID] = mapped_column(index=True)
    payload_encrypted: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    attempt_count: Mapped[int] = mapped_column(default=0)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (UniqueConstraint("scope", "key", name="uq_idempotency_scope_key"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    scope: Mapped[str] = mapped_column(String(160))
    key: Mapped[str] = mapped_column(String(120))
    request_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)
fernet = Fernet(base64.urlsafe_b64encode(hashlib.sha256(OTP_PEPPER.encode()).digest()))


class Claims(BaseModel):
    user_id: int
    username: str = ""
    full_name: str = ""
    email: str = ""
    phone: str = ""


def current_user(authorization: Annotated[str | None, Header()] = None) -> Claims:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, detail={"code": "UNAUTHORIZED", "message": "Thiếu access token."})
    try:
        payload = jwt.decode(authorization[7:], JWT_SECRET, algorithms=["HS256"])
        if payload.get("type") != "access":
            raise jwt.InvalidTokenError("wrong token type")
        return Claims(
            user_id=int(payload["user_id"]),
            username=payload.get("username", ""),
            full_name=payload.get("full_name", ""),
            email=payload.get("email", ""),
            phone=payload.get("phone", ""),
        )
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise HTTPException(401, detail={"code": "INVALID_TOKEN", "message": "Access token không hợp lệ hoặc đã hết hạn."}) from exc


def require_internal(x_internal_token: Annotated[str | None, Header()] = None) -> None:
    if not x_internal_token or not hmac.compare_digest(x_internal_token, INTERNAL_API_TOKEN):
        raise HTTPException(403, detail={"code": "FORBIDDEN", "message": "Internal token không hợp lệ."})


class PaymentCreate(BaseModel):
    student_code: str = Field(min_length=3, max_length=20, pattern=r"^[A-Za-z0-9-]+$")
    accepted_terms: bool


class OtpVerify(BaseModel):
    otp: str = Field(pattern=r"^\d{6}$")


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    student_code: str
    student_name: str
    term: str
    amount: int
    status: str
    failure_code: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class PaymentCreated(PaymentOut):
    masked_email: str
    otp_expires_at: datetime


class OtpResent(BaseModel):
    payment_id: uuid.UUID
    masked_email: str
    otp_expires_at: datetime
    resend_count: int


class PaymentPage(BaseModel):
    items: list[PaymentOut]
    page: int
    size: int


class ServiceFailure(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message


def fingerprint(code: str) -> str:
    return hmac.new(OTP_PEPPER.encode(), code.encode(), hashlib.sha256).hexdigest()


def mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    return f"{local[:2]}***@{domain}" if domain else "***"


def encrypt_payload(payload: dict) -> str:
    return fernet.encrypt(json.dumps(payload, ensure_ascii=False).encode()).decode()


def body_hash(payload: dict) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def otp_event(payment: Payment, otp_code: str, expires_at: datetime, sequence: int = 0) -> OutboxEvent:
    return OutboxEvent(
        event_type=f"otp.requested.{sequence}",
        aggregate_id=payment.id,
        payload_encrypted=encrypt_payload({
            "event_id": str(uuid.uuid4()), "type": "otp.requested", "payment_id": str(payment.id),
            "to": payment.payer_email, "payer_name": payment.payer_name, "student_code": payment.student_code,
            "amount": payment.amount, "otp": otp_code, "expires_at": expires_at.isoformat(),
        }),
    )


def make_otp(db) -> tuple[str, str]:
    for _ in range(30):
        code = f"{secrets.randbelow(1_000_000):06d}"
        code_fp = fingerprint(code)
        active = db.scalar(select(OtpChallenge.id).where(OtpChallenge.code_fingerprint == code_fp, OtpChallenge.status == "ISSUED"))
        if not active:
            return code, code_fp
    raise HTTPException(503, detail={"code": "OTP_GENERATION_FAILED", "message": "Không thể tạo OTP, vui lòng thử lại."})


async def service_request(method: str, url: str, **kwargs) -> dict:
    headers = dict(kwargs.pop("headers", {}))
    headers["X-Correlation-Id"] = correlation_id_var.get()
    response = None
    last_error = None
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.request(method, url, headers=headers, **kwargs)
            if response.status_code < 500:
                break
        except httpx.RequestError as exc:
            last_error = exc
        if attempt < 2:
            await asyncio.sleep(0.15 * (2**attempt))
    if response is None:
        raise ServiceFailure(503, "DEPENDENCY_UNAVAILABLE", "Dịch vụ phụ thuộc tạm thời không sẵn sàng.") from last_error
    body = response.json() if response.content else {}
    if response.status_code >= 400:
        raise ServiceFailure(response.status_code, body.get("code", "DEPENDENCY_ERROR"), body.get("message", "Dịch vụ phụ thuộc từ chối yêu cầu."))
    return body


def publish_outbox_batch() -> None:
    with SessionLocal() as db:
        events = db.scalars(select(OutboxEvent).where(OutboxEvent.published_at.is_(None)).order_by(OutboxEvent.created_at).limit(20)).all()
        if not events:
            return
        connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
        try:
            channel = connection.channel()
            channel.queue_declare(queue="notifications", durable=True)
            for event in events:
                body = fernet.decrypt(event.payload_encrypted.encode())
                channel.basic_publish(
                    exchange="",
                    routing_key="notifications",
                    body=body,
                    properties=pika.BasicProperties(delivery_mode=2, content_type="application/json", message_id=str(event.id), type=event.event_type),
                )
                event.published_at = datetime.now(timezone.utc)
                event.attempt_count += 1
            db.commit()
        finally:
            connection.close()


async def outbox_loop() -> None:
    while True:
        try:
            await asyncio.to_thread(publish_outbox_batch)
        except Exception:
            pass
        await asyncio.sleep(1)


async def recovery_loop() -> None:
    await asyncio.sleep(3)
    while True:
        with SessionLocal.begin() as db:
            stuck = db.scalars(select(Payment.id).where(Payment.status == "PROCESSING").order_by(Payment.updated_at).limit(20)).all()
            if stuck:
                db.execute(
                    Payment.__table__.update().where(Payment.id.in_(stuck)).values(recovery_attempts=Payment.recovery_attempts + 1)
                )
        for payment_id in stuck:
            try:
                await execute_saga(payment_id)
            except Exception as exc:
                logger.warning(f"saga_recovery_pending payment_id={payment_id} error={type(exc).__name__}", extra={"service": "payment"})
        await asyncio.sleep(3)


async def reconciliation_loop() -> None:
    await asyncio.sleep(10)
    while True:
        try:
            issues = await reconcile_payments()
            if issues:
                logger.error(f"reconciliation_issues count={len(issues)} payment_ids={[x['payment_id'] for x in issues]}", extra={"service": "payment"})
        except Exception as exc:
            logger.warning(f"reconciliation_unavailable error={type(exc).__name__}", extra={"service": "payment"})
        await asyncio.sleep(30)


def sync_demo_metadata() -> None:
    users = [
        (1, "Hoàng Thái Đăng Khoa", os.getenv("DEMO_EMAIL_1", "payer1@example.com")),
        (2, "Đinh Thanh Phong", os.getenv("DEMO_EMAIL_2", "payer2@example.com")),
        (3, "Nguyễn Trung Nguyên", os.getenv("DEMO_EMAIL_3", "payer3@example.com")),
    ]
    with SessionLocal.begin() as db:
        for old_code, new_code in ((f"5220000{i}", f"5240000{i}") for i in range(1, 8)):
            db.execute(Payment.__table__.update().where(Payment.student_code == old_code).values(student_code=new_code))
        for user_id, full_name, email in users:
            db.execute(
                Payment.__table__.update()
                .where(Payment.payer_user_id == user_id)
                .values(payer_name=full_name, payer_email=email)
            )


@asynccontextmanager
async def lifespan(_: FastAPI):
    sync_demo_metadata()
    outbox_task = asyncio.create_task(outbox_loop())
    recovery_task = asyncio.create_task(recovery_loop())
    reconciliation_task = asyncio.create_task(reconciliation_loop())
    yield
    outbox_task.cancel()
    recovery_task.cancel()
    reconciliation_task.cancel()


app = FastAPI(title="Payment and OTP Service", version="1.0.0", lifespan=lifespan)


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException):
    from fastapi.responses import JSONResponse

    detail = exc.detail if isinstance(exc.detail, dict) else {"code": "HTTP_ERROR", "message": str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content={**detail, "path": request.url.path})


@app.exception_handler(ServiceFailure)
async def service_error_handler(request: Request, exc: ServiceFailure):
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=exc.status_code, content={"code": exc.code, "message": exc.message, "path": request.url.path})


@app.get("/health")
def health():
    return {"status": "ok", "service": "payment"}


@app.get("/ready")
def ready():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ready", "service": "payment"}


@app.post("/api/v1/payments", response_model=PaymentCreated, status_code=201)
async def create_payment(
    body: PaymentCreate,
    user: Annotated[Claims, Depends(current_user)],
    authorization: Annotated[str, Header()],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    if not idempotency_key or len(idempotency_key) > 120:
        raise HTTPException(400, detail={"code": "IDEMPOTENCY_KEY_REQUIRED", "message": "Idempotency-Key là bắt buộc."})
    if not body.accepted_terms:
        raise HTTPException(422, detail={"code": "TERMS_NOT_ACCEPTED", "message": "Bạn phải đồng ý điều khoản trước khi thanh toán."})
    request_fingerprint = body_hash({"student_code": body.student_code.strip().upper(), "accepted_terms": body.accepted_terms})

    with SessionLocal() as db:
        existing = db.scalar(select(Payment).where(Payment.payer_user_id == user.user_id, Payment.idempotency_key == idempotency_key))
        if existing:
            if existing.request_hash != request_fingerprint:
                raise HTTPException(409, detail={"code": "IDEMPOTENCY_KEY_REUSED", "message": "Idempotency-Key đã được dùng với nội dung khác."})
            return PaymentCreated(**PaymentOut.model_validate(existing).model_dump(), masked_email=mask_email(existing.payer_email), otp_expires_at=existing.otp.expires_at)

    tuition = await service_request(
        "GET",
        f"{TUITION_URL}/api/v1/tuition-invoices/by-student/{body.student_code.strip().upper()}",
        headers={"Authorization": authorization},
    )
    account = await service_request("GET", f"{ACCOUNT_URL}/internal/v1/accounts/by-user/{user.user_id}", headers=INTERNAL_HEADERS)
    if int(account["available_balance"]) < int(tuition["amount"]):
        raise HTTPException(422, detail={"code": "INSUFFICIENT_FUNDS", "message": "Số dư khả dụng không đủ để thanh toán toàn bộ học phí."})

    now = datetime.now(timezone.utc)
    try:
        with SessionLocal.begin() as db:
            code, code_fp = make_otp(db)
            payment = Payment(
                payer_user_id=user.user_id,
                payer_name=user.full_name,
                payer_email=user.email,
                account_id=uuid.UUID(account["id"]),
                tuition_invoice_id=uuid.UUID(tuition["id"]),
                student_code=tuition["student_code"],
                student_name=tuition["student_name"],
                term=tuition["term"],
                amount=int(tuition["amount"]),
                status="OTP_PENDING",
                idempotency_key=idempotency_key,
                request_hash=request_fingerprint,
                correlation_id=correlation_id_var.get(),
            )
            db.add(payment)
            db.flush()
            otp = OtpChallenge(payment_id=payment.id, code_fingerprint=code_fp, issued_at=now, expires_at=now + timedelta(seconds=OTP_TTL_SECONDS))
            db.add(otp)
            db.add(otp_event(payment, code, otp.expires_at))
            db.flush()
            result = PaymentCreated(**PaymentOut.model_validate(payment).model_dump(), masked_email=mask_email(user.email), otp_expires_at=otp.expires_at)
        return result
    except IntegrityError:
        with SessionLocal() as db:
            existing = db.scalar(select(Payment).where(Payment.payer_user_id == user.user_id, Payment.idempotency_key == idempotency_key))
            if not existing:
                raise
            if existing.request_hash != request_fingerprint:
                raise HTTPException(409, detail={"code": "IDEMPOTENCY_KEY_REUSED", "message": "Idempotency-Key đã được dùng với nội dung khác."})
            return PaymentCreated(**PaymentOut.model_validate(existing).model_dump(), masked_email=mask_email(existing.payer_email), otp_expires_at=existing.otp.expires_at)


def set_failure(payment_id: uuid.UUID, status: str, code: str) -> None:
    with SessionLocal.begin() as db:
        payment = db.get(Payment, payment_id)
        if payment:
            payment.status = status
            payment.failure_code = code
            payment.completed_at = datetime.now(timezone.utc)


@app.post("/api/v1/payments/{payment_id}/otp/resend", response_model=OtpResent, status_code=202)
def resend_otp(payment_id: uuid.UUID, user: Annotated[Claims, Depends(current_user)]):
    now = datetime.now(timezone.utc)
    with SessionLocal.begin() as db:
        payment = db.scalar(select(Payment).where(Payment.id == payment_id).with_for_update())
        if not payment or payment.payer_user_id != user.user_id:
            raise HTTPException(404, detail={"code": "PAYMENT_NOT_FOUND", "message": "Không tìm thấy giao dịch."})
        if payment.status != "OTP_PENDING":
            raise HTTPException(409, detail={"code": "PAYMENT_INVALID_STATE", "message": "Chỉ có thể gửi lại OTP cho giao dịch đang chờ xác thực."})
        otp = db.scalar(select(OtpChallenge).where(OtpChallenge.payment_id == payment.id).with_for_update())
        if not otp:
            raise HTTPException(409, detail={"code": "OTP_NOT_FOUND", "message": "Không tìm thấy OTP của giao dịch."})
        elapsed = (now - otp.issued_at).total_seconds()
        if elapsed < OTP_RESEND_COOLDOWN_SECONDS:
            retry_after = int(OTP_RESEND_COOLDOWN_SECONDS - elapsed) + 1
            raise HTTPException(429, detail={"code": "OTP_RESEND_COOLDOWN", "message": f"Vui lòng chờ {retry_after} giây trước khi gửi lại OTP."})
        if otp.resend_count >= 3:
            raise HTTPException(429, detail={"code": "OTP_RESEND_LIMIT", "message": "Đã vượt quá số lần gửi lại OTP."})
        code, code_fp = make_otp(db)
        otp.code_fingerprint = code_fp
        otp.status = "ISSUED"
        otp.issued_at = now
        otp.expires_at = now + timedelta(seconds=OTP_TTL_SECONDS)
        otp.used_at = None
        otp.attempt_count = 0
        otp.resend_count += 1
        db.add(otp_event(payment, code, otp.expires_at, otp.resend_count))
        return OtpResent(payment_id=payment.id, masked_email=mask_email(payment.payer_email), otp_expires_at=otp.expires_at, resend_count=otp.resend_count)


def saga_snapshot(payment_id: uuid.UUID) -> dict:
    with SessionLocal() as db:
        payment = db.get(Payment, payment_id)
        if not payment:
            raise HTTPException(404, detail={"code": "PAYMENT_NOT_FOUND", "message": "Không tìm thấy giao dịch."})
        return {
            "id": payment.id, "account_id": payment.account_id, "invoice_id": payment.tuition_invoice_id,
            "amount": payment.amount, "student_code": payment.student_code, "term": payment.term,
            "step": payment.saga_step, "status": payment.status,
        }


def save_saga_step(payment_id: uuid.UUID, step: str) -> None:
    with SessionLocal.begin() as db:
        payment = db.scalar(select(Payment).where(Payment.id == payment_id).with_for_update())
        if payment and payment.status == "PROCESSING":
            payment.saga_step = step


def complete_payment(payment_id: uuid.UUID, balance_after: int) -> Payment:
    with SessionLocal.begin() as db:
        payment = db.scalar(select(Payment).where(Payment.id == payment_id).with_for_update())
        if payment.status == "SUCCEEDED":
            return payment
        payment.status = "SUCCEEDED"
        payment.saga_step = "COMPLETED"
        payment.failure_code = None
        payment.completed_at = datetime.now(timezone.utc)
        db.add(OutboxEvent(event_type="payment.completed", aggregate_id=payment.id, payload_encrypted=encrypt_payload({
            "event_id": str(uuid.uuid4()), "type": "payment.completed", "payment_id": str(payment.id),
            "to": payment.payer_email, "payer_name": payment.payer_name, "student_code": payment.student_code,
            "student_name": payment.student_name, "amount": payment.amount, "balance_after": balance_after,
            "completed_at": payment.completed_at.isoformat(),
        })))
        db.flush()
        return payment


async def execute_saga(payment_id: uuid.UUID, fault_point: str | None = None) -> Payment:
    payment = saga_snapshot(payment_id)
    if payment["status"] == "SUCCEEDED":
        with SessionLocal() as db:
            return db.get(Payment, payment_id)
    if payment["status"] != "PROCESSING":
        raise HTTPException(409, detail={"code": "PAYMENT_INVALID_STATE", "message": f"Saga không thể chạy ở trạng thái {payment['status']}."})

    try:
        await service_request("POST", f"{TUITION_URL}/internal/v1/tuition-invoices/{payment['invoice_id']}/reservations", headers=INTERNAL_HEADERS, json={"payment_id": str(payment_id)})
        save_saga_step(payment_id, "TUITION_RESERVED")
    except ServiceFailure as exc:
        if exc.status_code >= 500:
            raise HTTPException(503, detail={"code": "SAGA_RECOVERY_PENDING", "message": "Giao dịch đang chờ hệ thống tự động tiếp tục."}) from exc
        set_failure(payment_id, "FAILED_TUITION_UNAVAILABLE", exc.code)
        raise HTTPException(409, detail={"code": "TUITION_UNAVAILABLE", "message": "Khoản học phí đã được giao dịch khác xử lý."}) from exc

    try:
        account = await service_request("POST", f"{ACCOUNT_URL}/internal/v1/accounts/{payment['account_id']}/debits", headers=INTERNAL_HEADERS, json={"payment_id": str(payment_id), "amount": payment["amount"], "description": f"Học phí {payment['student_code']} {payment['term']}"})
        save_saga_step(payment_id, "ACCOUNT_DEBITED")
        if ENABLE_FAULT_INJECTION and fault_point == "after_debit":
            raise HTTPException(503, detail={"code": "SAGA_RECOVERY_PENDING", "message": "Đã mô phỏng gián đoạn sau bước debit; recovery worker sẽ tiếp tục."})
    except ServiceFailure as exc:
        if exc.status_code >= 500:
            raise HTTPException(503, detail={"code": "SAGA_RECOVERY_PENDING", "message": "Giao dịch đang chờ hệ thống tự động tiếp tục."}) from exc
        await service_request("DELETE", f"{TUITION_URL}/internal/v1/tuition-invoices/{payment['invoice_id']}/reservations/{payment_id}", headers=INTERNAL_HEADERS)
        set_failure(payment_id, "FAILED_INSUFFICIENT_FUNDS", exc.code)
        raise HTTPException(422, detail={"code": exc.code, "message": exc.message}) from exc

    try:
        await service_request("POST", f"{TUITION_URL}/internal/v1/tuition-invoices/{payment['invoice_id']}/mark-paid", headers=INTERNAL_HEADERS, json={"payment_id": str(payment_id)})
    except ServiceFailure as exc:
        if exc.status_code >= 500:
            raise HTTPException(503, detail={"code": "SAGA_RECOVERY_PENDING", "message": "Giao dịch đang chờ hệ thống tự động tiếp tục."}) from exc
        await service_request("POST", f"{ACCOUNT_URL}/internal/v1/accounts/{payment['account_id']}/compensating-credits", headers=INTERNAL_HEADERS, json={"payment_id": str(payment_id), "amount": payment["amount"], "description": "Hoàn tiền do không thể cập nhật học phí"})
        await service_request("DELETE", f"{TUITION_URL}/internal/v1/tuition-invoices/{payment['invoice_id']}/reservations/{payment_id}", headers=INTERNAL_HEADERS)
        set_failure(payment_id, "COMPENSATED", exc.code)
        raise HTTPException(409, detail={"code": "PAYMENT_COMPENSATED", "message": "Giao dịch không hoàn tất và số tiền đã được hoàn lại."}) from exc
    return complete_payment(payment_id, int(account["available_balance"]))


async def reconcile_payments() -> list[dict]:
    with SessionLocal() as db:
        payments = db.scalars(select(Payment).where(Payment.status.in_(["SUCCEEDED", "COMPENSATED"]))).all()
        snapshots = [{"id": p.id, "status": p.status, "account_id": p.account_id, "invoice_id": p.tuition_invoice_id, "amount": p.amount} for p in payments]
    issues = []
    for payment in snapshots:
        try:
            ledger = await service_request("GET", f"{ACCOUNT_URL}/internal/v1/accounts/{payment['account_id']}/ledger/{payment['id']}", headers=INTERNAL_HEADERS)
            invoice = await service_request("GET", f"{TUITION_URL}/internal/v1/tuition-invoices/{payment['invoice_id']}", headers=INTERNAL_HEADERS)
            if payment["status"] == "SUCCEEDED":
                valid = ledger["debit_count"] == 1 and ledger["credit_count"] == 0 and ledger["debit_amount"] == payment["amount"] and invoice["status"] == "PAID" and invoice["paid_by_payment_id"] == str(payment["id"])
            else:
                valid = ledger["debit_count"] == 1 and ledger["credit_count"] == 1 and ledger["debit_amount"] == ledger["credit_amount"] and invoice["paid_by_payment_id"] != str(payment["id"])
            if not valid:
                issues.append({"payment_id": str(payment["id"]), "status": payment["status"], "code": "STATE_MISMATCH"})
        except ServiceFailure as exc:
            issues.append({"payment_id": str(payment["id"]), "status": payment["status"], "code": exc.code})
    return issues


@app.get("/internal/v1/reconciliation", dependencies=[Depends(require_internal)])
async def reconciliation():
    issues = await reconcile_payments()
    return {"status": "ok" if not issues else "issues_found", "checked_at": datetime.now(timezone.utc), "issues": issues}


@app.post("/api/v1/payments/{payment_id}/otp/verify", response_model=PaymentOut)
async def verify_otp(
    payment_id: uuid.UUID,
    body: OtpVerify,
    user: Annotated[Claims, Depends(current_user)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    fault_point: Annotated[str | None, Header(alias="X-Fault-Point")] = None,
):
    if not idempotency_key:
        raise HTTPException(400, detail={"code": "IDEMPOTENCY_KEY_REQUIRED", "message": "Idempotency-Key là bắt buộc."})
    now = datetime.now(timezone.utc)
    with SessionLocal.begin() as db:
        payment = db.scalar(select(Payment).where(Payment.id == payment_id).with_for_update())
        if not payment or payment.payer_user_id != user.user_id:
            raise HTTPException(404, detail={"code": "PAYMENT_NOT_FOUND", "message": "Không tìm thấy giao dịch."})
        scope = f"verify:{user.user_id}:{payment.id}"
        verify_hash = body_hash({"otp": body.otp})
        record = db.scalar(select(IdempotencyRecord).where(IdempotencyRecord.scope == scope, IdempotencyRecord.key == idempotency_key))
        if record and record.request_hash != verify_hash:
            raise HTTPException(409, detail={"code": "IDEMPOTENCY_KEY_REUSED", "message": "Idempotency-Key đã được dùng với nội dung khác."})
        if not record:
            db.add(IdempotencyRecord(scope=scope, key=idempotency_key, request_hash=verify_hash))
        if payment.status == "SUCCEEDED":
            return payment
        if payment.status != "OTP_PENDING":
            raise HTTPException(409, detail={"code": "PAYMENT_INVALID_STATE", "message": f"Không thể xác thực giao dịch ở trạng thái {payment.status}."})
        otp = db.scalar(select(OtpChallenge).where(OtpChallenge.payment_id == payment.id).with_for_update())
        if not otp or otp.status != "ISSUED" or otp.used_at is not None:
            raise HTTPException(422, detail={"code": "OTP_ALREADY_USED", "message": "OTP đã được sử dụng hoặc không còn hiệu lực."})
        otp_error: tuple[str, str] | None = None
        if now >= otp.expires_at:
            otp.status = "EXPIRED"
            payment.status = "EXPIRED"
            payment.failure_code = "OTP_EXPIRED"
            otp_error = ("OTP_EXPIRED", "OTP đã hết hạn.")
        elif not hmac.compare_digest(otp.code_fingerprint, fingerprint(body.otp)):
            otp.attempt_count += 1
            if otp.attempt_count >= 5:
                otp.status = "REVOKED"
                payment.status = "CANCELLED"
                payment.failure_code = "OTP_ATTEMPTS_EXCEEDED"
                otp_error = ("OTP_ATTEMPTS_EXCEEDED", "OTP đã bị khóa do nhập sai quá nhiều lần.")
            else:
                otp_error = ("OTP_INVALID", "OTP không chính xác.")
        else:
            otp.status = "USED"
            otp.used_at = now
            payment.status = "PROCESSING"

    if otp_error:
        raise HTTPException(422, detail={"code": otp_error[0], "message": otp_error[1]})

    return await execute_saga(payment_id, fault_point)


@app.get("/api/v1/payments/{payment_id}", response_model=PaymentOut)
def get_payment(payment_id: uuid.UUID, user: Annotated[Claims, Depends(current_user)]):
    with SessionLocal() as db:
        payment = db.get(Payment, payment_id)
        if not payment or payment.payer_user_id != user.user_id:
            raise HTTPException(404, detail={"code": "PAYMENT_NOT_FOUND", "message": "Không tìm thấy giao dịch."})
        return payment


@app.get("/api/v1/payments", response_model=PaymentPage)
def list_payments(
    user: Annotated[Claims, Depends(current_user)],
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    with SessionLocal() as db:
        items = db.scalars(
            select(Payment)
            .where(Payment.payer_user_id == user.user_id)
            .order_by(Payment.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        ).all()
        return PaymentPage(items=[PaymentOut.model_validate(item) for item in items], page=page, size=size)


logger = install_platform(app, "payment")

