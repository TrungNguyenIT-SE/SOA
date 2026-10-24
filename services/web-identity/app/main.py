import hmac
import json
import os
import threading
import time
import urllib.request
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated

import jwt
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict, Field
from pwdlib import PasswordHash
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    create_engine,
    select,
    text,
    update,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

from app.platform import install_platform

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://soa:soa_dev_password@postgres:5432/identity_db")
ACCOUNT_DATABASE_URL = os.getenv("ACCOUNT_DATABASE_URL", "postgresql+psycopg://soa:soa_dev_password@postgres:5432/account_db")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-jwt-secret-change-me")
INTERNAL_API_TOKEN = os.getenv("INTERNAL_API_TOKEN", "dev-only-internal-token")
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "30"))
BASE_DIR = Path(__file__).resolve().parent.parent
password_hash = PasswordHash.recommended()
login_attempts: dict[str, list[float]] = {}
login_attempts_lock = threading.Lock()


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("status IN ('ACTIVE', 'LOCKED', 'DISABLED')", name="ck_user_status"),)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(160))
    phone: Mapped[str] = mapped_column(String(20))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


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

account_engine = create_engine(ACCOUNT_DATABASE_URL, pool_pre_ping=True)
AccountSessionLocal = sessionmaker(account_engine, expire_on_commit=False)


def seed() -> None:
    fixtures = [
        ("nguyenvana", "hoangthaidangkhoa", "Password123@", "Hoàng Thái Đăng Khoa", "0901000001", os.getenv("DEMO_EMAIL_1", "dangkhoa040706@gmail.com")),
        ("tranthib", "dinhthanhphong", "Password123@", "Đinh Thanh Phong", "0901000002", os.getenv("DEMO_EMAIL_2", "thanhphong090406@gmail.com")),
        ("levanc", "nguyentrungnguyen", "Password123@", "Nguyễn Trung Nguyên", "0901000003", os.getenv("DEMO_EMAIL_3", "trnguynnn@gmail.com")),
        ("admin", "admin", "Password123@", "Quản Trị Viên (Admin)", "0900000000", "admin@ibanking.vn"),
    ]
    with SessionLocal.begin() as db:
        for legacy_username, username, password, full_name, phone, email in fixtures:
            existing = db.scalar(select(User).where(User.username == username))
            if not existing:
                existing = db.scalar(select(User).where(User.username == legacy_username))
            if existing:
                existing.username = username
                existing.password_hash = password_hash.hash(password)
                existing.full_name = full_name
                existing.phone = phone
                existing.email = email
                existing.status = "ACTIVE"
            else:
                db.add(User(username=username, password_hash=password_hash.hash(password), full_name=full_name, phone=phone, email=email))

    with AccountSessionLocal.begin() as acc_db:
        if not acc_db.scalar(select(Account.id).limit(1)):
            acc_db.add_all(
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


openapi_tags = [
    {
        "name": "Xác thực (Auth)",
        "description": "Dịch vụ Xác thực và Phân quyền người dùng (Khoa). Đăng nhập và cấp phát Access Token / Refresh Token bảo mật theo chuẩn JWT.",
    },
    {
        "name": "Người dùng cá nhân (User)",
        "description": "Dịch vụ Tra cứu thông tin hồ sơ tài khoản cá nhân của người nộp đang đăng nhập (Khoa).",
    },
    {
        "name": "Quản trị - Người dùng (Admin)",
        "description": "Quản trị Toàn bộ Danh sách Người dùng và Cấp số dư khởi tạo trong hệ thống (Khoa).",
    },
    {
        "name": "Người dùng - Tài khoản & Số dư (User)",
        "description": "Dịch vụ Tra cứu Số dư khả dụng và Lịch sử biến động số dư sổ cái (Ledger) của tài khoản (Khoa).",
    },
    {
        "name": "Quản trị - Tài khoản & Số dư (Admin)",
        "description": "Quản trị Danh sách Tài khoản Ngân hàng và Thực hiện Nạp tiền (Deposit) vào ví người dùng (Khoa).",
    },
    {
        "name": "Nội bộ (Saga)",
        "description": "Các API giao tiếp nội bộ phục vụ trừ tiền và hoàn tiền bồi hoàn SAGA giữa các microservices (Khoa).",
    },
]

app = FastAPI(
    title="Quản lý Người dùng & Tài khoản (Khoa)",
    description="Microservice hợp nhất phụ trách Quản lý Người dùng, Đăng nhập Xác thực JWT, Tài khoản Ngân hàng và Sổ cái Số dư (Python 3.12 - FastAPI).",
    version="1.0.0",
    openapi_tags=openapi_tags,
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    email: str
    phone: str
    balance: int | None = None


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=6, max_length=200)
    full_name: str = Field(min_length=1, max_length=160)
    phone: str = Field(min_length=8, max_length=20)
    email: str = Field(min_length=5, max_length=254)
    balance: int | None = 10_000_000


class UserUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    email: str | None = None
    status: str | None = "ACTIVE"
    balance: int | None = None


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


def get_user_balance(user_id: int) -> int | None:
    try:
        with AccountSessionLocal() as db:
            account = get_account_for_user(db, user_id)
            return account.available_balance if account else None
    except Exception:
        return None


def set_user_balance(user_id: int, balance: int) -> None:
    try:
        with AccountSessionLocal.begin() as db:
            account = get_account_for_user(db, user_id)
            if account:
                account.available_balance = balance
                account.version += 1
    except Exception:
        pass


def serialize_user(user: User, balance: int | None = None) -> UserOut:
    if balance is None:
        balance = get_user_balance(user.id)
    return UserOut(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        email=user.email,
        phone=user.phone,
        balance=balance,
    )


class Claims(UserOut):
    pass


def issue_token(user: User, token_type: str, lifetime: timedelta) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "user_id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone,
            "type": token_type,
            "iat": now,
            "exp": now + lifetime,
        },
        JWT_SECRET,
        algorithm="HS256",
    )


