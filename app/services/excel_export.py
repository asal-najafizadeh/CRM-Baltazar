"""خروجی اکسل لیدها برای پنل ادمین و SDR."""

from __future__ import annotations

from io import BytesIO

import pandas as pd
from sqlalchemy import and_, or_

from app.models import Lead
from app.utils.jalali_dates import (
  format_jalali_date,
  format_jalali_datetime,
  jalali_date_filename,
  today_utc_range,
)


def _phones_joined(lead: Lead) -> str:
  nums = lead.all_phone_numbers
  return " | ".join(nums) if nums else lead.phone_number or ""


def _setter_meeting_type(location: str | None) -> str:
  if not location or not str(location).strip():
    return "—"
  loc = str(location).strip().lower()
  if any(
    token in loc
    for token in ("http://", "https://", "zoom", "meet.google", "teams", "آنلاین")
  ):
    return "آنلاین"
  return "حضوری"


def _setter_meeting_parts(lead: Lead) -> tuple[str, str]:
  dt = lead.setter_meeting_date
  if not dt:
    return "—", "—"
  full = format_jalali_datetime(dt)
  if " — " in full:
    date_part, time_part = full.split(" — ", 1)
    return date_part, time_part
  return full, "—"


def _contract_amount(lead: Lead) -> str:
  if lead.deal_outcome == "won" and lead.proposal_amount is not None:
    return str(lead.proposal_amount)
  if lead.pipeline_status == "closed_won" and lead.proposal_amount is not None:
    return str(lead.proposal_amount)
  return "—"


def _closer_notes(lead: Lead) -> str:
  return (lead.closer_notes or lead.closing_notes or "").strip() or "—"


def _dataframe_to_xlsx(df: pd.DataFrame) -> BytesIO:
  buffer = BytesIO()
  with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    df.to_excel(writer, index=False, sheet_name="لیدها")
  buffer.seek(0)
  return buffer


def _lh_base_row(lead: Lead) -> dict:
  return {
    "نام کسب و کار": lead.company_name,
    "شماره‌های تماس": _phones_joined(lead),
    "نوع کسب و کار": lead.business_type_display,
    "منبع": lead.source_display,
    "آدرس سایت": lead.website or "—",
    "تلگرام": lead.telegram or "—",
    "اینستاگرام": lead.instagram or "—",
    "آدرس محل": lead.address or "—",
    "توضیحات کلی": lead.description or "—",
  }


def build_sdr_daily_rows(leads: list[Lead]) -> pd.DataFrame:
  rows = [_lh_base_row(lead) for lead in leads]
  columns = [
    "نام کسب و کار",
    "شماره‌های تماس",
    "نوع کسب و کار",
    "منبع",
    "آدرس سایت",
    "تلگرام",
    "اینستاگرام",
    "آدرس محل",
    "توضیحات کلی",
  ]
  return pd.DataFrame(rows, columns=columns) if rows else pd.DataFrame(columns=columns)


def build_sdr_department_rows(leads: list[Lead]) -> pd.DataFrame:
  rows = []
  for lead in leads:
    row = _lh_base_row(lead)
    row["وضعیت تماس"] = lead.sdr_call_status or "—"
    row["نام شخص تصمیم‌گیرنده"] = lead.sdr_contact_name or "—"
    rows.append(row)
  columns = [
    "نام کسب و کار",
    "شماره‌های تماس",
    "نوع کسب و کار",
    "منبع",
    "آدرس سایت",
    "تلگرام",
    "اینستاگرام",
    "آدرس محل",
    "وضعیت تماس",
    "نام شخص تصمیم‌گیرنده",
    "توضیحات کلی",
  ]
  return pd.DataFrame(rows, columns=columns) if rows else pd.DataFrame(columns=columns)


def build_setter_department_rows(leads: list[Lead]) -> pd.DataFrame:
  rows = []
  for lead in leads:
    meeting_date, meeting_time = _setter_meeting_parts(lead)
    rows.append(
      {
        "نام کسب و کار": lead.company_name,
        "شماره تماس": _phones_joined(lead),
        "تاریخ جلسه شمسی": meeting_date,
        "ساعت جلسه": meeting_time,
        "نوع جلسه": _setter_meeting_type(lead.setter_meeting_location),
        "وضعیت تایید جلسه": lead.setter_status or "—",
        "یادداشت Setter": lead.setter_notes or "—",
      }
    )
  columns = [
    "نام کسب و کار",
    "شماره تماس",
    "تاریخ جلسه شمسی",
    "ساعت جلسه",
    "نوع جلسه",
    "وضعیت تایید جلسه",
    "یادداشت Setter",
  ]
  return pd.DataFrame(rows, columns=columns) if rows else pd.DataFrame(columns=columns)


def build_closer_department_rows(leads: list[Lead]) -> pd.DataFrame:
  rows = []
  for lead in leads:
    rows.append(
      {
        "نام کسب و کار": lead.company_name,
        "شماره تماس": _phones_joined(lead),
        "وضعیت نهایی جلسه": lead.closer_meeting_status or "—",
        "نتیجه همکاری": lead.closer_cooperation_status or "—",
        "مبلغ قرارداد در صورت موفقیت": _contract_amount(lead),
        "یادداشت Closer": _closer_notes(lead),
      }
    )
  columns = [
    "نام کسب و کار",
    "شماره تماس",
    "وضعیت نهایی جلسه",
    "نتیجه همکاری",
    "مبلغ قرارداد در صورت موفقیت",
    "یادداشت Closer",
  ]
  return pd.DataFrame(rows, columns=columns) if rows else pd.DataFrame(columns=columns)


def _username_label(user) -> str:
  if user and getattr(user, "username", None):
    return user.username
  return "—"


