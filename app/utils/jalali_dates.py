"""تبدیل و نمایش تاریخ شمسی (جلالی)."""

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

import jdatetime

TEHRAN = ZoneInfo("Asia/Tehran")


def now_tehran() -> datetime:
  return datetime.now(TEHRAN)


def today_tehran() -> date:
  return now_tehran().date()


def jalali_today_label() -> str:
  """تاریخ امروز شمسی به‌صورت عددی YYYY/MM/DD."""
  jtoday = jdatetime.date.fromgregorian(date=today_tehran())
  return jtoday.strftime("%Y/%m/%d")


def jalali_date_filename() -> str:
  """تاریخ شمسی برای نام فایل: YYYY_MM_DD."""
  return jalali_today_label().replace("/", "_")


def format_jalali_date(d: date | None) -> str:
  if not d:
    return "—"
  jd = jdatetime.date.fromgregorian(date=d)
  return jd.strftime("%Y/%m/%d")


def format_jalali_datetime(dt: datetime | None) -> str:
  if not dt:
    return "—"
  if dt.tzinfo is None:
    dt = dt.replace(tzinfo=timezone.utc).astimezone(TEHRAN)
  else:
    dt = dt.astimezone(TEHRAN)
  jd = jdatetime.datetime.fromgregorian(datetime=dt)
  return jd.strftime("%Y/%m/%d — %H:%M")


def parse_jalali_date(value: str | None) -> date | None:
  if not value or not str(value).strip():
    return None
  text = str(value).strip().replace("-", "/")
  parts = text.split("/")
  if len(parts) != 3:
    return None
  try:
    y, m, d = (int(p) for p in parts)
    return jdatetime.date(y, m, d).togregorian()
  except (ValueError, TypeError):
    return None


def parse_jalali_datetime(value: str | None) -> datetime | None:
  if not value or not str(value).strip():
    return None
  text = str(value).strip()
  if " " in text:
    date_part, time_part = text.split(" ", 1)
  elif "T" in text:
    date_part, time_part = text.split("T", 1)
  else:
    d = parse_jalali_date(text)
    if not d:
      return None
    return datetime.combine(d, time.min).replace(tzinfo=TEHRAN).astimezone(timezone.utc).replace(tzinfo=None)

  d = parse_jalali_date(date_part)
  if not d:
    return None
  try:
    if ":" in time_part:
      tparts = time_part.split(":")
      hour = int(tparts[0])
      minute = int(tparts[1]) if len(tparts) > 1 else 0
      t = time(hour=hour, minute=minute)
    else:
      t = time.min
    jd = jdatetime.datetime.fromgregorian(datetime=datetime.combine(d, t))
    return jd.togregorian().replace(tzinfo=TEHRAN).astimezone(timezone.utc).replace(tzinfo=None)
  except (ValueError, TypeError):
    return None


def gregorian_to_jalali_input(d: date | None) -> str:
  if not d:
    return ""
  jd = jdatetime.date.fromgregorian(date=d)
  return jd.strftime("%Y/%m/%d")


def gregorian_to_jalali_datetime_input(dt: datetime | None) -> str:
  if not dt:
    return ""
  if dt.tzinfo is None:
    dt = dt.replace(tzinfo=timezone.utc)
  local = dt.astimezone(TEHRAN)
  jd = jdatetime.datetime.fromgregorian(datetime=local.replace(tzinfo=None))
  return jd.strftime("%Y/%m/%d %H:%M")


def today_utc_range() -> tuple[datetime, datetime]:
  """بازه شروع/پایان «امروز» بر اساس وقت تهران (برای فیلتر دیتابیس)."""
  now = now_tehran()
  start = datetime.combine(now.date(), time.min, tzinfo=TEHRAN)
  end = datetime.combine(now.date(), time.max, tzinfo=TEHRAN)
  return (
    start.astimezone(timezone.utc).replace(tzinfo=None),
    end.astimezone(timezone.utc).replace(tzinfo=None),
  )


def today_gregorian_date() -> date:
  return today_tehran()