bearer_scheme = HTTPBearer(auto_error=False)


def current_user(
    cred: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> Claims:
    raw_token = cred.credentials if (cred and cred.credentials) else None
    if not raw_token and authorization and authorization.startswith("Bearer "):
        raw_token = authorization[7:].strip()
    if not raw_token:
        raise HTTPException(401, detail={"code": "UNAUTHORIZED", "message": "Thiếu access token."})
    try:
        payload = jwt.decode(raw_token, JWT_SECRET, algorithms=["HS256"])
        if payload.get("type") != "access":
            raise jwt.InvalidTokenError("wrong token type")
        return Claims(
            id=int(payload["user_id"]),
            username=payload["username"],
            full_name=payload["full_name"],
            email=payload["email"],
            phone=payload["phone"],
        )
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise HTTPException(401, detail={"code": "INVALID_TOKEN", "message": "Access token không hợp lệ hoặc đã hết hạn."}) from exc


def require_internal(x_internal_token: Annotated[str | None, Header()] = None) -> None:
    if not x_internal_token or not hmac.compare_digest(x_internal_token, INTERNAL_API_TOKEN):
        raise HTTPException(403, detail={"code": "FORBIDDEN", "message": "Internal token không hợp lệ."})


def require_admin(user: Annotated[Claims, Depends(current_user)]) -> Claims:
    """Chỉ cho phép tài khoản admin (username == 'admin') truy cập."""
    if user.username != "admin":
        raise HTTPException(403, detail={"code": "FORBIDDEN", "message": "Bạn không có quyền truy cập tính năng quản trị."})
    return user


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, dict) else {"code": "HTTP_ERROR", "message": str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content={**detail, "path": request.url.path})


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/health", include_in_schema=False, summary="Kiểm tra trạng thái Service")
def health():
    return {"status": "ok", "service": "web-identity"}


@app.get("/ready", include_in_schema=False, summary="Kiểm tra kết nối Database PostgreSQL")
def ready():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ready", "service": "web-identity"}


@app.post("/api/v1/auth/login", tags=["Xác thực (Auth)"], summary="Đăng nhập tài khoản & Cấp JWT Token")
def login(body: LoginIn, request: Request):
    client_key = request.client.host if request.client else "unknown"
    now = time.monotonic()
    with login_attempts_lock:
        recent = [stamp for stamp in login_attempts.get(client_key, []) if now - stamp < 60]
        if len(recent) >= 10:
            raise HTTPException(429, detail={"code": "LOGIN_RATE_LIMITED", "message": "Quá nhiều lần đăng nhập. Vui lòng thử lại sau một phút."})
        recent.append(now)
        login_attempts[client_key] = recent
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == body.username.strip()))
        if not user or user.status != "ACTIVE" or not password_hash.verify(body.password, user.password_hash):
            raise HTTPException(401, detail={"code": "INVALID_CREDENTIALS", "message": "Tên đăng nhập hoặc mật khẩu không đúng."})
        with login_attempts_lock:
            login_attempts.pop(client_key, None)
        return {
            "access": issue_token(user, "access", timedelta(minutes=ACCESS_TOKEN_MINUTES)),
            "refresh": issue_token(user, "refresh", timedelta(days=1)),
            "user": serialize_user(user),
        }


@app.get(
    "/api/v1/users/me",
    response_model=UserOut,
    include_in_schema=True,
    tags=["Người dùng cá nhân (User)"],
    summary="Xem thông tin tài khoản cá nhân đang đăng nhập",
)
def me(user: Annotated[Claims, Depends(current_user)]):
    return UserOut(**user.model_dump())


