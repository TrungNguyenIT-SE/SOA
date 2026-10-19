import contextvars, json, logging, sys, time, uuid
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
correlation_id_var=contextvars.ContextVar("correlation_id",default="-")
class JsonFormatter(logging.Formatter):
    def format(self,r): return json.dumps({"timestamp":datetime.now(timezone.utc).isoformat(),"level":r.levelname,"service":getattr(r,"service","unknown"),"correlationId":correlation_id_var.get(),"message":r.getMessage()},ensure_ascii=False)
def install_platform(app:FastAPI,service:str):
    logger=logging.getLogger(service);logger.setLevel(logging.INFO);logger.propagate=False
    if not logger.handlers:
        handler=logging.StreamHandler(sys.stdout);handler.setFormatter(JsonFormatter());logger.addHandler(handler)
    def error(req,status,code,msg,fields=None): return JSONResponse(status_code=status,content={"timestamp":datetime.now(timezone.utc).isoformat(),"status":status,"code":code,"message":msg,"path":req.url.path,"correlationId":correlation_id_var.get(),"fieldErrors":fields or []},headers={"X-Correlation-Id":correlation_id_var.get()})
    @app.middleware("http")
    async def context(req:Request,call_next):
        cid=(req.headers.get("X-Correlation-Id") or str(uuid.uuid4()))[:128];token=correlation_id_var.set(cid);started=time.perf_counter()
        try: response=await call_next(req)
        except Exception: logger.exception("unhandled_request_error",extra={"service":service});return error(req,500,"INTERNAL_ERROR","Hệ thống gặp lỗi ngoài dự kiến.")
        finally: logger.info(f"request method={req.method} path={req.url.path} duration_ms={round((time.perf_counter()-started)*1000,2)}",extra={"service":service});correlation_id_var.reset(token)
        response.headers.update({"X-Correlation-Id":cid,"X-Content-Type-Options":"nosniff","X-Frame-Options":"DENY","Referrer-Policy":"no-referrer"});return response
    @app.exception_handler(HTTPException)
    async def http_error(req:Request,exc:HTTPException):
        detail=exc.detail if isinstance(exc.detail,dict) else {};return error(req,exc.status_code,detail.get("code","HTTP_ERROR"),detail.get("message",str(exc.detail)))
    @app.exception_handler(RequestValidationError)
    async def validation(req:Request,exc:RequestValidationError): return error(req,422,"VALIDATION_ERROR","Dữ liệu đầu vào không hợp lệ.",[{"field":".".join(map(str,e["loc"])),"message":e["msg"]} for e in exc.errors()])
    return logger
