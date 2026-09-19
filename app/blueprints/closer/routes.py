from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from app.blueprints.closer import bp
from app.extensions import db
from app.forms.closer_forms import CloserForm
from app.models import Lead, utcnow
from app.utils.decorators import role_required


def _closer_lead_options():
  return [
    joinedload(Lead.created_by),
    joinedload(Lead.sdr_agent),
    joinedload(Lead.setter_agent),
    joinedload(Lead.closer_agent),
  ]


def _apply_closer_form_to_lead(lead: Lead, form: CloserForm) -> None:
  lead.closer_meeting_status = form.closer_meeting_status.data
  lead.closer_cooperation_status = form.closer_cooperation_status.data
  lead.closer_followup_date = form.closer_followup_date.data
  lead.closer_notes = (form.closer_notes.data or "").strip()
  lead.closing_notes = lead.closer_notes
  lead.closer_agent_id = current_user.id
  lead.updated_at = utcnow()

  coop = form.closer_cooperation_status.data

  if coop == Lead.CLOSER_COOP_SUCCESS:
    lead.pipeline_status = "closed_won"
    lead.deal_outcome = "won"
    lead.current_stage = 5
    lead.closed_at = utcnow()
    lead.closer_followup_date = None
  elif coop == Lead.CLOSER_COOP_REJECT:
    lead.pipeline_status = "closed_lost"
    lead.deal_outcome = "lost"
    lead.current_stage = 5
    lead.closed_at = utcnow()
    lead.closer_followup_date = None
  elif coop == Lead.CLOSER_COOP_FOLLOWUP:
    lead.pipeline_status = "active"
    lead.current_stage = 5
    lead.deal_outcome = None
    lead.closed_at = None
  else:
    lead.pipeline_status = "active"
    lead.current_stage = 5


def _populate_form_from_lead(form: CloserForm, lead: Lead) -> None:
  form.closer_meeting_status.data = lead.closer_meeting_status or ""
  form.closer_cooperation_status.data = lead.closer_cooperation_status or ""
  form.closer_followup_date.data = lead.closer_followup_date
  form.closer_notes.data = lead.closer_notes or lead.closing_notes or ""


@bp.route("/")
@role_required("closer")
def dashboard():
  base = [Lead.current_stage == 5, Lead.pipeline_status == "active"]

  new_referrals = (
    Lead.query.options(*_closer_lead_options())
    .filter(
      *base,
      or_(Lead.closer_cooperation_status.is_(None), Lead.closer_cooperation_status == ""),
    )
    .order_by(Lead.setter_meeting_date.asc().nullslast(), Lead.updated_at.desc())
    .all()
  )

  followup_leads = (
    Lead.query.options(*_closer_lead_options())
    .filter(*base, Lead.closer_cooperation_status == Lead.CLOSER_COOP_FOLLOWUP)
    .order_by(Lead.closer_followup_date.asc().nullslast(), Lead.updated_at.desc())
    .all()
  )

  return render_template(
    "closer/dashboard.html",
    new_referrals=new_referrals,
    followup_leads=followup_leads,
  )


@bp.route("/lead/<int:lead_id>/process", methods=["GET", "POST"])
@role_required("closer")
def process_lead(lead_id):
  lead = (
    Lead.query.options(*_closer_lead_options())
    .filter_by(id=lead_id)
    .first()
  )
  if not lead:
    abort(404)

  if lead.is_deal_closed and not lead.is_closer_followup_queue:
    flash("این معامله بسته شده و قابل ویرایش نیست.", "warning")
    return redirect(url_for("closer.dashboard"))

  is_followup = lead.is_closer_followup_queue
  can_process = lead.current_stage == 5 and (
    is_followup
    or lead.pipeline_status == "active"
  )

  if not can_process:
    flash("این سرنخ در صف کلوزر نیست.", "warning")
    return redirect(url_for("closer.dashboard"))

  form = CloserForm()
  if form.validate_on_submit():
    _apply_closer_form_to_lead(lead, form)
    db.session.commit()

    if lead.closer_cooperation_status == Lead.CLOSER_COOP_SUCCESS:
      flash(f"معامله «{lead.company_name}» با موفقیت بسته شد (برنده).", "success")
    elif lead.closer_cooperation_status == Lead.CLOSER_COOP_REJECT:
      flash(f"معامله «{lead.company_name}» ناموفق ثبت شد (بازنده).", "success")
    elif lead.closer_cooperation_status == Lead.CLOSER_COOP_FOLLOWUP:
      flash(
        f"پیگیری مجدد برای «{lead.company_name}» ثبت شد.",
        "success",
      )
    else:
      flash("نتیجه جلسه ذخیره شد.", "success")
    return redirect(url_for("closer.dashboard"))

  if request.method == "GET" and lead.closer_meeting_status:
    _populate_form_from_lead(form, lead)

  return render_template(
    "closer/process_lead.html",
    form=form,
    lead=lead,
    is_followup=is_followup,
  )