@app.get("/internal/v1/users/{user_id}", response_model=UserOut, dependencies=[Depends(require_internal)], include_in_schema=False)
def internal_user(user_id: int):
    with SessionLocal() as db:
        user = db.get(User, user_id)
        if not user or user.status != "ACTIVE":
            raise HTTPException(404, detail={"code": "USER_NOT_FOUND", "message": "Không tìm thấy người dùng."})
        return serialize_user(user)


@app.get("/internal/v1/users/by-email/{email:path}", response_model=UserOut, dependencies=[Depends(require_internal)], include_in_schema=False)
def internal_user_by_email(email: str):
    clean_email = email.strip().lower()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == clean_email))
        if not user:
            user = db.scalar(select(User).where(User.email == email.strip()))
        if not user or user.status != "ACTIVE":
            raise HTTPException(404, detail={"code": "USER_NOT_FOUND", "message": "Không tìm thấy người dùng theo email."})
        return serialize_user(user)





@app.get(
    "/api/v1/admin/users",
    response_model=list[UserOut],
    tags=["Quản trị - Người dùng (Admin)"],
    summary="Xem danh sách toàn bộ người dùng & số dư",
    dependencies=[Depends(require_admin)],
)
@app.get("/api/v1/users", response_model=list[UserOut], include_in_schema=False, dependencies=[Depends(require_admin)])
def list_users():
    """Xem toàn bộ danh sách người dùng"""
    with SessionLocal() as db:
        users = db.scalars(select(User).order_by(User.id)).all()
        return [serialize_user(u) for u in users]


@app.post(
    "/api/v1/admin/users",
    response_model=UserOut,
    status_code=201,
    tags=["Quản trị - Người dùng (Admin)"],
    summary="Tạo người dùng mới & cấp số dư ban đầu",
    dependencies=[Depends(require_admin)],
)
@app.post("/api/v1/users", response_model=UserOut, status_code=201, include_in_schema=False, dependencies=[Depends(require_admin)])
def create_user(body: UserCreate):
    """Tạo người dùng mới kèm số dư"""
    with SessionLocal.begin() as db:
        existing = db.scalar(select(User).where((User.username == body.username.strip()) | (User.email == body.email.strip())))
        if existing:
            raise HTTPException(409, detail={"code": "USER_EXISTS", "message": "Tên đăng nhập hoặc email đã tồn tại."})
        user = User(
            username=body.username.strip(),
            password_hash=password_hash.hash(body.password),
            full_name=body.full_name.strip(),
            phone=body.phone.strip(),
            email=body.email.strip(),
            status="ACTIVE",
        )
        db.add(user)
        db.flush()
        user_id = user.id

    if body.balance is not None:
        set_user_balance(user_id, body.balance)

    return serialize_user(user, balance=body.balance)


@app.get(
    "/api/v1/admin/users/{user_id}",
    response_model=UserOut,
    tags=["Quản trị - Người dùng (Admin)"],
    summary="Xem thông tin chi tiết một người dùng",
    dependencies=[Depends(require_admin)],
)
@app.get("/api/v1/users/{user_id}", response_model=UserOut, include_in_schema=False, dependencies=[Depends(require_admin)])
def get_user_by_id(user_id: int):
    """Xem thông tin chi tiết một người dùng theo ID"""
    with SessionLocal.begin() as db:
        user = db.get(User, user_id)
        if not user:
            raise HTTPException(404, detail={"code": "USER_NOT_FOUND", "message": "Không tìm thấy người dùng."})
        return serialize_user(user)


@app.put(
    "/api/v1/admin/users/{user_id}",
    response_model=UserOut,
    tags=["Quản trị - Người dùng (Admin)"],
    summary="Cập nhật thông tin & số dư người dùng",
    dependencies=[Depends(require_admin)],
)
@app.put("/api/v1/users/{user_id}", response_model=UserOut, include_in_schema=False, dependencies=[Depends(require_admin)])
def update_user(user_id: int, body: UserUpdate):
    """Cập nhật thông tin người dùng và số dư"""
    with SessionLocal.begin() as db:
        user = db.get(User, user_id)
        if not user:
            raise HTTPException(404, detail={"code": "USER_NOT_FOUND", "message": "Không tìm thấy người dùng."})
        if user.username == "admin" and body.status and body.status != "ACTIVE":
            raise HTTPException(400, detail={"code": "CANNOT_LOCK_ADMIN", "message": "Không thể khóa hoặc vô hiệu hóa tài khoản Quản trị viên (admin)."})
        if body.full_name is not None:
            user.full_name = body.full_name.strip()
        if body.phone is not None:
            user.phone = body.phone.strip()
        if body.email is not None:
            user.email = body.email.strip()
        if body.status is not None:
            user.status = body.status
        db.flush()

    if body.balance is not None:
        set_user_balance(user_id, body.balance)

    return serialize_user(user, balance=body.balance)


