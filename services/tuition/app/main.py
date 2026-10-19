import hmac
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, FastAPI, Header, HTTPException, Path, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, create_engine, select, text, update
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from app.platform import install_platform

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://soa:soa_dev_password@postgres:5432/tuition_db")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-jwt-secret-change-me")
INTERNAL_API_TOKEN = os.getenv("INTERNAL_API_TOKEN", "dev-only-internal-token")


class Base(DeclarativeBase):
    pass


class Student(Base):
    __tablename__ = "students"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    student_code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    invoices: Mapped[list["TuitionInvoice"]] = relationship(back_populates="student")


class TuitionInvoice(Base):
    __tablename__ = "tuition_invoices"
    __table_args__ = (
        UniqueConstraint("student_id", "term", name="uq_student_term"),
        CheckConstraint("amount > 0", name="ck_tuition_positive_amount"),
        CheckConstraint("status IN ('UNPAID', 'RESERVED', 'PAID')", name="ck_tuition_status"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"), index=True)
    term: Mapped[str] = mapped_column(String(40))
    amount: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(20), default="UNPAID", index=True)
    reserved_by_payment_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, unique=True)
    reservation_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_by_payment_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, unique=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(default=0)
    student: Mapped[Student] = relationship(back_populates="invoices")


engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def seed() -> None:
    fixtures = [
        ("52400001", "Nguyễn Minh Anh", "HK1/2026-2027", 1_200_000, "UNPAID"),
        ("52400002", "Trần Quốc Bảo", "HK1/2026-2027", 1_000_000, "UNPAID"),
        ("52400003", "Lê Gia Hân", "HK1/2026-2027", 1_000_000, "UNPAID"),
        ("52400004", "Phạm Hoàng Nam", "HK1/2026-2027", 900_000, "PAID"),
        ("52400005", "Võ Khánh Linh", "HK1/2026-2027", 1_000_000, "UNPAID"),
        ("52400006", "Đặng Minh Quân", "HK1/2026-2027", 1_000_000, "UNPAID"),
        ("52400007", "Bùi Thu Trang", "HK1/2026-2027", 1_000_000, "UNPAID"),
    ]
    with SessionLocal.begin() as db:
        for code, name, term, amount, status in fixtures:
            legacy_code = code.replace("524", "522", 1)
            student = db.scalar(select(Student).where(Student.student_code == code))
            if not student:
                student = db.scalar(select(Student).where(Student.student_code == legacy_code))
            if student:
                student.student_code = code
                student.full_name = name
                continue
            student = Student(student_code=code, full_name=name)
            db.add(student)
            db.flush()
            db.add(TuitionInvoice(student_id=student.id, term=term, amount=amount, status=status, paid_at=datetime.now(timezone.utc) if status == "PAID" else None))


@asynccontextmanager
async def lifespan(_: FastAPI):
    seed()
    yield


app = FastAPI(title="Tuition Service", version="1.0.0", lifespan=lifespan)


class Claims(BaseModel):
    user_id: int


def current_user(authorization: Annotated[str | None, Header()] = None) -> Claims:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, detail={"code": "UNAUTHORIZED", "message": "Thiếu access token."})
    try:
        payload = jwt.decode(authorization[7:], JWT_SECRET, algorithms=["HS256"])
        if payload.get("type") != "access":
            raise jwt.InvalidTokenError("wrong token type")
        return Claims(user_id=int(payload["user_id"]))
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise HTTPException(401, detail={"code": "INVALID_TOKEN", "message": "Access token không hợp lệ hoặc đã hết hạn."}) from exc


def require_internal(x_internal_token: Annotated[str | None, Header()] = None) -> None:
    if not x_internal_token or not hmac.compare_digest(x_internal_token, INTERNAL_API_TOKEN):
        raise HTTPException(403, detail={"code": "FORBIDDEN", "message": "Internal token không hợp lệ."})


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    student_code: str
    student_name: str
    term: str
    amount: int
    status: str
    reserved_by_payment_id: uuid.UUID | None = None
    paid_by_payment_id: uuid.UUID | None = None


class ReservationCommand(BaseModel):
    payment_id: uuid.UUID


def invoice_out(invoice: TuitionInvoice) -> InvoiceOut:
    return InvoiceOut(
        id=invoice.id,
        student_code=invoice.student.student_code,
        student_name=invoice.student.full_name,
        term=invoice.term,
        amount=invoice.amount,
        status=invoice.status,
        reserved_by_payment_id=invoice.reserved_by_payment_id,
        paid_by_payment_id=invoice.paid_by_payment_id,
    )


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException):
    from fastapi.responses import JSONResponse

    detail = exc.detail if isinstance(exc.detail, dict) else {"code": "HTTP_ERROR", "message": str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content={**detail, "path": request.url.path})


@app.get("/health")
def health():
    return {"status": "ok", "service": "tuition"}


@app.get("/ready")
def ready():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ready", "service": "tuition"}


