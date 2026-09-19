from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from app.blueprints.setter import bp
from app.extensions import db
from app.forms.setter_forms import SetterForm
from app.models import Lead, utcnow
from app.services.scoring import award_setter_approval_points
from app.utils.decorators import role_required


def _setter_base_filter():
  return [
    Lead.sdr_next_action == Lead.SDR_NEXT_ACTION_SETTER,
    Lead.pipeline_status == "active",
  ]


def _apply_setter_form_to_lead(lead: Lead, form: SetterForm) -> bool:
  """اعمال فرم؛ در صورت تأیید تازه جلسه، True برمی‌گرداند (برای امتیاز)."""
  previous_status = lead.setter_status
  lead.setter_status = form.setter_status.data
  lead.setter_meeting_date = form.setter_meeting_date.data
  lead.setter_meeting_location = (form.setter_meeting_location.data or "").strip() or None
  lead.setter_notes = (form.setter_notes.data or "").strip() or None
  lead.setter_agent_id = current_user.id
  lead.updated_at = utcnow()

  status = form.setter_status.data

  if status == Lead.SETTER_STATUS_APPROVED:
    lead.current_stage = 5
    lead.pipeline_status = "active"
  elif status == Lead.SETTER_STATUS_REJECTED:
    lead.current_stage = 3
    lead.pipeline_status = "disqualified"
  elif status == Lead.SETTER_STATUS_UNCERTAIN:
    lead.current_stage = 3
    lead.pipeline_status = "active"

  return (
    status == Lead.SETTER_STATUS_APPROVED
    and previous_status != Lead.SETTER_STATUS_APPROVED
  )


def _populate_form_from_lead(form: SetterForm, lead: Lead) -> None:
  form.setter_status.data = lead.setter_status or ""
  form.setter_meeting_date.data = lead.setter_meeting_date
  form.setter_meeting_location.data = lead.setter_meeting_location or ""
  form.setter_notes.data = lead.setter_notes or ""


@bp.route("/")
@role_required("setter")
def dashboard():
  base = _setter_base_filter()

  new_inbound = (
    Lead.query.options(joinedload(Lead.sdr_agent), joinedload(Lead.created_by))
    .filter(
      *base,
      Lead.current_stage == 3,
      or_(Lead.setter_status.is_(None), Lead.setter_status == ""),
    )
    .order_by(Lead.updated_at.desc())
    .all()
  )

  followup_leads = (
    Lead.query.options(joinedload(Lead.sdr_agent), joinedload(Lead.created_by))
    .filter(
      *base,
      Lead.current_stage == 3,
      Lead.setter_status == Lead.SETTER_STATUS_UNCERTAIN,
    )
    .order_by(Lead.setter_meeting_date.asc().nullslast(), Lead.updated_at.desc())
    .all()
  )

  rejected_leads = (
    Lead.query.options(joinedload(Lead.setter_agent), joinedload(Lead.sdr_agent))
    .filter(Lead.setter_status == Lead.SETTER_STATUS_REJECTED)
    .order_by(Lead.updated_at.desc())
    .limit(50)
    .all()
  )

  return render_template(
    "setter/dashboard.html",
    new_inbound=new_inbound,
    followup_leads=followup_leads,
    rejected_leads=rejected_leads,
  )


@bp.route("/lead/<int:lead_id>/process", methods=["GET", "POST"])
@role_required("setter")
def process_lead(lead_id):
  lead = (
    Lead.query.options(joinedload(Lead.sdr_agent), joinedload(Lead.created_by))
    .filter_by(id=lead_id)
    .first()
  )
  if not lead:
    abort(404)

  if lead.is_setter_rejected:
    flash("این سرنخ کنسل/حذف شده و قابل ویرایش نیست.", "warning")
    return redirect(url_for("setter.dashboard"))

  is_followup = lead.is_setter_followup_queue
  can_process = (
    lead.sdr_next_action == Lead.SDR_NEXT_ACTION_SETTER
    and (
      lead.current_stage == 3
      or is_followup
      or not lead.setter_status
    )
    and lead.current_stage != 5
  )

  if not can_process and lead.current_stage == 5:
    flash("این سرنخ قبلاً به کلوزر منتقل شده است.", "info")
    return redirect(url_for("setter.dashboard"))

  if not can_process:
    flash("این سرنخ در صف ستر نیست.", "warning")
    return redirect(url_for("setter.dashboard"))

  form = SetterForm()
  if form.validate_on_submit():
    newly_approved = _apply_setter_form_to_lead(lead, form)
    if newly_approved:
      award_setter_approval_points(lead)
    db.session.commit()

    if lead.setter_status == Lead.SETTER_STATUS_APPROVED:
      msg = (
        f"جلسه «{lead.company_name}» تأیید شد و به تیم کلوزر (مرحله ۵) منتقل گردید."
      )
      if newly_approved:
        msg += " امتیاز +۱ به LH و SDR مربوطه تعلق گرفت."
      flash(msg, "success")
    elif lead.setter_status == Lead.SETTER_STATUS_REJECTED:
      flash(f"جلسه «{lead.company_name}» رد و در لیست کنسل‌شده‌ها ثبت شد.", "success")
    elif lead.setter_status == Lead.SETTER_STATUS_UNCERTAIN:
      flash(
        f"«{lead.company_name}» در لیست پیگیری‌های معلق قرار گرفت.",
        "success",
      )
    else:
      flash("اطلاعات با موفقیت ذخیره شد.", "success")
    return redirect(url_for("setter.dashboard"))

  if request.method == "GET" and lead.setter_status:
    _populate_form_from_lead(form, lead)

  return render_template(
    "setter/process_lead.html",
    form=form,
    lead=lead,
    is_followup=is_followup,
  )


@bp.route("/lead/<int:lead_id>")
@role_required("setter")
def lead_handover(lead_id):
  return redirect(url_for("setter.process_lead", lead_id=lead_id))
