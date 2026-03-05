# tcp_server.py
from __future__ import annotations
import socket
import threading
from typing import Optional

from parser import FEParser, decode_1001_templates, decode_1002_value
from database import insert_measurement, replace_templates


HOST = "0.0.0.0"
PORT = 5000


def handle_conn(conn: socket.socket, addr) -> None:
    conn.settimeout(120)
    parser = FEParser()
    print("connected:", addr, flush=True)
    try:
        conn.sendall(b"\x00")
        print("sent probe 00", flush=True)
    except Exception as e:
        print("probe send failed:", repr(e), flush=True)
    try:
        while True:
            data = conn.recv(4096)
            print(f"recv {len(data)} bytes from {addr}")
            if data:
                print("head:", data[:16].hex(), flush=True)
            if not data:
                break

            frames = parser.feed(data)
            for fr in frames:
                if fr.ftype == 0x1001:
                    info = decode_1001_templates(fr.payload)
                    if info.get("ok"):
                        replace_templates(fr.device_id, info["templates"])

                        # ✅ 加在这里：把 23 个模板编号整串打印出来
                        print(f"[1001-templates] device={fr.device_id} seq={fr.seq} templates={info['templates']}",
                              flush=True)

                        print(f"[1001] device={fr.device_id} templates={info['count']} seq={fr.seq}", flush=True)
                    else:
                        print(f"[1001] device={fr.device_id} bad payload len={len(fr.payload)}", flush=True)





                elif fr.ftype == 0x1002:

                    print(

                        f"[1002-raw] device={fr.device_id} payload_len={len(fr.payload)} hex={fr.payload.hex()}",

                        flush=True

                    )

                    v = decode_1002_value(fr.payload)

                    if not isinstance(v, dict):
                        print(f"[1002] decode failed, payload_len={len(fr.payload)}", flush=True)

                        continue

                    code = int(v.get("code", 0))

                    raw = v.get("raw")

                    flag = int(v.get("flag", 0))

                    if raw is None:
                        print(f"[1002] missing raw, v={v}", flush=True)

                        continue

                    value = float(raw) / 10.0

                    insert_measurement(fr.device_id, code, value, flag)

                    print(f"[1002] device={fr.device_id} code={code} raw={raw} value={value:.4f}", flush=True)
                elif fr.ftype == 0x1008:
                    print(f"[1008-raw] device={fr.device_id} payload_len={len(fr.payload)} hex={fr.payload.hex()}",
                          flush=True)
    except socket.timeout:
        pass
    except Exception as e:
        print("conn error:", repr(e))
    finally:
        try:
            conn.close()
        except Exception:
            pass


def start_tcp_server() -> None:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(50)
    print(f"TCP server listening on {HOST}:{PORT}")

    while True:
        conn, addr = s.accept()
        print("connected:", addr)
        t = threading.Thread(target=handle_conn, args=(conn, addr), daemon=True)
        t.start()


if __name__ == "__main__":
    start_tcp_server()