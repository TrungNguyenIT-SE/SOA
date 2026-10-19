import json
import logging
import os
import smtplib
import ssl
import time
import uuid
from datetime import datetime, timedelta, timezone
from email.headerregistry import Address
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from html import escape

import pika
from sqlalchemy import CheckConstraint, DateTime, String, Text, create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/%2F")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://soa:soa_dev_password@postgres:5432/notification_db")
SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "false").lower() == "true"
SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "false").lower() == "true"
FROM_EMAIL = os.getenv("FROM_EMAIL", "").strip()
MAX_DELIVERY_ATTEMPTS = int(os.getenv("MAX_DELIVERY_ATTEMPTS", "5"))
logging.basicConfig(level=logging.INFO, format='{"timestamp":"%(asctime)s","level":"%(levelname)s","service":"notification","message":"%(message)s"}')
logger = logging.getLogger("notification")


class Base(DeclarativeBase):
    pass


class Delivery(Base):
    __tablename__ = "email_deliveries"
    __table_args__ = (
        CheckConstraint("status IN ('SENT','RETRYING','DEAD_LETTER')", name="ck_delivery_status"),
        CheckConstraint("attempt_count >= 0", name="ck_delivery_attempt_count"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    event_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(80))
    recipient: Mapped[str] = mapped_column(String(254))
    subject: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(24))
    attempt_count: Mapped[int] = mapped_column(default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def format_money(value: int) -> str:
    return f"{value:,.0f}".replace(",", ".") + " VND"


def format_datetime(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone(timedelta(hours=7))).strftime("%H:%M, %d/%m/%Y")
    except (TypeError, ValueError):
        return value


def render(payload: dict) -> tuple[str, str, str]:
    if payload["type"] == "otp.requested":
        subject = f"[iBanking Tuition] Xác thực giao dịch {payload['student_code']}"
        text = (
            f"Xin chào {payload['payer_name']},\n\n"
            "Bạn nhận được email này vì vừa yêu cầu thanh toán học phí trên iBanking Tuition.\n\n"
            f"Mã xác thực: {payload['otp']}\n"
            f"Số tiền: {format_money(int(payload['amount']))}\n"
            f"Mã giao dịch: {payload['payment_id']}\n"
            f"Mã hết hạn lúc: {format_datetime(payload['expires_at'])} và chỉ được dùng một lần.\n\n"
            "Nếu bạn không thực hiện giao dịch này, hãy bỏ qua email và không chia sẻ mã xác thực."
        )
    else:
        subject = f"[iBanking Tuition] Biên nhận thanh toán {payload['student_code']}"
        text = (
            f"Xin chào {payload['payer_name']},\n\n"
            f"Bạn đã thanh toán thành công học phí cho {payload['student_name']} ({payload['student_code']}).\n"
            f"Số tiền: {format_money(int(payload['amount']))}\n"
            f"Số dư còn lại: {format_money(int(payload['balance_after']))}\n"
            f"Mã giao dịch: {payload['payment_id']}\n"
            f"Thời gian: {format_datetime(payload['completed_at'])}\n"
        )
    return payload["to"], subject, text


def detail_row(label: str, value: str, *, emphasized: bool = False) -> str:
    value_style = "font-size:16px;font-weight:750;color:#0b1731;" if emphasized else "font-size:14px;font-weight:650;color:#172033;"
    return (
        '<tr><td style="padding:12px 0;border-bottom:1px solid #e4e9f1;'
        f'font-size:13px;color:#667085;">{escape(label)}</td>'
        f'<td align="right" style="padding:12px 0;border-bottom:1px solid #e4e9f1;{value_style}">{escape(value)}</td></tr>'
    )


def render_html(payload: dict) -> str:
    is_otp = payload["type"] == "otp.requested"
    payer_name = escape(str(payload["payer_name"]))
    student_code = str(payload["student_code"])
    payment_id = str(payload["payment_id"])
    amount = format_money(int(payload["amount"]))

    if is_otp:
        title = "Xác thực thanh toán"
        preheader = f"Mã OTP cho giao dịch học phí {student_code}"
        status_color = "#246bfd"
        status_background = "#eaf1ff"
        hero = f'''
          <p style="margin:0 0 8px;font-size:12px;font-weight:800;letter-spacing:1.4px;color:#246bfd;">XÁC THỰC GIAO DỊCH</p>
          <h1 style="margin:0;font-size:26px;line-height:1.25;color:#0b1731;">Mã OTP thanh toán học phí</h1>
          <p style="margin:14px 0 0;font-size:15px;line-height:1.65;color:#667085;">Xin chào <strong style="color:#172033;">{payer_name}</strong>, bạn nhận được email này vì vừa yêu cầu thanh toán học phí trên iBanking Tuition.</p>
          <div style="margin:26px 0;padding:22px 18px;text-align:center;background:#f5f8ff;border:1px solid #d8e5ff;border-radius:12px;">
            <p style="margin:0 0 9px;font-size:11px;font-weight:800;letter-spacing:1.5px;color:#667085;">MÃ XÁC THỰC</p>
            <p style="margin:0;font-family:Arial,sans-serif;font-size:34px;font-weight:800;letter-spacing:9px;color:#0b1731;">{escape(str(payload['otp']))}</p>
            <p style="margin:10px 0 0;font-size:12px;color:#667085;">Có hiệu lực đến {escape(format_datetime(payload['expires_at']))}</p>
          </div>'''
        rows = "".join([
            detail_row("Mã sinh viên", student_code),
            detail_row("Số tiền", amount, emphasized=True),
            detail_row("Mã giao dịch", payment_id),
        ])
        notice = '''<div style="margin-top:22px;padding:14px 16px;background:#fff8eb;border-left:3px solid #eaaa08;border-radius:7px;font-size:13px;line-height:1.6;color:#7a5b12;"><strong>Lưu ý bảo mật:</strong> iBanking không bao giờ yêu cầu bạn cung cấp mã OTP qua điện thoại hoặc tin nhắn.</div>'''
    else:
        title = "Thanh toán thành công"
        preheader = f"Giao dịch học phí {student_code} đã hoàn tất"
        status_color = "#087f69"
        status_background = "#eaf9f5"
        hero = f'''
          <div style="width:50px;height:50px;line-height:50px;text-align:center;background:#eaf9f5;border-radius:50%;font-size:25px;font-weight:800;color:#087f69;">✓</div>
          <p style="margin:20px 0 8px;font-size:12px;font-weight:800;letter-spacing:1.4px;color:#087f69;">GIAO DỊCH HOÀN TẤT</p>
          <h1 style="margin:0;font-size:26px;line-height:1.25;color:#0b1731;">Thanh toán học phí thành công</h1>
          <p style="margin:14px 0 24px;font-size:15px;line-height:1.65;color:#667085;">Xin chào <strong style="color:#172033;">{payer_name}</strong>, giao dịch của bạn đã được ghi nhận.</p>'''
        rows = "".join([
            detail_row("Sinh viên", str(payload["student_name"])),
            detail_row("Mã sinh viên", student_code),
            detail_row("Số tiền thanh toán", amount, emphasized=True),
            detail_row("Số dư còn lại", format_money(int(payload["balance_after"]))),
            detail_row("Thời gian", format_datetime(payload["completed_at"])),
            detail_row("Mã giao dịch", payment_id),
        ])
        notice = '''<div style="margin-top:22px;padding:14px 16px;background:#f5f7fb;border-radius:7px;font-size:13px;line-height:1.6;color:#667085;">Email này là biên nhận điện tử cho giao dịch của bạn. Vui lòng lưu lại khi cần đối chiếu.</div>'''

    return f'''<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)}</title></head>
<body style="margin:0;padding:0;background:#f5f7fb;font-family:Arial,'Helvetica Neue',sans-serif;color:#172033;">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;">{escape(preheader)}</div>
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#f5f7fb;"><tr><td align="center" style="padding:32px 14px;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:600px;">
      <tr><td style="padding:0 4px 18px;">
        <table role="presentation" cellspacing="0" cellpadding="0" border="0"><tr>
          <td style="width:42px;height:42px;text-align:center;background:#0b1731;border-radius:11px;font-size:18px;font-weight:800;color:#fff;">iB</td>
          <td style="padding-left:11px;"><div style="font-size:18px;font-weight:800;color:#0b1731;">iBanking</div><div style="margin-top:2px;font-size:10px;font-weight:700;letter-spacing:1.5px;color:#667085;">DIGITAL BANKING</div></td>
        </tr></table>
      </td></tr>
      <tr><td style="overflow:hidden;background:#fff;border:1px solid #e4e9f1;border-radius:16px;">
        <div style="height:5px;background:{status_color};"></div>
        <div style="padding:34px 36px 30px;">{hero}
          <div style="margin-top:4px;padding:2px 18px 0;background:#fff;border:1px solid #e4e9f1;border-radius:10px;">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">{rows}</table>
          </div>
          {notice}
        </div>
        <div style="padding:18px 36px;background:{status_background};border-top:1px solid #e4e9f1;font-size:12px;line-height:1.55;color:#667085;">Cần hỗ trợ? Liên hệ <strong style="color:{status_color};">1900 0000</strong>. Không trả lời trực tiếp email tự động này.</div>
      </td></tr>
      <tr><td align="center" style="padding:20px 20px 0;font-size:11px;line-height:1.6;color:#98a2b3;">© 2026 iBanking Tuition<br>Giao dịch được bảo vệ bằng xác thực OTP.</td></tr>
    </table>
  </td></tr></table>
</body></html>'''


def validate_smtp_config() -> None:
    missing = [
        name
        for name, value in (
            ("SMTP_HOST", SMTP_HOST),
            ("SMTP_USERNAME", SMTP_USERNAME),
            ("SMTP_PASSWORD", SMTP_PASSWORD),
            ("FROM_EMAIL", FROM_EMAIL),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(f"Thiếu cấu hình SMTP thật: {', '.join(missing)}")
    if SMTP_USE_TLS and SMTP_USE_SSL:
        raise RuntimeError("SMTP_USE_TLS và SMTP_USE_SSL không thể cùng bật")
    if not 1 <= SMTP_PORT <= 65535:
        raise RuntimeError("SMTP_PORT không hợp lệ")


def send_email(recipient: str, subject: str, content: str, html_content: str | None = None) -> None:
    message = EmailMessage()
    sender_domain = FROM_EMAIL.rpartition("@")[2] or None
    message["From"] = Address(display_name="iBanking Tuition", addr_spec=FROM_EMAIL)
    message["To"] = recipient
    message["Reply-To"] = Address(display_name="iBanking Tuition", addr_spec=FROM_EMAIL)
    message["Subject"] = subject
    message["Date"] = formatdate(localtime=False)
    message["Message-ID"] = make_msgid(domain=sender_domain)
    message["Auto-Submitted"] = "auto-generated"
    message["X-Auto-Response-Suppress"] = "All"
    message.set_content(content)
    if html_content:
        message.add_alternative(html_content, subtype="html")
    validate_smtp_config()
    smtp_class = smtplib.SMTP_SSL if SMTP_USE_SSL else smtplib.SMTP
    options = {"timeout": 15}
    if SMTP_USE_SSL:
        options["context"] = ssl.create_default_context()
    with smtp_class(SMTP_HOST, SMTP_PORT, **options) as smtp:
        if SMTP_USE_TLS:
            smtp.ehlo()
            smtp.starttls(context=ssl.create_default_context())
            smtp.ehlo()
        if SMTP_USERNAME:
            if not SMTP_PASSWORD:
                raise RuntimeError("Thiếu SMTP_PASSWORD")
            smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
        smtp.send_message(message)


def handle(channel, method, properties, body: bytes) -> None:
    payload = json.loads(body.decode())
    event_id = payload["event_id"]
    with SessionLocal.begin() as db:
        delivery = db.scalar(select(Delivery).where(Delivery.event_id == event_id).with_for_update())
        if delivery and delivery.status == "SENT":
            channel.basic_ack(method.delivery_tag)
            return
    recipient, subject, content = render(payload)
    html_content = render_html(payload)
    retry_count = int((properties.headers or {}).get("x-retry-count", 0)) if properties else 0
    try:
        send_email(recipient, subject, content, html_content)
        with SessionLocal.begin() as db:
            delivery = db.scalar(select(Delivery).where(Delivery.event_id == event_id).with_for_update())
            if not delivery:
                delivery = Delivery(event_id=event_id, event_type=payload["type"], recipient=recipient, subject=subject, status="SENT")
                db.add(delivery)
            delivery.status = "SENT"
            delivery.attempt_count = retry_count + 1
            delivery.last_error = None
            delivery.delivered_at = datetime.now(timezone.utc)
        channel.basic_ack(method.delivery_tag)
        logger.info(f"email_sent event_id={event_id} type={payload['type']} recipient={recipient}")
    except IntegrityError:
        channel.basic_ack(method.delivery_tag)
    except Exception as exc:
        next_attempt = retry_count + 1
        with SessionLocal.begin() as db:
            delivery = db.scalar(select(Delivery).where(Delivery.event_id == event_id).with_for_update())
            if not delivery:
                delivery = Delivery(event_id=event_id, event_type=payload["type"], recipient=recipient, subject=subject, status="FAILED")
                db.add(delivery)
            delivery.status = "DEAD_LETTER" if next_attempt >= MAX_DELIVERY_ATTEMPTS else "RETRYING"
            delivery.attempt_count = next_attempt
            delivery.last_error = str(exc)[:2000]
        target = "notifications.dlq" if next_attempt >= MAX_DELIVERY_ATTEMPTS else "notifications"
        channel.basic_publish(exchange="", routing_key=target, body=body, properties=pika.BasicProperties(delivery_mode=2, content_type="application/json", message_id=event_id, type=payload["type"], headers={"x-retry-count": next_attempt}))
        channel.basic_ack(method.delivery_tag)
        logger.warning(f"email_delivery_failed event_id={event_id} attempt={next_attempt} target={target} error={type(exc).__name__}")
        if target == "notifications":
            time.sleep(min(2**next_attempt, 8))


def run() -> None:
    validate_smtp_config()
    logger.info(f"real_smtp_configured host={SMTP_HOST} port={SMTP_PORT} tls={SMTP_USE_TLS} ssl={SMTP_USE_SSL}")
    while True:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
            channel = connection.channel()
            channel.queue_declare(queue="notifications", durable=True)
            channel.queue_declare(queue="notifications.dlq", durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue="notifications", on_message_callback=handle)
            logger.info("notification_worker_ready")
            channel.start_consuming()
        except Exception as exc:
            logger.warning(f"notification_worker_reconnecting error={type(exc).__name__}")
            time.sleep(3)


if __name__ == "__main__":
    run()