@app.delete(
    "/api/v1/admin/users/{user_id}",
    tags=["Quản trị - Người dùng (Admin)"],
    summary="Xóa người dùng khỏi hệ thống",
    dependencies=[Depends(require_admin)],
)
@app.delete("/api/v1/users/{user_id}", include_in_schema=False, dependencies=[Depends(require_admin)])
def delete_user(user_id: int):
    """Xóa người dùng"""
    with SessionLocal.begin() as db:
        user = db.get(User, user_id)
        if not user:
            raise HTTPException(404, detail={"code": "USER_NOT_FOUND", "message": "Không tìm thấy người dùng."})
        if user.username == "admin":
            raise HTTPException(400, detail={"code": "CANNOT_DELETE_ADMIN", "message": "Không thể xóa tài khoản Quản trị viên (admin)."})
        db.delete(user)
        return {"status": "success", "message": f"Đã xóa người dùng {user_id}."}





class StudentOut(BaseModel):
    id: str | None = None
    student_code: str
    student_name: str
    term: str | None = None
    amount: int | None = None
    status: str | None = None


class StudentCreate(BaseModel):
    student_code: str = Field(min_length=3, max_length=20, examples=["52400099"])
    student_name: str = Field(min_length=1, max_length=160, examples=["Nguyễn Văn Mới"])
    term: str = Field(default="HK1/2026-2027", examples=["HK1/2026-2027"])
    amount: int = Field(default=1_000_000, examples=[1000000])
    status: str = Field(default="UNPAID", examples=["UNPAID", "PAID"])


class StudentUpdate(BaseModel):
    full_name: str | None = Field(default=None, examples=["Nguyễn Văn Mới Đổi Tên"])
    term: str | None = Field(default=None, examples=["HK1/2026-2027"])
    amount: int | None = Field(default=None, examples=[1500000])
    status: str | None = Field(default=None, examples=["PAID", "UNPAID"])
    payer_user_id: int | None = Field(default=None, examples=[2])


def forward_tuition_request(method: str, path: str, data: dict | None = None):
    url = f"http://tuition:8000{path}"
    payload = json.dumps(data).encode("utf-8") if data is not None else None
    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(url, data=payload, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=4.0) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        try:
            parsed = json.loads(error_body)
            detail = parsed.get("detail", error_body)
            if isinstance(detail, dict) and "message" in detail:
                detail = detail["message"]
            elif isinstance(parsed, dict) and "message" in parsed:
                detail = parsed["message"]
        except Exception:
            detail = error_body
        raise HTTPException(status_code=e.code, detail=detail)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Không thể kết nối đến Tuition Service: {str(e)}")


@app.get(
    "/api/v1/admin/students",
    response_model=list[StudentOut],
    include_in_schema=False,
    tags=["Quản trị - Sinh viên & Học phí (Admin)"],
    summary="Xem danh sách toàn bộ sinh viên trong trường",
    dependencies=[Depends(require_admin)],
)
@app.get("/api/v1/students", response_model=list[StudentOut], include_in_schema=False, dependencies=[Depends(require_admin)])
def list_students():
    """Xem danh sách toàn bộ sinh viên trong trường"""
    return forward_tuition_request("GET", "/api/v1/admin/students")


@app.post(
    "/api/v1/admin/students",
    response_model=StudentOut,
    status_code=201,
    include_in_schema=False,
    tags=["Quản trị - Sinh viên & Học phí (Admin)"],
    summary="Thêm hồ sơ sinh viên mới & khởi tạo học phí",
    dependencies=[Depends(require_admin)],
)
@app.post("/api/v1/students", response_model=StudentOut, status_code=201, include_in_schema=False, dependencies=[Depends(require_admin)])
def create_student(body: StudentCreate):
    """Tạo sinh viên mới kèm khoản học phí"""
    return forward_tuition_request("POST", "/api/v1/admin/students", body.model_dump())


@app.get(
    "/api/v1/students/{student_code}",
    response_model=StudentOut,
    include_in_schema=False,
    tags=["Người dùng - Tra cứu học phí (User)"],
    summary="Tra cứu thông tin sinh viên & học phí theo MSSV",
)
@app.get(
    "/api/v1/admin/students/{student_code}",
    response_model=StudentOut,
    include_in_schema=False,
    tags=["Quản trị - Sinh viên & Học phí (Admin)"],
    summary="Xem thông tin chi tiết hồ sơ sinh viên theo MSSV",
    dependencies=[Depends(require_admin)],
)
def get_student(student_code: str):
    """Tra cứu sinh viên theo MSSV"""
    return forward_tuition_request("GET", f"/api/v1/students/{student_code.strip().upper()}")


