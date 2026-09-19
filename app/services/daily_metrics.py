"""محاسبه آمار روزانه داشبورد ادمین."""

from datetime import date

from sqlalchemy import and_, func

from app.extensions import db
from app.models import Lead, User
from app.utils.jalali_dates import jalali_today_label, today_gregorian_date, today_utc_range


def compute_daily_metrics() -> dict:
  start, end = today_utc_range()
  today = today_gregorian_date()

  def _between_dt(column):
    return and_(column >= start, column <= end)

  lh_leads_today = (
    db.session.query(func.count(Lead.id))
    .join(User, Lead.created_by_id == User.id)
    .filter(User.role == "lh", _between_dt(Lead.created_at))
    .scalar()
    or 0
  )

  sdr_success_today = (
    Lead.query.filter(
      Lead.sdr_call_status == "پاسخ داد",
      _between_dt(Lead.sdr_processed_at),
    ).count()
  )

  to_setter_today = (
    Lead.query.filter(
      Lead.sdr_next_action == Lead.SDR_NEXT_ACTION_SETTER,
      Lead.current_stage >= 3,
      _between_dt(Lead.sdr_processed_at),
    ).count()
  )

  wrong_self = (
    Lead.query.filter(
      Lead.sdr_call_status == "شماره اشتباه",
      Lead.wrong_number_type == Lead.WRONG_NUMBER_SELF,
      _between_dt(Lead.sdr_processed_at),
    ).count()
  )
  wrong_owner = (
    Lead.query.filter(
      Lead.sdr_call_status == "شماره اشتباه",
      Lead.wrong_number_type == Lead.WRONG_NUMBER_OWNER,
      _between_dt(Lead.sdr_processed_at),
    ).count()
  )
  wrong_total = wrong_self + wrong_owner

  setter_approved_today = (
    Lead.query.filter(
      Lead.setter_status == Lead.SETTER_STATUS_APPROVED,
      _between_dt(Lead.updated_at),
    ).count()
  )

  closer_held_today = (
    Lead.query.filter(
      Lead.closer_meeting_status == Lead.CLOSER_MEETING_HELD,
      _between_dt(Lead.updated_at),
    ).count()
  )

  proposal_followups_today = (
    Lead.query.filter(
      Lead.sdr_routed_to_pm.is_(True),
      Lead.pm_proposal_ready.is_(True),
      _between_dt(Lead.updated_at),
    ).count()
  )

  sdr_recall_today = Lead.query.filter(Lead.sdr_followup_date == today).count()
  closer_recall_today = (
    db.session.query(func.count(Lead.id))
    .filter(
      Lead.closer_cooperation_status == Lead.CLOSER_COOP_FOLLOWUP,
      func.date(Lead.closer_followup_date) == today,
    )
    .scalar()
    or 0
  )

  rejected_today = (
    Lead.query.filter(
      Lead.sdr_result == Lead.SDR_RESULT_REJECTED,
      _between_dt(Lead.sdr_processed_at),
    ).count()
  )

  return {
    "jalali_date_label": jalali_today_label(),
    "lh_leads_today": lh_leads_today,
    "sdr_success_today": sdr_success_today,
    "to_setter_today": to_setter_today,
    "wrong_numbers_today": wrong_total,
    "wrong_number_self": wrong_self,
    "wrong_number_owner": wrong_owner,
    "setter_approved_today": setter_approved_today,
    "closer_held_today": closer_held_today,
    "proposal_followups_today": proposal_followups_today,
    "sdr_recall_scheduled_today": sdr_recall_today,
    "closer_recall_scheduled_today": closer_recall_today,
    "recall_followups_total": sdr_recall_today + closer_recall_today,
    "rejected_today": rejected_today,
  }
