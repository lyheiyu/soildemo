# app.py
from __future__ import annotations
import threading
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.requests import Request
from fastapi.templating import Jinja2Templates

from database import init_db, get_latest_measurements, get_devices, get_latest_by_code
from tcp_server import start_tcp_server

app = FastAPI()
templates = Jinja2Templates(directory="templates")


# 你可以在这里维护 code 到名字的映射，后续我们再根据设备模板完善
CODE_NAME = {
    0x0019: "Value(0x0019)",
    0x001A: "Value(0x001A)",
    0x001B: "Value(0x001B)",
}


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    t = threading.Thread(target=start_tcp_server, daemon=True)
    t.start()

@app.get("/health")
def health():
    return {"ok": True}
@app.get("/", response_class=HTMLResponse)
def home(request: Request, device_id: str | None = None):
    devices = get_devices()
    if device_id is None and devices:
        device_id = devices[0]

    latest = get_latest_measurements(limit=50)
    latest_by_code = get_latest_by_code(device_id) if device_id else []

    # 补充 name
    latest_by_code_view = []
    for ts, dev, code, value, flag in latest_by_code:
        latest_by_code_view.append({
            "ts": ts,
            "device_id": dev,
            "code": code,
            "name": CODE_NAME.get(code, f"code_0x{code:04x}"),
            "value": value,
            "flag": flag
        })

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "devices": devices,
            "device_id": device_id,
            "latest_by_code": latest_by_code_view,
            "latest_rows": latest,
        },
    )