def build_master_rows(leads: list[Lead]) -> pd.DataFrame:
  rows = []
  for lead in leads:
    rows.append(
      {
        "شناسه": lead.id,
        "نام کسب و کار": lead.company_name,
        "شماره تماس اصلی": lead.phone_number,
        "شماره تماس ۲": lead.phone_number_2 or "—",
        "شماره تماس ۳": lead.phone_number_3 or "—",
        "شماره طلایی (اصلی)": lead.phone_primary,
        "نوع کسب و کار": lead.business_type,
        "نوع کسب و کار (سفارشی)": lead.business_type_custom or "—",
        "منبع": lead.source,
        "منبع (سفارشی)": lead.source_custom or "—",
        "آدرس سایت": lead.website or "—",
        "تلگرام": lead.telegram or "—",
        "اینستاگرام": lead.instagram or "—",
        "آدرس محل": lead.address or "—",
        "توضیحات کلی": lead.description or "—",
        "مرحله فعلی": lead.current_stage,
        "وضعیت پایپ‌لاین": lead.pipeline_status,
        "ثبت‌شده توسط": _username_label(lead.created_by),
        "تاریخ ایجاد": format_jalali_datetime(lead.created_at),
        "تاریخ به‌روزرسانی": format_jalali_datetime(lead.updated_at),
        "SDR اختصاص‌یافته": _username_label(lead.assigned_sdr),
        "تاریخ اختصاص SDR": format_jalali_datetime(lead.assigned_sdr_at),
        "وضعیت تماس SDR": lead.sdr_call_status or "—",
        "نتیجه SDR": lead.sdr_result or "—",
        "دلیل رد SDR": lead.sdr_rejection_reason or "—",
        "شدت درد": lead.sdr_pain_severity or "—",
        "قدرت خرید": lead.sdr_buying_power or "—",
        "شخص تماس": lead.sdr_contact_person or "—",
        "نام تصمیم‌گیرنده": lead.sdr_contact_name or "—",
        "سطح علاقه": lead.sdr_interest_level or "—",
        "اقدام بعدی SDR": lead.sdr_next_action or "—",
        "تاریخ پیگیری SDR": format_jalali_date(lead.sdr_followup_date),
        "نوع شماره اشتباه": lead.wrong_number_type or "—",
        "یادداشت شماره اشتباه": lead.wrong_number_notes or "—",
        "خلاصه SDR": lead.sdr_summary or "—",
        "اپراتور SDR": _username_label(lead.sdr_agent),
        "زمان پردازش SDR": format_jalali_datetime(lead.sdr_processed_at),
        "ارجاع به PM": "بله" if lead.sdr_routed_to_pm else "خیر",
        "پروپوزال آماده PM": "بله" if lead.pm_proposal_ready else "خیر",
        "وضعیت پروپوزال": lead.proposal_status,
        "وضعیت Setter": lead.setter_status or "—",
        "زمان جلسه Setter": format_jalali_datetime(lead.setter_meeting_date),
        "مکان جلسه Setter": lead.setter_meeting_location or "—",
        "یادداشت Setter": lead.setter_notes or "—",
        "اپراتور Setter": _username_label(lead.setter_agent),
        "اپراتور PM": _username_label(lead.pm_agent),
        "عنوان پروپوزال": lead.proposal_title or "—",
        "مبلغ پروپوزال": lead.proposal_amount if lead.proposal_amount is not None else "—",
        "جزئیات پروپوزال": lead.proposal_details or "—",
        "تاریخ پروپوزال": format_jalali_date(lead.proposal_date),
        "وضعیت جلسه Closer": lead.closer_meeting_status or "—",
        "نتیجه همکاری Closer": lead.closer_cooperation_status or "—",
        "تاریخ پیگیری Closer": format_jalali_datetime(lead.closer_followup_date),
        "یادداشت Closer": lead.closer_notes or "—",
        "اپراتور Closer": _username_label(lead.closer_agent),
        "نتیجه معامله": lead.deal_outcome or "—",
        "یادداشت بستن معامله": lead.closing_notes or "—",
        "تاریخ بسته‌شدن": format_jalali_datetime(lead.closed_at),
        "حذف توسط ادمین": format_jalali_datetime(lead.admin_deleted_at),
        "حذف‌کننده ادمین": _username_label(lead.admin_deleted_by),
      }
    )
  return pd.DataFrame(rows) if rows else pd.DataFrame()


def sdr_today_leads_query(assigned_sdr_id: int):
  start, end = today_utc_range()

  def _between(column):
    return and_(column >= start, column <= end)

  return Lead.query.filter(
    Lead.assigned_sdr_id == assigned_sdr_id,
    or_(
      _between(Lead.sdr_processed_at),
      _between(Lead.updated_at),
      _between(Lead.assigned_sdr_at),
    ),
  ).order_by(Lead.updated_at.desc())


def export_sdr_daily_xlsx(leads: list[Lead], sdr_username: str) -> tuple[BytesIO, str]:
  df = build_sdr_daily_rows(leads)
  filename = f"Baltazar_SDR_{sdr_username}_{jalali_date_filename()}.xlsx"
  return _dataframe_to_xlsx(df), filename


def export_master_xlsx(leads: list[Lead]) -> tuple[BytesIO, str]:
  df = build_master_rows(leads)
  filename = f"Baltazar_CRM_Master_{jalali_date_filename()}.xlsx"
  return _dataframe_to_xlsx(df), filename


def export_department_xlsx(
  leads: list[Lead], department: str, builder
) -> tuple[BytesIO, str]:
  df = builder(leads)
  filename = f"Baltazar_CRM_{department}_{jalali_date_filename()}.xlsx"
  return _dataframe_to_xlsx(df), filename
