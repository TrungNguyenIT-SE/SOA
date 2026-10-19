import contextvars
import json
import logging
import sys
import time
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

correlation_id_var = contextvars.ContextVar("correlation_id", default="-")


class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(), "level": record.levelname, "service": getattr(record, "service", "unknown"), "correlationId": correlation_id_var.get(), "message": record.getMessage()}, ensure_ascii=False)


def install_platform(app: FastAPI, service: str):
    logger = logging.getLogger(service)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)

    def error(request, status, code, message, fields=None):
        return JSONResponse(status_code=status, content={"timestamp": datetime.now(timezone.utc).isoformat(), "status": status, "code": code, "message": message, "path": request.url.path, "correlationId": correlation_id_var.get(), "fieldErrors": fields or []}, headers={"X-Correlation-Id": correlation_id_var.get()})

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        correlation_id = (request.headers.get("X-Correlation-Id") or str(uuid.uuid4()))[:128]
        token = correlation_id_var.set(correlation_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("unhandled_request_error", extra={"service": service})
            return error(request, 500, "INTERNAL_ERROR", "Hệ thống gặp lỗi ngoài dự kiến.")
        finally:
            logger.info(f"request method={request.method} path={request.url.path} duration_ms={round((time.perf_counter() - started) * 1000, 2)}", extra={"service": service})
            correlation_id_var.reset(token)
        response.headers.update({"X-Correlation-Id": correlation_id, "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer"})
        return response

    @app.exception_handler(HTTPException)
    async def http_exception(request: Request, exc: HTTPException):
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        return error(request, exc.status_code, detail.get("code", "HTTP_ERROR"), detail.get("message", str(exc.detail)))

    @app.exception_handler(RequestValidationError)
    async def validation_exception(request: Request, exc: RequestValidationError):
        fields = [{"field": ".".join(map(str, item["loc"])), "message": item["msg"]} for item in exc.errors()]
        return error(request, 422, "VALIDATION_ERROR", "Dữ liệu đầu vào không hợp lệ.", fields)

    return logger
