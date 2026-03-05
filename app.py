# app.py
from __future__ import annotations

import threading
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.requests import Request
from fastapi.templating import Jinja2Templates

from database import (
    init_db,
    get_latest_measurements,
    get_devices,
    get_latest_by_code,
    upsert_template_meta,
    get_template_meta_map,
    get_templates_for_device,
    get_min_code,
)
from tcp_server import start_tcp_server

app = FastAPI()
templates = Jinja2Templates(directory="templates")


# Temporary mapping: code -> template_id
# Later we can learn this mapping automatically once we confirm the protocol
CODE_TO_TEMPLATE: dict[int, int] = {
    0x0018: 342,  # example: treat code 0x0018 as Soil N for now
}


@app.on_event("startup")
def on_startup() -> None:
    init_db()

    # Insert/Update template meta information
    upsert_template_meta([
        (327, "Air Temperature", "°C", 0.1),
        (328, "Air Humidity", "%RH", 0.1),
        (554, "Air Pressure", "hPa", 0.01),
        (1575, "Illuminance / Optical Rain", "lux", 1.0),
        (555, "CO2", "ppm", 1.0),
        (468, "CO", "ppm", 1.0),
        (466, "SO2", "ppm", 1.0),
        (467, "NO2", "ppm", 1.0),
        (2694, "NH3", "ppm", 0.01),
        (345, "Wind Speed", "m/s", 0.1),
        (656, "Wind Direction", "deg", 1.0),
        (333, "Rainfall", "mm", 0.1),
        (336, "Solar Radiation", "W/m²", 1.0),
        (337, "Soil Temperature", "°C", 0.1),
        (338, "Soil Moisture", "%", 0.1),
        (341, "Soil pH", "pH", 0.01),
        (339, "Soil EC", "uS/cm", 1.0),
        (342, "Soil N", "mg/kg", 1.0),
        (556, "Soil P", "mg/kg", 1.0),
        (344, "Soil K", "mg/kg", 1.0),
    ])

    # Start TCP ingest server in background thread
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

    latest_rows = get_latest_measurements(limit=50)
    latest_by_code = get_latest_by_code(device_id) if device_id else []

    # template_id -> {name, unit, scale}
    meta_map = get_template_meta_map()

    # ✅ 从 1001 保存的 templates 表里取出该设备模板顺序
    device_templates = get_templates_for_device(device_id) if device_id else []
    base_code = get_min_code(device_id) if device_id else None

    latest_by_code_view = []
    for ts, dev, code, value, flag in latest_by_code:

        # ✅ 核心：把 code 当成“传感器索引”，映射到 template_id
        template_id = None
        # A) code 是带偏移的通道号，例如从 0x001B 开始
        if base_code is not None and device_templates:
            idx = int(code) - int(base_code)
            if 0 <= idx < len(device_templates):
                template_id = device_templates[idx]

        # B) 兼容：如果 code 本身就是 template_id
        if template_id is None and int(code) in meta_map:
            template_id = int(code)

        meta = meta_map.get(template_id) if template_id else None

        name = meta["name"] if meta else f"code_0x{code:04x}"
        unit = meta["unit"] if meta else ""
        scale = meta["scale"] if meta else 1.0

        # 如果 value 是 raw，可以用 scale 转换；你现在先保持原样
        value_view = float(value)

        latest_by_code_view.append({
            "ts": ts,
            "device_id": dev,
            "code": code,
            "template_id": template_id,
            "name": name,
            "unit": unit,
            "value": value_view,
            "flag": flag,
        })

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "devices": devices,
            "device_id": device_id,
            "latest_by_code": latest_by_code_view,
            "latest_rows": latest_rows,
        },
    )