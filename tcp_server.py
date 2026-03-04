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
            if data:
                print("head:", data[:16].hex())
            if not data:
                break

            frames = parser.feed(data)
            for fr in frames:
                if fr.ftype == 0x1001:
                    info = decode_1001_templates(fr.payload)
                    if info.get("ok"):
                        replace_templates(fr.device_id, info["templates"])
                        print(f"[1001] device={fr.device_id} templates={info['count']} seq={fr.seq}")
                    else:
                        print(f"[1001] device={fr.device_id} bad payload len={len(fr.payload)}")


                elif fr.ftype == 0x1002:

                    print(f"[1002-raw] device={fr.device_id} payload_len={len(fr.payload)} hex={fr.payload.hex()}",
                          flush=True)
                    v = decode_1002_value(fr.payload)
                    if v:
                        insert_measurement(fr.device_id, v["code"], v["value"], v["flag"])
                        print(f"[1002] device={fr.device_id} code=0x{v['code']:04x} value={v['value']:.4f} flag=0x{v['flag']:02x}")
                    else:
                        print(f"[1002] device={fr.device_id} unexpected payload len={len(fr.payload)}")

                elif fr.ftype == 0x1008:
                    # 暂时只记录有 1008 到来，后续你给我更多样本我再写完整解析
                    print(f"[1008] device={fr.device_id} payload_len={len(fr.payload)} seq={fr.seq}")

                else:
                    print(f"[????] device={fr.device_id} ftype=0x{fr.ftype:04x} payload_len={len(fr.payload)} seq={fr.seq}")

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