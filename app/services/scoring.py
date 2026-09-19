"""امتیازدهی گیمیفیکیشن."""

from app.extensions import db
from app.models import Lead, User


def award_setter_approval_points(lead: Lead) -> None:
  """
  پس از تأیید جلسه توسط Setter:
  +۱ به LH ثبت‌کننده و +۱ به SDR واجد شرایط.
  """
  if lead.created_by_id:
    lh = db.session.get(User, lead.created_by_id)
    if lh and lh.is_active and lh.role == "lh":
      lh.score = (lh.score or 0) + 1

  sdr_id = lead.assigned_sdr_id or lead.sdr_agent_id
  if sdr_id:
    sdr = db.session.get(User, sdr_id)
    if sdr and sdr.is_active and sdr.role == "sdr":
      sdr.score = (sdr.score or 0) + 1
