import hmac
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Annotated

import jwt
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, create_engine, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

from app.platform import install_platform

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://soa:soa_dev_password@postgres:5432/account_db")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-jwt-secret-change-me")
INTERNAL_API_TOKEN = os.getenv("INTERNAL_API_TOKEN", "dev-only-internal-token")


class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint("available_balance >= 0", name="ck_account_nonnegative_balance"),
        CheckConstraint("currency = 'VND'", name="ck_account_currency_vnd"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(unique=True, index=True)
    account_number: Mapped[str] = mapped_column(String(20), unique=True)
    currency: Mapped[str] = mapped_column(String(3), default="VND")
    available_balance: Mapped[int] = mapped_column(BigInteger)
    version: Mapped[int] = mapped_column(default=0)
    entries: Mapped[list["LedgerEntry"]] = relationship(back_populates="account")


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    __table_args__ = (
        UniqueConstraint("payment_id", "entry_type", name="uq_ledger_payment_type"),
        CheckConstraint("amount > 0", name="ck_ledger_positive_amount"),
        CheckConstraint("entry_type IN ('DEBIT', 'COMPENSATING_CREDIT')", name="ck_ledger_entry_type"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id"), index=True)
    payment_id: Mapped[uuid.UUID] = mapped_column(index=True)
    entry_type: Mapped[str] = mapped_column(String(24))
    amount: Mapped[int] = mapped_column(BigInteger)
    balance_after: Mapped[int] = mapped_column(BigInteger)
    description: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    account: Mapped[Account] = relationship(back_populates="entries")


engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def seed() -> None:
    with SessionLocal.begin() as db:
        if db.scalar(select(Account.id).limit(1)):
            return
        db.add_all(
            [
                Account(user_id=1, account_number="970400000001", available_balance=5_000_000),
                Account(user_id=2, account_number="970400000002", available_balance=3_000_000),
                Account(user_id=3, account_number="970400000003", available_balance=1_500_000),
            ]
        )


@asynccontextmanager
async def lifespan(_: FastAPI):
    seed()
    yield


app = FastAPI(title="Account Service", version="1.0.0", lifespan=lifespan)


class UserClaims(BaseModel):
    user_id: int
    username: str = ""
    email: str = ""
    full_name: str = ""


bearer_scheme = HTTPBearer(auto_error=False)


def current_user(
    cred: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> UserClaims:
    raw_token = cred.credentials if (cred and cred.credentials) else None
    if not raw_token and authorization and authorization.startswith("Bearer "):
        raw_token = authorization[7:].strip()
    if not raw_token:
        raise HTTPException(401, detail={"code": "UNAUTHORIZED", "message": "Thiếu access token."})
    try:
        payload = jwt.decode(raw_token, JWT_SECRET, algorithms=["HS256"])
        if payload.get("type") != "access":
            raise jwt.InvalidTokenError("wrong token type")
        return UserClaims(
            user_id=int(payload["user_id"]),
            username=payload.get("username", ""),
            email=payload.get("email", ""),
            full_name=payload.get("full_name", ""),
        )
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise HTTPException(401, detail={"code": "INVALID_TOKEN", "message": "Access token không hợp lệ hoặc đã hết hạn."}) from exc


def require_internal(x_internal_token: Annotated[str | None, Header()] = None) -> None:
    if not x_internal_token or not hmac.compare_digest(x_internal_token, INTERNAL_API_TOKEN):
        raise HTTPException(403, detail={"code": "FORBIDDEN", "message": "Internal token không hợp lệ."})


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    account_number: str
    currency: str
    available_balance: int


class LedgerOut(BaseModel):
    id: uuid.UUID
    payment_id: uuid.UUID
    type: str
    amount: int
    balance_after: int
    created_at: datetime


class PageOut(BaseModel):
    items: list[LedgerOut]
    page: int
    size: int


class LedgerState(BaseModel):
    debit_count: int
    credit_count: int
    debit_amount: int
    credit_amount: int


class MoneyCommand(BaseModel):
    payment_id: uuid.UUID
    amount: int = Field(gt=0)
    description: str = Field(default="Thanh toán học phí", max_length=255)


def get_account_for_user(db: Session, user_id: int) -> Account:
    account = db.scalar(select(Account).where(Account.user_id == user_id))
    if not account:
        try:
            account = Account(
                user_id=user_id,
                account_number=f"9704{user_id:08d}",
                available_balance=10_000_000,
            )
            db.add(account)
            db.commit()
            db.refresh(account)
        except Exception:
            db.rollback()
            account = db.scalar(select(Account).where(Account.user_id == user_id))
            if not account:
                raise HTTPException(404, detail={"code": "ACCOUNT_NOT_FOUND", "message": "Không tìm thấy tài khoản."})
    return account


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException):
    from fastapi.responses import JSONResponse

    detail = exc.detail if isinstance(exc.detail, dict) else {"code": "HTTP_ERROR", "message": str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content={**detail, "path": request.url.path})


@app.get("/health", tags=["Hệ thống (Health)"], summary="Kiểm tra trạng thái Service")
def health():
    return {"status": "ok", "service": "account"}


@app.get("/ready", tags=["Hệ thống (Health)"], summary="Kiểm tra kết nối Database Account")
def ready():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ready", "service": "account"}


class DepositCommand(BaseModel):
    account_number: str
    amount: int = Field(gt=0)


@app.get("/api/v1/accounts", response_model=list[AccountOut], tags=["Tài khoản & Số dư"], summary="Xem danh sách toàn bộ tài khoản ngân hàng")
def list_accounts():
    """Xem danh sách toàn bộ tài khoản ngân hàng"""
    with SessionLocal() as db:
        accounts = db.scalars(select(Account).order_by(Account.id)).all()
        return [AccountOut.model_validate(acc) for acc in accounts]


@app.post("/api/v1/accounts/deposit", response_model=AccountOut, tags=["Tài khoản & Số dư"], summary="Nạp thêm tiền vào tài khoản ngân hàng")
def deposit(command: DepositCommand):
    """Nạp thêm tiền vào tài khoản"""
    with SessionLocal.begin() as db:
        account = db.scalar(select(Account).where(Account.account_number == command.account_number.strip()))
        if not account:
            raise HTTPException(404, detail={"code": "ACCOUNT_NOT_FOUND", "message": "Không tìm thấy số tài khoản."})
        account.available_balance += command.amount
        account.version += 1
        db.flush()
        return AccountOut.model_validate(account)


@app.get("/api/v1/accounts/me", response_model=AccountOut, tags=["Tài khoản & Số dư"], summary="Xem số dư khả dụng tài khoản đăng nhập")
def my_account(user: Annotated[UserClaims, Depends(current_user)]):
    with SessionLocal() as db:
        return get_account_for_user(db, user.user_id)


@app.get("/api/v1/accounts/me/transactions", response_model=PageOut, tags=["Tài khoản & Số dư"], summary="Xem lịch sử giao dịch (Ledger)")
def my_transactions(
    user: Annotated[UserClaims, Depends(current_user)],
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    with SessionLocal() as db:
        account = get_account_for_user(db, user.user_id)
        entries = db.scalars(
            select(LedgerEntry)
            .where(LedgerEntry.account_id == account.id)
            .order_by(LedgerEntry.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        ).all()
        return PageOut(
            items=[
                LedgerOut(
                    id=item.id,
                    payment_id=item.payment_id,
                    type=item.entry_type,
                    amount=item.amount,
                    balance_after=item.balance_after,
                    created_at=item.created_at,
                )
                for item in entries
            ],
            page=page,
            size=size,
        )


@app.get("/internal/v1/accounts/by-user/{user_id}", response_model=AccountOut, dependencies=[Depends(require_internal)])
def account_by_user(user_id: int):
    with SessionLocal() as db:
        return get_account_for_user(db, user_id)


class BalanceUpdate(BaseModel):
    available_balance: int = Field(ge=0)


@app.put("/internal/v1/accounts/by-user/{user_id}/balance", response_model=AccountOut, dependencies=[Depends(require_internal)])
def update_balance_by_user(user_id: int, body: BalanceUpdate):
    with SessionLocal.begin() as db:
        account = get_account_for_user(db, user_id)
        account.available_balance = body.available_balance
        account.version += 1
        db.flush()
        return account


@app.post("/internal/v1/accounts/{account_id}/debits", response_model=AccountOut, dependencies=[Depends(require_internal)], tags=["Nội bộ (Saga)"], summary="Trừ tiền tài khoản nguyên tử có kiểm tra số dư")
def debit(account_id: uuid.UUID, command: MoneyCommand):
    try:
        with SessionLocal.begin() as db:
            existing = db.scalar(
                select(LedgerEntry).where(
                    LedgerEntry.payment_id == command.payment_id,
                    LedgerEntry.entry_type == "DEBIT",
                )
            )
            if existing:
                return db.get(Account, existing.account_id)

            result = db.execute(
                update(Account)
                .where(Account.id == account_id, Account.available_balance >= command.amount)
                .values(
                    available_balance=Account.available_balance - command.amount,
                    version=Account.version + 1,
                )
            )
            if result.rowcount != 1:
                if not db.get(Account, account_id):
                    raise HTTPException(404, detail={"code": "ACCOUNT_NOT_FOUND", "message": "Không tìm thấy tài khoản."})
                raise HTTPException(422, detail={"code": "INSUFFICIENT_FUNDS", "message": "Số dư khả dụng không đủ."})

            account = db.get(Account, account_id)
            db.add(
                LedgerEntry(
                    account_id=account.id,
                    payment_id=command.payment_id,
                    entry_type="DEBIT",
                    amount=command.amount,
                    balance_after=account.available_balance,
                    description=command.description,
                )
            )
            db.flush()
            return account
    except IntegrityError:
        with SessionLocal() as db:
            existing = db.scalar(select(LedgerEntry).where(LedgerEntry.payment_id == command.payment_id, LedgerEntry.entry_type == "DEBIT"))
            if existing:
                return db.get(Account, existing.account_id)
        raise


@app.post("/internal/v1/accounts/{account_id}/compensating-credits", response_model=AccountOut, dependencies=[Depends(require_internal)], tags=["Nội bộ (Saga)"], summary="Hoàn tiền bồi hoàn khi Saga thất bại")
def compensate(account_id: uuid.UUID, command: MoneyCommand):
    with SessionLocal.begin() as db:
        credit = db.scalar(select(LedgerEntry).where(LedgerEntry.payment_id == command.payment_id, LedgerEntry.entry_type == "COMPENSATING_CREDIT"))
        if credit:
            return db.get(Account, credit.account_id)
        debit_entry = db.scalar(select(LedgerEntry).where(LedgerEntry.payment_id == command.payment_id, LedgerEntry.entry_type == "DEBIT"))
        if not debit_entry or debit_entry.account_id != account_id or debit_entry.amount != command.amount:
            raise HTTPException(409, detail={"code": "DEBIT_NOT_FOUND", "message": "Không tìm thấy debit phù hợp để hoàn tiền."})
        db.execute(update(Account).where(Account.id == account_id).values(available_balance=Account.available_balance + command.amount, version=Account.version + 1))
        account = db.get(Account, account_id)
        db.add(LedgerEntry(account_id=account.id, payment_id=command.payment_id, entry_type="COMPENSATING_CREDIT", amount=command.amount, balance_after=account.available_balance, description=command.description))
        db.flush()
        return account


@app.get("/internal/v1/accounts/{account_id}/ledger/{payment_id}", response_model=LedgerState, dependencies=[Depends(require_internal)])
def ledger_state(account_id: uuid.UUID, payment_id: uuid.UUID):
    with SessionLocal() as db:
        entries = db.scalars(select(LedgerEntry).where(LedgerEntry.account_id == account_id, LedgerEntry.payment_id == payment_id)).all()
        debits = [entry for entry in entries if entry.entry_type == "DEBIT"]
        credits = [entry for entry in entries if entry.entry_type == "COMPENSATING_CREDIT"]
        return LedgerState(debit_count=len(debits), credit_count=len(credits), debit_amount=sum(x.amount for x in debits), credit_amount=sum(x.amount for x in credits))


logger = install_platform(app, "account")

