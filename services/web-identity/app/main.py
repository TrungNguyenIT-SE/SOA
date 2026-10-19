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


app = FastAPI(title="Web and Identity Service", version="1.0.0", lifespan=lifespan)
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


class Claims(UserOut):
    pass


def serialize_user(user: User) -> UserOut:
    return UserOut(id=user.id, username=user.username, full_name=user.full_name, email=user.email, phone=user.phone)


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


def current_user(authorization: Annotated[str | None, Header()] = None) -> Claims:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, detail={"code": "UNAUTHORIZED", "message": "Thiếu access token."})
    try:
        payload = jwt.decode(authorization[7:], JWT_SECRET, algorithms=["HS256"])
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


@app.get("/health")
def health():
    return {"status": "ok", "service": "web-identity"}


@app.get("/ready")
def ready():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ready", "service": "web-identity"}


@app.post("/api/v1/auth/login")
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


@app.get("/api/v1/users/me", response_model=UserOut)
def me(user: Annotated[Claims, Depends(current_user)]):
    return UserOut(**user.model_dump())


@app.get("/internal/v1/users/{user_id}", response_model=UserOut, dependencies=[Depends(require_internal)])
def internal_user(user_id: int):
    with SessionLocal() as db:
        user = db.get(User, user_id)
        if not user or user.status != "ACTIVE":
            raise HTTPException(404, detail={"code": "USER_NOT_FOUND", "message": "Không tìm thấy người dùng."})
        return serialize_user(user)


logger = install_platform(app, "web-identity")

