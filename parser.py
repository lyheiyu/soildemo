# parser.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any
import struct


MAGIC = b"\xFE\xDC"


@dataclass
class Frame:
    ftype: int          # 0x1001 / 0x1002 / 0x1008
    device_id: str      # hex string, 12 chars
    seq: int
    payload: bytes


class FEParser:
    """
    Stream parser. Feed raw TCP bytes, it returns complete FE DC frames.
    Frame format (validated by your captures):
      FE DC (2)
      type (2)
      device_id (6)
      seq (2)
      length (2)
      payload (length)
    """
    def __init__(self) -> None:
        self._buf = b""

    def feed(self, data: bytes) -> List[Frame]:
        self._buf += data
        frames: List[Frame] = []

        while True:
            start = self._buf.find(MAGIC)
            if start < 0:
                # keep small tail in case MAGIC split
                self._buf = self._buf[-1:] if len(self._buf) > 1 else self._buf
                break

            if start > 0:
                self._buf = self._buf[start:]

            # header minimal length: 2 + 2 + 6 + 2 + 2 = 14
            if len(self._buf) < 14:
                break

            ftype = int.from_bytes(self._buf[2:4], "big")
            dev = self._buf[4:10].hex()
            seq = int.from_bytes(self._buf[10:12], "big")
            length = int.from_bytes(self._buf[12:14], "big")

            total = 14 + length
            if len(self._buf) < total:
                break

            payload = self._buf[14:total]
            frames.append(Frame(ftype=ftype, device_id=dev, seq=seq, payload=payload))
            self._buf = self._buf[total:]

        return frames


def decode_1001_templates(payload: bytes) -> Dict[str, Any]:
    """
    Your sample:
      payload begins with: 10 00 00 02 00 02 00 17 ...
      count seems at offset 6..8 (0x0017 = 23)
      templates follow from offset 8, each 2 bytes big-endian
    """
    out: Dict[str, Any] = {"ok": False, "count": 0, "templates": []}
    if len(payload) < 8:
        return out

    count = int.from_bytes(payload[6:8], "big")
    templates: List[int] = []
    pos = 8
    for _ in range(count):
        if pos + 2 > len(payload):
            break
        templates.append(int.from_bytes(payload[pos:pos+2], "big"))
        pos += 2

    out["ok"] = True
    out["count"] = len(templates)
    out["templates"] = templates
    return out


def decode_1002_value(payload: bytes) -> Optional[Dict[str, Any]]:
    """
    Your sample:
      length = 0x0007
      payload = code(2) + flag(1) + float(4 little-endian)
      e.g. 00 19 0e 75 00 dc 41
    """
    if len(payload) != 7:
        return None

    code = int.from_bytes(payload[0:2], "big")
    flag = payload[2]
    value = struct.unpack("<f", payload[3:7])[0]

    return {"code": code, "flag": flag, "value": float(value)}