@app.get("/api/v1/tuition-invoices/by-student/{student_code}", response_model=InvoiceOut)
def lookup(student_code: Annotated[str, Path(min_length=3, max_length=20, pattern=r"^[A-Za-z0-9-]+$")], _: Annotated[Claims, Depends(current_user)]):
    with SessionLocal() as db:
        invoice = db.scalar(
            select(TuitionInvoice)
            .join(TuitionInvoice.student)
            .where(Student.student_code == student_code.strip().upper())
            .order_by(TuitionInvoice.term.desc())
        )
        if not invoice:
            raise HTTPException(404, detail={"code": "TUITION_NOT_FOUND", "message": "Không tìm thấy khoản học phí cho MSSV này."})
        if invoice.status == "PAID":
            raise HTTPException(409, detail={"code": "TUITION_ALREADY_PAID", "message": "Khoản học phí đã được thanh toán."})
        return invoice_out(invoice)


@app.get("/internal/v1/tuition-invoices/{invoice_id}", response_model=InvoiceOut, dependencies=[Depends(require_internal)])
def internal_get(invoice_id: uuid.UUID):
    with SessionLocal() as db:
        invoice = db.get(TuitionInvoice, invoice_id)
        if not invoice:
            raise HTTPException(404, detail={"code": "TUITION_NOT_FOUND", "message": "Không tìm thấy khoản học phí."})
        return invoice_out(invoice)


@app.post("/internal/v1/tuition-invoices/{invoice_id}/reservations", response_model=InvoiceOut, dependencies=[Depends(require_internal)])
def reserve(invoice_id: uuid.UUID, command: ReservationCommand):
    now = datetime.now(timezone.utc)
    with SessionLocal.begin() as db:
        existing = db.get(TuitionInvoice, invoice_id)
        if not existing:
            raise HTTPException(404, detail={"code": "TUITION_NOT_FOUND", "message": "Không tìm thấy khoản học phí."})
        if existing.status == "RESERVED" and existing.reserved_by_payment_id == command.payment_id:
            return invoice_out(existing)
        result = db.execute(
            update(TuitionInvoice)
            .where(TuitionInvoice.id == invoice_id, TuitionInvoice.status == "UNPAID")
            .values(status="RESERVED", reserved_by_payment_id=command.payment_id, reservation_expires_at=now + timedelta(minutes=10), version=TuitionInvoice.version + 1)
        )
        if result.rowcount != 1:
            raise HTTPException(409, detail={"code": "TUITION_UNAVAILABLE", "message": "Khoản học phí đã được giao dịch khác xử lý."})
        return invoice_out(db.get(TuitionInvoice, invoice_id))


@app.post("/internal/v1/tuition-invoices/{invoice_id}/mark-paid", response_model=InvoiceOut, dependencies=[Depends(require_internal)])
def mark_paid(invoice_id: uuid.UUID, command: ReservationCommand):
    now = datetime.now(timezone.utc)
    with SessionLocal.begin() as db:
        existing = db.get(TuitionInvoice, invoice_id)
        if not existing:
            raise HTTPException(404, detail={"code": "TUITION_NOT_FOUND", "message": "Không tìm thấy khoản học phí."})
        if existing.status == "PAID" and existing.paid_by_payment_id == command.payment_id:
            return invoice_out(existing)
        result = db.execute(
            update(TuitionInvoice)
            .where(TuitionInvoice.id == invoice_id, TuitionInvoice.status == "RESERVED", TuitionInvoice.reserved_by_payment_id == command.payment_id)
            .values(status="PAID", paid_by_payment_id=command.payment_id, paid_at=now, reserved_by_payment_id=None, reservation_expires_at=None, version=TuitionInvoice.version + 1)
        )
        if result.rowcount != 1:
            raise HTTPException(409, detail={"code": "RESERVATION_NOT_OWNED", "message": "Payment không sở hữu reservation này."})
        return invoice_out(db.get(TuitionInvoice, invoice_id))


@app.delete("/internal/v1/tuition-invoices/{invoice_id}/reservations/{payment_id}", response_model=InvoiceOut, dependencies=[Depends(require_internal)])
def release(invoice_id: uuid.UUID, payment_id: uuid.UUID):
    with SessionLocal.begin() as db:
        invoice = db.get(TuitionInvoice, invoice_id)
        if not invoice:
            raise HTTPException(404, detail={"code": "TUITION_NOT_FOUND", "message": "Không tìm thấy khoản học phí."})
        if invoice.status == "RESERVED" and invoice.reserved_by_payment_id == payment_id:
            db.execute(
                update(TuitionInvoice)
                .where(TuitionInvoice.id == invoice_id, TuitionInvoice.status == "RESERVED", TuitionInvoice.reserved_by_payment_id == payment_id)
                .values(status="UNPAID", reserved_by_payment_id=None, reservation_expires_at=None, version=TuitionInvoice.version + 1)
            )
        return invoice_out(db.get(TuitionInvoice, invoice_id))


logger = install_platform(app, "tuition")