@app.put(
    "/api/v1/admin/students/{student_code}",
    response_model=StudentOut,
    include_in_schema=False,
    tags=["Quản trị - Sinh viên & Học phí (Admin)"],
    summary="Cập nhật hồ sơ sinh viên hoặc thực hiện thanh toán học phí",
)
@app.put(
    "/api/v1/students/{student_code}",
    response_model=StudentOut,
    include_in_schema=False,
)
def update_student(
    student_code: str,
    body: StudentUpdate,
    user: Annotated[Claims, Depends(current_user)],
):
    """
    Cập nhật thông tin sinh viên hoặc thanh toán học phí:
    - Admin: Toàn quyền chỉnh sửa thông tin sinh viên và học phí.
    - User bình thường: Được phép thực hiện thanh toán học phí của sinh viên (status='PAID'),
      hệ thống tự động liên kết payer_user_id với tài khoản của chính user đang đăng nhập.
    """
    data = body.model_dump(exclude_unset=True)
    if user.username != "admin":
        if body.status != "PAID":
            raise HTTPException(403, detail={"code": "FORBIDDEN", "message": "Bạn không có quyền truy cập tính năng quản trị."})
        data = {
            "status": "PAID",
            "payer_user_id": user.id,
        }
    return forward_tuition_request("PUT", f"/api/v1/admin/students/{student_code.strip().upper()}", data)


@app.delete(
    "/api/v1/admin/students/{student_code}",
    include_in_schema=False,
    tags=["Quản trị - Sinh viên & Học phí (Admin)"],
    summary="Xóa sinh viên và học phí khỏi hệ thống",
    dependencies=[Depends(require_admin)],
)
@app.delete("/api/v1/students/{student_code}", include_in_schema=False, dependencies=[Depends(require_admin)])
def delete_student(student_code: str):
    """Xóa sinh viên khỏi hệ thống"""
    return forward_tuition_request("DELETE", f"/api/v1/admin/students/{student_code.strip().upper()}")


class TransactionOut(BaseModel):
    id: str
    payer_user_id: int | None = None
    payer_name: str
    payer_email: str
    student_code: str
    student_name: str
    term: str
    amount: int
    status: str
    failure_code: str | None = None
    created_at: str | datetime
    completed_at: str | datetime | None = None


class TransactionCreate(BaseModel):
    payer_user_id: int | None = Field(default=None, examples=[2])
    payer_name: str = Field(min_length=1, max_length=160, examples=["Hoàng Thái Đăng Khoa"])
    payer_email: str = Field(min_length=5, max_length=254, examples=["dangkhoa040706@gmail.com"])
    student_code: str = Field(min_length=3, max_length=20, examples=["52400001"])
    student_name: str = Field(min_length=1, max_length=160, examples=["Nguyễn Minh Anh"])
    term: str = Field(default="HK1/2026-2027", examples=["HK1/2026-2027"])
    amount: int = Field(gt=0, examples=[1200000])
    status: str = Field(default="SUCCEEDED", examples=["SUCCEEDED"])


class TransactionUpdate(BaseModel):
    status: str | None = Field(default=None, examples=["SUCCEEDED"])
    amount: int | None = Field(default=None, examples=[1500000])
    student_name: str | None = Field(default=None, examples=["Nguyễn Minh Anh"])
    term: str | None = Field(default=None, examples=["HK1/2026-2027"])
    failure_code: str | None = Field(default=None, examples=["NONE"])


def forward_payment_request(method: str, path: str, data: dict | None = None):
    url = f"http://payment:8000{path}"
    payload = json.dumps(data).encode("utf-8") if data is not None else None
    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(url, data=payload, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=4.0) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        try:
            parsed = json.loads(error_body)
            detail = parsed.get("detail", error_body)
            if isinstance(detail, dict) and "message" in detail:
                detail = detail["message"]
            elif isinstance(parsed, dict) and "message" in parsed:
                detail = parsed["message"]
        except Exception:
            detail = error_body
        raise HTTPException(status_code=e.code, detail=detail)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Không thể kết nối đến Payment Service: {str(e)}")


@app.get(
    "/api/v1/admin/transactions",
    response_model=list[TransactionOut],
    include_in_schema=False,
    tags=["Quản trị - Lịch sử giao dịch (Admin)"],
    summary="Xem danh sách toàn bộ giao dịch thanh toán trong hệ thống",
    dependencies=[Depends(require_admin)],
)
@app.get("/api/v1/transactions", response_model=list[TransactionOut], include_in_schema=False, dependencies=[Depends(require_admin)])
def list_transactions():
    """Xem danh sách toàn bộ giao dịch thanh toán trong hệ thống"""
    return forward_payment_request("GET", "/api/v1/admin/transactions")


