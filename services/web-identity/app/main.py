import json
import urllib.request
import hmac
import os
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated

import jwt
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from pwdlib import PasswordHash
from sqlalchemy import CheckConstraint, DateTime, String, create_engine, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from app.platform import install_platform

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://soa:soa_dev_password@postgres:5432/identity_db")
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


engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def seed() -> None:
    fixtures = [
        ("admin", "admin", "Password123@", "Quản Trị Viên (Admin)", "0900000000", "admin@ibanking.vn"),
        ("nguyenvana", "hoangthaidangkhoa", "Password123@", "Hoàng Thái Đăng Khoa", "0901000001", os.getenv("DEMO_EMAIL_1", "payer1@example.com")),
        ("tranthib", "dinhthanhphong", "Password123@", "Đinh Thanh Phong", "0901000002", os.getenv("DEMO_EMAIL_2", "payer2@example.com")),
        ("levanc", "nguyentrungnguyen", "Password123@", "Nguyễn Trung Nguyên", "0901000003", os.getenv("DEMO_EMAIL_3", "payer3@example.com")),
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


@asynccontextmanager
async def lifespan(_: FastAPI):
    seed()
    yield


app = FastAPI(
    title="Đại Học SOA - Cổng Quản Lý & API Đa Ngôn Ngữ",
    version="1.0.0",
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


def get_user_balance(user_id: int) -> int | None:
    try:
        req = urllib.request.Request(
            f"http://account:8000/internal/v1/accounts/by-user/{user_id}",
            headers={"X-Internal-Token": INTERNAL_API_TOKEN},
        )
        with urllib.request.urlopen(req, timeout=2.0) as res:
            return json.loads(res.read()).get("available_balance")
    except Exception:
        return None


def set_user_balance(user_id: int, balance: int) -> None:
    try:
        payload = json.dumps({"available_balance": balance}).encode()
        req = urllib.request.Request(
            f"http://account:8000/internal/v1/accounts/by-user/{user_id}/balance",
            data=payload,
            headers={"X-Internal-Token": INTERNAL_API_TOKEN, "Content-Type": "application/json"},
            method="PUT",
        )
        with urllib.request.urlopen(req, timeout=2.0) as res:
            pass
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


@app.get("/api/v1/users/me", response_model=UserOut, include_in_schema=False)
def me(user: Annotated[Claims, Depends(current_user)]):
    return UserOut(**user.model_dump())


@app.get("/internal/v1/users/{user_id}", response_model=UserOut, dependencies=[Depends(require_internal)], include_in_schema=False)

def internal_user(user_id: int):

    with SessionLocal() as db:

        user = db.get(User, user_id)

        if not user or user.status != "ACTIVE":

            raise HTTPException(404, detail={"code": "USER_NOT_FOUND", "message": "Không tìm thấy người dùng."})

        return serialize_user(user)





@app.get("/api/v1/users", response_model=list[UserOut], tags=["Người dùng (User)"], summary="Xem danh sách toàn bộ người dùng & số dư")

def list_users():

    """Xem toàn bộ danh sách người dùng"""

    with SessionLocal() as db:

        users = db.scalars(select(User).order_by(User.id)).all()

        return [serialize_user(u) for u in users]





@app.post("/api/v1/users", response_model=UserOut, status_code=201, tags=["Người dùng (User)"], summary="Tạo người dùng mới & cấp số dư ban đầu")
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


@app.get("/api/v1/users/{user_id}", response_model=UserOut, tags=["Người dùng (User)"], summary="Xem thông tin chi tiết một người dùng")
def get_user_by_id(user_id: int):
    """Xem thông tin chi tiết một người dùng theo ID"""
    with SessionLocal.begin() as db:
        user = db.get(User, user_id)
        if not user:
            raise HTTPException(404, detail={"code": "USER_NOT_FOUND", "message": "Không tìm thấy người dùng."})
        return serialize_user(user)


@app.put("/api/v1/users/{user_id}", response_model=UserOut, tags=["Người dùng (User)"], summary="Cập nhật thông tin & số dư người dùng")
def update_user(user_id: int, body: UserUpdate):
    """Cập nhật thông tin người dùng và số dư"""
    with SessionLocal.begin() as db:
        user = db.get(User, user_id)
        if not user:
            raise HTTPException(404, detail={"code": "USER_NOT_FOUND", "message": "Không tìm thấy người dùng."})
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


@app.delete("/api/v1/users/{user_id}", tags=["Người dùng (User)"], summary="Xóa người dùng khỏi hệ thống")

def delete_user(user_id: int):

    """Xóa người dùng"""

    with SessionLocal.begin() as db:

        user = db.get(User, user_id)

        if not user:

            raise HTTPException(404, detail={"code": "USER_NOT_FOUND", "message": "Không tìm thấy người dùng."})

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
        with urllib.request.urlopen(req, timeout=3.0) as resp:
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


@app.get("/api/v1/students", include_in_schema=False, response_model=list[StudentOut], tags=["Sinh viên (Student)"], summary="Xem danh sách toàn bộ sinh viên")
def list_students():
    """Xem danh sách toàn bộ sinh viên trong trường"""
    return forward_tuition_request("GET", "/api/v1/students")


@app.post("/api/v1/students", include_in_schema=False, response_model=StudentOut, status_code=201, tags=["Sinh viên (Student)"], summary="Tạo sinh viên mới & học phí")
def create_student(body: StudentCreate):
    """Tạo sinh viên mới kèm khoản học phí"""
    return forward_tuition_request("POST", "/api/v1/students", body.model_dump())


@app.get("/api/v1/students/{student_code}", include_in_schema=False, response_model=StudentOut, tags=["Sinh viên (Student)"], summary="Tra cứu thông tin sinh viên theo MSSV")
def get_student(student_code: str):
    """Tra cứu sinh viên theo MSSV"""
    return forward_tuition_request("GET", f"/api/v1/students/{student_code.strip().upper()}")


@app.put("/api/v1/students/{student_code}", include_in_schema=False, response_model=StudentOut, tags=["Sinh viên (Student)"], summary="Cập nhật thông tin sinh viên hoặc học phí")
def update_student(student_code: str, body: StudentUpdate):
    """Cập nhật thông tin sinh viên hoặc học phí"""
    return forward_tuition_request("PUT", f"/api/v1/students/{student_code.strip().upper()}", body.model_dump(exclude_unset=True))


@app.delete("/api/v1/students/{student_code}", include_in_schema=False, tags=["Sinh viên (Student)"], summary="Xóa sinh viên khỏi hệ thống")
def delete_student(student_code: str):
    """Xóa sinh viên khỏi hệ thống"""
    return forward_tuition_request("DELETE", f"/api/v1/students/{student_code.strip().upper()}")



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


@app.get("/api/v1/transactions", include_in_schema=False, response_model=list[TransactionOut], tags=["Lịch sử giao dịch (Transactions)"], summary="Xem danh sách toàn bộ lịch sử giao dịch")
def list_transactions():
    """Xem danh sách toàn bộ giao dịch thanh toán trong hệ thống"""
    return forward_payment_request("GET", "/api/v1/admin/transactions")


@app.post("/api/v1/transactions", include_in_schema=False, response_model=TransactionOut, status_code=201, tags=["Lịch sử giao dịch (Transactions)"], summary="Tạo bản ghi giao dịch mới")
def create_transaction(body: TransactionCreate):
    """Tạo bản ghi giao dịch mới"""
    return forward_payment_request("POST", "/api/v1/admin/transactions", body.model_dump())


@app.get("/api/v1/transactions/{transaction_id}", include_in_schema=False, response_model=TransactionOut, tags=["Lịch sử giao dịch (Transactions)"], summary="Tra cứu chi tiết một giao dịch")
def get_transaction(transaction_id: str):
    """Xem chi tiết một giao dịch theo Transaction ID"""
    return forward_payment_request("GET", f"/api/v1/admin/transactions/{transaction_id}")


@app.put("/api/v1/transactions/{transaction_id}", include_in_schema=False, response_model=TransactionOut, tags=["Lịch sử giao dịch (Transactions)"], summary="Cập nhật trạng thái hoặc thông tin giao dịch")
def update_transaction(transaction_id: str, body: TransactionUpdate):
    """Cập nhật trạng thái hoặc thông tin giao dịch"""
    return forward_payment_request("PUT", f"/api/v1/admin/transactions/{transaction_id}", body.model_dump(exclude_unset=True))


@app.delete("/api/v1/transactions/{transaction_id}", include_in_schema=False, tags=["Lịch sử giao dịch (Transactions)"], summary="Xóa giao dịch khỏi hệ thống")
def delete_transaction(transaction_id: str):
    """Xóa giao dịch khỏi lịch sử"""
    return forward_payment_request("DELETE", f"/api/v1/admin/transactions/{transaction_id}")


@app.get("/api/v1/admin/stats", include_in_schema=False, tags=["Quản trị (Admin)"], summary="Thống kê tổng quan số liệu Dashboard")
def admin_stats():
    """Lấy số liệu thống kê thời gian thực cho Admin Dashboard"""
    with SessionLocal() as db:
        total_users = db.scalar(select(text("count(*)")).select_from(User)) or 0
    try:
        students = forward_tuition_request("GET", "/api/v1/students")
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



