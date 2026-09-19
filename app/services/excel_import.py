"""واردسازی گروهی سرنخ از فایل اکسل."""

from __future__ import annotations

import pandas as pd
from flask_login import current_user

from app.extensions import db
from app.forms.lh_forms import BUSINESS_TYPE_CHOICES
from app.models import Lead
from app.services.lead_workflow import send_lead_to_sdr_pool
from app.utils.phone import (
  format_phone_for_storage,
  load_normalized_phone_index,
  normalize_phone,
)

EXCEL_SOURCE_LABEL = "آپلود اکسل"
VALID_BUSINESS_TYPES = {c[0] for c in BUSINESS_TYPE_CHOICES if c[0]}


def _cell_str(value) -> str:
  if value is None or (isinstance(value, float) and pd.isna(value)):
    return ""
  return str(value).strip()


def _normalize_business_type(raw: str) -> str:
  text = _cell_str(raw)
  if not text:
    return "سایر"
  if text in VALID_BUSINESS_TYPES:
    return text
  return "سایر"


def import_leads_from_excel(file_storage) -> tuple[int, int]:
  """
  خواندن ستون‌های B، C، D از ردیف ۲ به بعد.
  برمی‌گرداند: (تعداد واردشده، تعداد ردشده به‌خاطر تکراری).
  """
  filename = (file_storage.filename or "").lower()
  if filename.endswith(".xls") and not filename.endswith(".xlsx"):
    df = pd.read_excel(file_storage, header=None, engine=None)
  else:
    df = pd.read_excel(file_storage, header=None, engine="openpyxl")

  known_phones = load_normalized_phone_index()
  imported = 0
  skipped = 0

  for row_idx in range(1, len(df)):
    company_name = _cell_str(df.iloc[row_idx, 1] if df.shape[1] > 1 else "")
    business_type = _normalize_business_type(
      df.iloc[row_idx, 2] if df.shape[1] > 2 else ""
    )
    phone_raw = _cell_str(df.iloc[row_idx, 3] if df.shape[1] > 3 else "")
    phone_stored = format_phone_for_storage(phone_raw)

    if not company_name and not phone_stored:
      continue

    if not company_name or not phone_stored:
      skipped += 1
      continue

    phone_norm = normalize_phone(phone_stored)
    if not phone_norm:
      skipped += 1
      continue

    if phone_norm in known_phones:
      skipped += 1
      continue

    lead = Lead(
      company_name=company_name[:200],
      phone_number=phone_stored,
      business_type=business_type,
      source=EXCEL_SOURCE_LABEL,
      current_stage=2,
      pipeline_status="active",
      created_by_id=current_user.id if current_user.is_authenticated else None,
    )
    send_lead_to_sdr_pool(lead)
    db.session.add(lead)
    known_phones.add(phone_norm)
    imported += 1

  if imported:
    db.session.commit()
  else:
    db.session.rollback()

  return imported, skipped
