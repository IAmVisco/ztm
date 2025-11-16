import inspect
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

ZTMTimeZone = ZoneInfo(os.environ.get("TIMEZONE", "CET"))


@dataclass
class ZTMDepartureDataReading:
    def __post_init__(self):
        if not re.match(r'^\d{2}:\d{2}:\d{2}$', self.czas):
            raise ValueError("The 'czas' field must be in HH:MM:SS format.")

    kierunek: str = field(default="na")
    czas: str = field(default="00:00:00")

    symbol_1: Optional[str] = field(default=None)
    symbol_2: Optional[str] = field(default=None)
    trasa: Optional[str] = field(default=None)
    brygada: Optional[str] = field(default=None)

    @classmethod
    def from_dict(cls, data):
        return cls(**{
            k: v for k, v in data.items()
            if k in inspect.signature(cls).parameters
        })

    @property
    def night_bus(self) -> bool:
        _hour, _, _ = self.czas.split(':')

        hour = int(_hour)

        if int(hour) >= 24:
            return True

        return False

    @property
    def dt(self):
        hour, minute, _ = self.czas.split(':')

        hour = int(hour)
        minute = int(minute)

        if int(hour) >= 24:
            hour = hour - 24

        now = datetime.now().astimezone(tz=ZTMTimeZone)

        try:
            # Build timezone-aware datetime in ZTM timezone, with correct date rollover
            target_date = now.date() + timedelta(days=1 if self.night_bus else 0)
            local_dt = datetime(
                year=target_date.year,
                month=target_date.month,
                day=target_date.day,
                hour=hour,
                minute=minute,
                second=0,
                microsecond=0,
                tzinfo=ZTMTimeZone,
            )

            dt = local_dt.astimezone(timezone.utc)
            
            return dt
        except Exception:
            return None

    @property
    def time_to_depart(self):
        now = datetime.now(timezone.utc)

        return int((self.dt - now).seconds / 60)


@dataclass
class ZTMDepartureData:
    departures: list[ZTMDepartureDataReading]
