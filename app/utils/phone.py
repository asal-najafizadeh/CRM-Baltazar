"""اعتبارسنجی و نرمال‌سازی شماره تماس."""

from app.extensions import db
from app.models import Lead

DUPLICATE_PHONE_MESSAGE = (
  "این شماره تماس قبلاً در سیستم ثبت شده است و تکراری می‌باشد."
)

_PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
_ASCII_DIGITS = "0123456789"
_DIGIT_MAP = str.maketrans(_PERSIAN_DIGITS, _ASCII_DIGITS)
_ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
_ARABIC_MAP = str.maketrans(_ARABIC_DIGITS, _ASCII_DIGITS)


def normalize_phone(phone: str | None) -> str:
  if phone is None:
    return ""
  text = str(phone).strip().translate(_DIGIT_MAP).translate(_ARABIC_MAP)
  return "".join(c for c in text if c.isdigit())


def format_phone_for_storage(phone: str | None) -> str:
  """
  نرمال‌سازی برای ذخیره: ارقام یکسان + پیشوند ۰ برای ۹۱۲…
  (اگر با 9 شروع شود و 09 نباشد، 0 اضافه می‌شود).
  """
  if phone is None:
    return ""
  raw = str(phone).strip()
  if not raw:
    return ""
  digits = normalize_phone(raw)
  if not digits:
    return raw[:40]
  if digits.startswith("9") and not digits.startswith("09"):
    digits = "0" + digits
  return digits[:40]


def lead_phone_fields(lead: Lead) -> list[str]:
  return [lead.phone_number, lead.phone_number_2, lead.phone_number_3]


def normalize_phone_list(phones: list[str] | None) -> list[str]:
  """لیست شماره‌های نرمال‌شده و یکتا (بدون تکرار داخل همان فرم)."""
  seen: set[str] = set()
  result: list[str] = []
  for raw in phones or []:
    formatted = format_phone_for_storage(raw)
    if not formatted:
      continue
    key = normalize_phone(formatted)
    if key in seen:
      continue
    seen.add(key)
    result.append(formatted)
  return result


def phone_number_exists(phone: str, exclude_lead_id: int | None = None) -> bool:
  normalized = normalize_phone(phone)
  if not normalized:
    return False

  query = Lead.query.filter(Lead.active_only())
  if exclude_lead_id is not None:
    query = query.filter(Lead.id != exclude_lead_id)

  for lead in query.all():
    for field_phone in lead_phone_fields(lead):
      if field_phone and normalize_phone(field_phone) == normalized:
        return True
  return False


def any_phone_exists(phones: list[str], exclude_lead_id: int | None = None) -> str | None:
  """اولین شماره تکراری در سیستم را برمی‌گرداند؛ در غیر این صورت None."""
  for phone in phones:
    if phone_number_exists(phone, exclude_lead_id=exclude_lead_id):
      return phone
  return None


def load_normalized_phone_index() -> set[str]:
  index: set[str] = set()
  for lead in Lead.query.filter(Lead.active_only()).all():
    for field_phone in lead_phone_fields(lead):
      key = normalize_phone(field_phone)
      if key:
        index.add(key)
  return index