@app.post(
    "/api/v1/admin/transactions",
    response_model=TransactionOut,
    status_code=201,
    include_in_schema=False,
    tags=["Quản trị - Lịch sử giao dịch (Admin)"],
    summary="Tạo bản ghi giao dịch mới",
    dependencies=[Depends(require_admin)],
)
@app.post("/api/v1/transactions", response_model=TransactionOut, status_code=201, include_in_schema=False, dependencies=[Depends(require_admin)])
def create_transaction(body: TransactionCreate):
    """Tạo bản ghi giao dịch mới"""
    return forward_payment_request("POST", "/api/v1/transactions", body.model_dump())


@app.get(
    "/api/v1/admin/transactions/{transaction_id}",
    response_model=TransactionOut,
    include_in_schema=False,
    tags=["Quản trị - Lịch sử giao dịch (Admin)"],
    summary="Tra cứu chi tiết một giao dịch theo Transaction ID",
    dependencies=[Depends(require_admin)],
)
@app.get("/api/v1/transactions/{transaction_id}", response_model=TransactionOut, include_in_schema=False, dependencies=[Depends(require_admin)])
def get_transaction(transaction_id: str):
    """Xem chi tiết một giao dịch theo Transaction ID"""
    return forward_payment_request("GET", f"/api/v1/admin/transactions/{transaction_id}")


@app.put(
    "/api/v1/admin/transactions/{transaction_id}",
    response_model=TransactionOut,
    include_in_schema=False,
    tags=["Quản trị - Lịch sử giao dịch (Admin)"],
    summary="Cập nhật trạng thái hoặc thông tin giao dịch",
    dependencies=[Depends(require_admin)],
)
@app.put("/api/v1/transactions/{transaction_id}", response_model=TransactionOut, include_in_schema=False, dependencies=[Depends(require_admin)])
def update_transaction(transaction_id: str, body: TransactionUpdate):
    """Cập nhật trạng thái hoặc thông tin giao dịch"""
    return forward_payment_request("PUT", f"/api/v1/admin/transactions/{transaction_id}", body.model_dump(exclude_unset=True))


@app.delete(
    "/api/v1/admin/transactions/{transaction_id}",
    include_in_schema=False,
    tags=["Quản trị - Lịch sử giao dịch (Admin)"],
    summary="Xóa giao dịch khỏi hệ thống",
    dependencies=[Depends(require_admin)],
)
@app.delete("/api/v1/transactions/{transaction_id}", include_in_schema=False, dependencies=[Depends(require_admin)])
def delete_transaction(transaction_id: str):
    """Xóa giao dịch khỏi lịch sử"""
    return forward_payment_request("DELETE", f"/api/v1/admin/transactions/{transaction_id}")


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID | str
    user_id: int
    account_number: str
    currency: str = "VND"
    available_balance: int


class LedgerOut(BaseModel):
    id: uuid.UUID | str
    payment_id: uuid.UUID | str
    type: str
    amount: int
    balance_after: int
    created_at: datetime | str


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


class DepositCommand(BaseModel):
    account_number: str = Field(min_length=5, examples=["970400000001"])
    amount: int = Field(gt=0, examples=[2000000])


class BalanceUpdate(BaseModel):
    available_balance: int = Field(ge=0)


@app.get(
    "/api/v1/accounts/me",
    response_model=AccountOut,
    tags=["Người dùng - Tài khoản & Số dư (User)"],
    summary="Xem số dư khả dụng tài khoản đăng nhập",
)
def my_account(user: Annotated[Claims, Depends(current_user)]):
    with AccountSessionLocal() as db:
        return get_account_for_user(db, user.id)


@app.get(
    "/api/v1/accounts/me/transactions",
    response_model=PageOut,
    tags=["Người dùng - Tài khoản & Số dư (User)"],
    summary="Xem lịch sử giao dịch biến động số dư (Ledger)",
)
def my_transactions(
    user: Annotated[Claims, Depends(current_user)],
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    with AccountSessionLocal() as db:
        account = get_account_for_user(db, user.id)
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
                    id=str(item.id),
                    payment_id=str(item.payment_id),
                    type=item.entry_type,
                    amount=item.amount,
                    balance_after=item.balance_after,
                    created_at=item.created_at.isoformat() if hasattr(item.created_at, "isoformat") else str(item.created_at),
                )
                for item in entries
            ],
            page=page,
            size=size,
        )


@app.get(
    "/api/v1/admin/accounts",
    response_model=list[AccountOut],
    tags=["Quản trị - Tài khoản & Số dư (Admin)"],
    summary="Xem danh sách toàn bộ tài khoản ngân hàng",
    dependencies=[Depends(require_admin)],
)
@app.get("/api/v1/accounts", response_model=list[AccountOut], include_in_schema=False, dependencies=[Depends(require_admin)])
def list_accounts():
    """Xem danh sách toàn bộ tài khoản ngân hàng"""
    with AccountSessionLocal() as db:
        accounts = db.scalars(select(Account).order_by(Account.id)).all()
        return [AccountOut.model_validate(acc) for acc in accounts]


