# sensor_meta.py
from dataclasses import dataclass

@dataclass(frozen=True)
class Meta:
    name: str
    unit: str
    scale: float
    signed: bool

SENSOR_INDEX_META = {
    0:  Meta("Air Temperature", "°C", 10.0, True),   # 0.1
    1:  Meta("Air Humidity", "%", 10.0, False),      # 0.1
    2:  Meta("Air Pressure", "hPa", 100.0, False),   # 0.01
    3:  Meta("Light", "lux", 1.0, False),
    4:  Meta("CO2", "ppm", 1.0, False),
    5:  Meta("CO", "ppm", 1.0, False),
    6:  Meta("SO2", "ppm", 1.0, False),
    7:  Meta("NO2", "ppm", 1.0, False),
    8:  Meta("NH3", "ppm", 100.0, False),           # 0.01
    9:  Meta("Wind Speed", "m/s", 10.0, False),      # 0.1
    10: Meta("Wind Direction", "°", 1.0, False),
    11: Meta("Rainfall", "mm", 10.0, False),         # 0.1
    12: Meta("Solar Radiation", "W/m²", 1.0, False),
    13: Meta("Soil Temperature", "°C", 10.0, True),  # 0.1
    14: Meta("Soil Moisture", "%", 10.0, False),     # 0.1
    15: Meta("Soil pH", "pH", 100.0, False),         # 0.01
    16: Meta("Soil EC", "µS/cm", 1.0, False),
    17: Meta("Soil N", "mg/kg", 1.0, False),
    18: Meta("Soil P", "mg/kg", 1.0, False),
    19: Meta("Soil K", "mg/kg", 1.0, False),
}