@app.post(
    "/api/v1/admin/accounts/deposit",
    response_model=AccountOut,
    tags=["Quản trị - Tài khoản & Số dư (Admin)"],
    summary="Nạp thêm tiền vào tài khoản ngân hàng",
    dependencies=[Depends(require_admin)],
)
@app.post("/api/v1/accounts/deposit", response_model=AccountOut, include_in_schema=False, dependencies=[Depends(require_admin)])
def deposit(command: DepositCommand):
    """Nạp thêm tiền vào tài khoản"""
    with AccountSessionLocal.begin() as db:
        account = db.scalar(select(Account).where(Account.account_number == command.account_number.strip()))
        if not account:
            raise HTTPException(404, detail={"code": "ACCOUNT_NOT_FOUND", "message": "Không tìm thấy số tài khoản."})
        account.available_balance += command.amount
        account.version += 1
        db.flush()
        return AccountOut.model_validate(account)


@app.get("/internal/v1/accounts/by-user/{user_id}", response_model=AccountOut, dependencies=[Depends(require_internal)], include_in_schema=False)
def account_by_user(user_id: int):
    with AccountSessionLocal() as db:
        return get_account_for_user(db, user_id)


@app.put("/internal/v1/accounts/by-user/{user_id}/balance", response_model=AccountOut, dependencies=[Depends(require_internal)], include_in_schema=False)
def update_balance_by_user(user_id: int, body: BalanceUpdate):
    with AccountSessionLocal.begin() as db:
        account = get_account_for_user(db, user_id)
        account.available_balance = body.available_balance
        account.version += 1
        db.flush()
        return AccountOut.model_validate(account)


@app.post("/internal/v1/accounts/{account_id}/debits", response_model=AccountOut, dependencies=[Depends(require_internal)], tags=["Nội bộ (Saga)"], summary="Trừ tiền tài khoản nguyên tử có kiểm tra số dư")
def debit(account_id: uuid.UUID, command: MoneyCommand):
    try:
        with AccountSessionLocal.begin() as db:
            existing = db.scalar(
                select(LedgerEntry).where(
                    LedgerEntry.payment_id == command.payment_id,
                    LedgerEntry.entry_type == "DEBIT",
                )
            )
            if existing:
                return AccountOut.model_validate(db.get(Account, existing.account_id))

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
            return AccountOut.model_validate(account)
    except IntegrityError:
        with AccountSessionLocal() as db:
            existing = db.scalar(select(LedgerEntry).where(LedgerEntry.payment_id == command.payment_id, LedgerEntry.entry_type == "DEBIT"))
            if existing:
                return AccountOut.model_validate(db.get(Account, existing.account_id))
        raise


@app.post("/internal/v1/accounts/{account_id}/compensating-credits", response_model=AccountOut, dependencies=[Depends(require_internal)], tags=["Nội bộ (Saga)"], summary="Hoàn tiền bồi hoàn khi Saga thất bại")
def compensate(account_id: uuid.UUID, command: MoneyCommand):
    with AccountSessionLocal.begin() as db:
        credit = db.scalar(select(LedgerEntry).where(LedgerEntry.payment_id == command.payment_id, LedgerEntry.entry_type == "COMPENSATING_CREDIT"))
        if credit:
            return AccountOut.model_validate(db.get(Account, credit.account_id))
        debit_entry = db.scalar(select(LedgerEntry).where(LedgerEntry.payment_id == command.payment_id, LedgerEntry.entry_type == "DEBIT"))
        if not debit_entry or debit_entry.account_id != account_id or debit_entry.amount != command.amount:
            raise HTTPException(409, detail={"code": "DEBIT_NOT_FOUND", "message": "Không tìm thấy debit phù hợp để hoàn tiền."})
        db.execute(update(Account).where(Account.id == account_id).values(available_balance=Account.available_balance + command.amount, version=Account.version + 1))
        account = db.get(Account, account_id)
        db.add(LedgerEntry(account_id=account.id, payment_id=command.payment_id, entry_type="COMPENSATING_CREDIT", amount=command.amount, balance_after=account.available_balance, description=command.description))
        db.flush()
        return AccountOut.model_validate(account)


@app.get("/internal/v1/accounts/{account_id}/ledger/{payment_id}", response_model=LedgerState, dependencies=[Depends(require_internal)], tags=["Nội bộ (Saga)"], summary="Xem trạng thái sổ cái SAGA của giao dịch")
def ledger_state(account_id: uuid.UUID, payment_id: uuid.UUID):
    with AccountSessionLocal() as db:
        entries = db.scalars(select(LedgerEntry).where(LedgerEntry.account_id == account_id, LedgerEntry.payment_id == payment_id)).all()
        debits = [entry for entry in entries if entry.entry_type == "DEBIT"]
        credits = [entry for entry in entries if entry.entry_type == "COMPENSATING_CREDIT"]
        return LedgerState(debit_count=len(debits), credit_count=len(credits), debit_amount=sum(x.amount for x in debits), credit_amount=sum(x.amount for x in credits))


class OtpGenerateIn(BaseModel):
    student_code: str = Field(min_length=3, examples=["52400001"])
    email: str = Field(min_length=5, examples=["dangkhoa040706@gmail.com"])
    amount: int = Field(gt=0, examples=[1200000])


class OtpVerifyIn(BaseModel):
    student_code: str = Field(min_length=3, examples=["52400001"])
    otp: str = Field(min_length=6, max_length=6, examples=["123456"])
    email: str | None = Field(default=None, examples=["dangkhoa040706@gmail.com"])


@app.get(
    "/api/v1/tuition-invoices/by-student/{student_code}",
    response_model=StudentOut,
    include_in_schema=False,
    tags=["Người dùng - Tra cứu học phí (User)"],
    summary="Tra cứu hóa đơn học phí theo MSSV",
)
def get_tuition_invoice_proxy(student_code: str):
    """Tra cứu hóa đơn học phí theo MSSV"""
    return forward_tuition_request("GET", f"/api/v1/tuition-invoices/by-student/{student_code.strip().upper()}")


@app.post(
    "/api/v1/otp/generate",
    include_in_schema=False,
    tags=["Xác thực OTP Học phí (OTP)"],
    summary="Tạo và gửi mã OTP xác thực thanh toán học phí qua Email",
)
def generate_otp_proxy(body: OtpGenerateIn):
    """Tạo mã OTP và gửi qua Email xác thực thanh toán học phí"""
    return forward_tuition_request("POST", "/api/v1/otp/generate", body.model_dump())


@app.post(
    "/api/v1/otp/verify",
    include_in_schema=False,
    tags=["Xác thực OTP Học phí (OTP)"],
    summary="Xác thực OTP và tự động hoàn tất thanh toán học phí",
)
def verify_otp_proxy(body: OtpVerifyIn):
    """Xác thực OTP và tự động thanh toán học phí"""
    return forward_tuition_request("POST", "/api/v1/otp/verify", body.model_dump())



@app.get("/api/v1/admin/stats", include_in_schema=True, tags=["Quản trị - Người dùng (Admin)"], summary="Thống kê tổng quan số liệu Dashboard", dependencies=[Depends(require_admin)])
def admin_stats():
    """Lấy số liệu thống kê thời gian thực cho Admin Dashboard"""
    with SessionLocal() as db:
        total_users = db.scalar(select(text("count(*)")).select_from(User)) or 0
    try:
        students = forward_tuition_request("GET", "/api/v1/admin/students")
        total_students = len(students) if isinstance(students, list) else 0
    except Exception:
        total_students = 0
    try:
        txs = forward_payment_request("GET", "/api/v1/admin/transactions")
        total_transactions = len(txs) if isinstance(txs, list) else 0
        total_revenue = sum(item.get("amount", 0) for item in txs if item.get("status") == "SUCCEEDED")
    except Exception:
        total_transactions = 0
        total_revenue = 0

    return {
        "total_users": total_users,
        "total_students": total_students,
        "total_transactions": total_transactions,
        "total_revenue": total_revenue,
    }


@app.get("/api-docs/tuition", include_in_schema=False)
def get_tuition_openapi():
    try:
        req = urllib.request.Request("http://tuition:8000/v3/api-docs")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            data["servers"] = [
                {"url": "http://localhost:8003", "description": "Cổng riêng Java (Nguyên)"},
                {"url": "http://localhost:8080", "description": "Cổng Gateway SOA"},
            ]
            return data
    except Exception:
        return {
            "openapi": "3.0.1",
            "info": {"title": "Nguyên - Java Tuition & OTP Service (Đang kết nối)", "version": "1.0.0"},
            "paths": {},
        }


@app.get("/api-docs/payment", include_in_schema=False)
def get_payment_openapi():
    try:
        req = urllib.request.Request("http://payment:8000/swagger/v1/swagger.json")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            data["servers"] = [
                {"url": "http://localhost:8004", "description": "Cổng riêng C# (Phong)"},
                {"url": "http://localhost:8080", "description": "Cổng Gateway SOA"},
            ]
            return data
    except Exception:
        return {
            "openapi": "3.0.1",
            "info": {"title": "Phong - C# Payment Service (Đang kết nối)", "version": "1.0.0"},
            "paths": {},
        }


logger = install_platform(app, "web-identity")



