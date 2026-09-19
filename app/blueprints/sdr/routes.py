from flask import abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from app.blueprints.sdr import bp
from app.extensions import db
from app.forms.sdr_forms import SDRLeadForm, _is_empty_choice
from app.models import Lead, utcnow
from app.services.excel_export import export_sdr_daily_xlsx, sdr_today_leads_query
from app.services.lead_workflow import return_lead_to_lh_wrong_number
from app.services.sdr_queue import sort_sdr_daily_queue
from app.utils.decorators import role_required
from app.utils.jalali_dates import format_jalali_date


def _sdr_assigned_filter():
  return Lead.assigned_sdr_id == current_user.id


def _apply_sdr_form_to_lead(lead: Lead, form: SDRLeadForm) -> None:
  lead.sdr_call_status = form.sdr_call_status.data
  lead.sdr_agent_id = current_user.id
  lead.sdr_processed_at = utcnow()
  lead.updated_at = utcnow()

  if form.call_was_wrong_number:
    lead.wrong_number_type = form.wrong_number_type.data
    lead.wrong_number_notes = (form.wrong_number_notes.data or "").strip()
    lead.sdr_result = None
    lead.sdr_rejection_reason = None
    lead.sdr_pain_severity = None
    lead.sdr_buying_power = None
    lead.sdr_contact_person = None
    lead.sdr_contact_name = None
    lead.sdr_interest_level = None
    lead.sdr_next_action = None
    lead.sdr_followup_date = None
    lead.sdr_summary = None
    return_lead_to_lh_wrong_number(lead)
    return

  if form.call_was_unanswered:
    lead.wrong_number_type = None
    lead.wrong_number_notes = None
    lead.sdr_result = None
    lead.sdr_rejection_reason = None
    lead.sdr_pain_severity = None
    lead.sdr_buying_power = None
    lead.sdr_contact_person = None
    lead.sdr_contact_name = None
    lead.sdr_interest_level = None
    lead.sdr_summary = (form.sdr_summary.data or "").strip() or None
    lead.sdr_followup_date = form.sdr_followup_date.data

    next_action = form.sdr_next_action.data
    if _is_empty_choice(next_action):
      lead.sdr_next_action = None
      lead.current_stage = 2
      lead.pipeline_status = "active"
      return

    lead.sdr_next_action = next_action
    if next_action == Lead.SDR_NEXT_ACTION_DELETE:
      lead.current_stage = 2
      lead.pipeline_status = "disqualified"
    elif next_action == Lead.SDR_NEXT_ACTION_FOLLOWUP:
      lead.sdr_result = Lead.SDR_RESULT_RECALL
      lead.current_stage = 2
      lead.pipeline_status = "active"
    else:
      lead.current_stage = 2
      lead.pipeline_status = "active"
    return

  lead.wrong_number_type = None
  lead.wrong_number_notes = None
  lead.sdr_result = form.sdr_result.data
  lead.sdr_rejection_reason = (
    (form.sdr_rejection_reason.data or "").strip() or None
  )
  lead.sdr_pain_severity = form.sdr_pain_severity.data
  lead.sdr_buying_power = form.sdr_buying_power.data
  lead.sdr_contact_person = form.sdr_contact_person.data
  lead.sdr_contact_name = (form.sdr_contact_name.data or "").strip() or None
  lead.sdr_interest_level = form.sdr_interest_level.data
  lead.sdr_next_action = form.sdr_next_action.data
  lead.sdr_followup_date = form.sdr_followup_date.data
  lead.sdr_summary = (form.sdr_summary.data or "").strip()

  next_action = form.sdr_next_action.data

  if next_action == Lead.SDR_NEXT_ACTION_SETTER:
    lead.current_stage = 3
    lead.pipeline_status = "active"
    lead.sdr_routed_to_pm = False
  elif next_action == Lead.SDR_NEXT_ACTION_PROPOSAL:
    lead.current_stage = 4
    lead.pipeline_status = "active"
    lead.sdr_routed_to_pm = True
    lead.pm_proposal_ready = False
    lead.proposal_status = "pending"
  elif next_action == Lead.SDR_NEXT_ACTION_DELETE:
    lead.current_stage = 2
    lead.pipeline_status = "disqualified"
  elif next_action == Lead.SDR_NEXT_ACTION_FOLLOWUP:
    lead.current_stage = 2
    lead.pipeline_status = "active"
  else:
    lead.current_stage = 2
    lead.pipeline_status = "active"

  if form.sdr_result.data == Lead.SDR_RESULT_REJECTED and next_action != Lead.SDR_NEXT_ACTION_SETTER:
    lead.pipeline_status = "disqualified"


def _populate_form_from_lead(form: SDRLeadForm, lead: Lead) -> None:
  form.sdr_call_status.data = lead.sdr_call_status or ""
  form.wrong_number_type.data = lead.wrong_number_type or ""
  form.wrong_number_notes.data = lead.wrong_number_notes or ""
  form.sdr_result.data = lead.sdr_result or ""
  form.sdr_rejection_reason.data = lead.sdr_rejection_reason or ""
  form.sdr_pain_severity.data = lead.sdr_pain_severity or ""
  form.sdr_buying_power.data = lead.sdr_buying_power or ""
  form.sdr_contact_person.data = lead.sdr_contact_person or ""
  form.sdr_contact_name.data = lead.sdr_contact_name or ""
  form.sdr_interest_level.data = lead.sdr_interest_level or ""
  form.sdr_next_action.data = lead.sdr_next_action or ""
  form.sdr_followup_date.data = lead.sdr_followup_date
  form.sdr_summary.data = lead.sdr_summary or ""


def _ensure_sdr_owns_lead(lead: Lead) -> bool:
  if lead.assigned_sdr_id != current_user.id:
    return False
  return True


@bp.route("/")
@role_required("sdr")
def dashboard():
  assigned = _sdr_assigned_filter()

  new_inbound_raw = (
    Lead.query.options(joinedload(Lead.created_by))
    .filter(
      assigned,
      Lead.active_only(),
      Lead.current_stage == 2,
      Lead.pipeline_status == "active",
      or_(Lead.sdr_next_action.is_(None), Lead.sdr_next_action == ""),
    )
    .all()
  )
  new_inbound = sort_sdr_daily_queue(new_inbound_raw)

  followup_leads = (
    Lead.query.options(joinedload(Lead.created_by))
    .filter(
      assigned,
      Lead.current_stage == 2,
      Lead.sdr_next_action != Lead.SDR_NEXT_ACTION_DELETE,
      Lead.sdr_next_action.isnot(None),
      Lead.sdr_next_action != "",
      or_(
        Lead.sdr_result == Lead.SDR_RESULT_RECALL,
        Lead.sdr_next_action == Lead.SDR_NEXT_ACTION_FOLLOWUP,
      ),
    )
    .order_by(Lead.sdr_followup_date.asc().nullslast(), Lead.updated_at.desc())
    .all()
  )

  deleted_leads = (
    Lead.query.options(joinedload(Lead.sdr_agent))
    .filter(assigned, Lead.sdr_next_action == Lead.SDR_NEXT_ACTION_DELETE)
    .order_by(Lead.updated_at.desc())
    .limit(50)
    .all()
  )

  proposal_followup = (
    Lead.query.filter(
      assigned,
      Lead.sdr_routed_to_pm.is_(True),
      Lead.pm_proposal_ready.is_(True),
    )
    .order_by(Lead.updated_at.desc())
    .all()
  )

  return render_template(
    "sdr/dashboard.html",
    new_inbound=new_inbound,
    followup_leads=followup_leads,
    deleted_leads=deleted_leads,
    proposal_followup=proposal_followup,
    format_jalali_date=format_jalali_date,
  )


@bp.route("/lead/<int:lead_id>/process", methods=["GET", "POST"])
@role_required("sdr")
def process_lead(lead_id):
  lead = (
    Lead.query.options(joinedload(Lead.created_by))
    .filter_by(id=lead_id)
    .first()
  )
  if not lead:
    abort(404)

  if not _ensure_sdr_owns_lead(lead):
    flash("این سرنخ به شما اختصاص داده نشده است.", "warning")
    return redirect(url_for("sdr.dashboard"))

  form = SDRLeadForm()
  is_followup = lead.is_sdr_followup_queue

  if lead.is_admin_deleted or lead.is_sdr_archived:
    flash("این سرنخ حذف شده و قابل ویرایش نیست.", "warning")
    return redirect(url_for("sdr.dashboard"))

  can_process = (
    lead.current_stage == 2
    or is_followup
    or lead.needs_sdr_proposal_followup
  )
  if not can_process:
    flash("این سرنخ در صف SDR نیست.", "warning")
    return redirect(url_for("sdr.dashboard"))

  if form.validate_on_submit():
    _apply_sdr_form_to_lead(lead, form)
    db.session.commit()

    if form.call_was_wrong_number:
      flash(
        "شماره اشتباه ثبت شد و سرنخ برای اصلاح به شکارچی سرنخ (LH) بازگردانده شد.",
        "success",
      )
      return redirect(url_for("sdr.dashboard"))

    if form.call_was_unanswered:
      flash("وضعیت تماس بدون پاسخ ثبت شد.", "success")
      return redirect(url_for("sdr.dashboard"))

    if lead.sdr_next_action == Lead.SDR_NEXT_ACTION_SETTER:
      flash("سرنخ با موفقیت به تیم ستر منتقل شد.", "success")
    elif lead.sdr_next_action == Lead.SDR_NEXT_ACTION_PROPOSAL:
      flash("سرنخ به بخش PM (پروپوزال) ارسال شد.", "success")
    elif lead.sdr_next_action == Lead.SDR_NEXT_ACTION_DELETE:
      flash("سرنخ در لیست حذف‌شده‌ها آرشیو شد.", "success")
    elif lead.sdr_next_action == Lead.SDR_NEXT_ACTION_FOLLOWUP:
      flash("تماس بعدی ثبت شد و در لیست پیگیری قرار گرفت.", "success")
    else:
      flash("اطلاعات تماس با موفقیت ذخیره شد.", "success")
    return redirect(url_for("sdr.dashboard"))

  if request.method == "GET" and (lead.sdr_call_status or is_followup):
    _populate_form_from_lead(form, lead)

  return render_template(
    "sdr/process_lead.html",
    form=form,
    lead=lead,
    is_followup=is_followup,
  )


@bp.route("/export/today-excel")
@role_required("sdr")
def export_today_excel():
  leads = sdr_today_leads_query(current_user.id).all()
  buffer, filename = export_sdr_daily_xlsx(leads, current_user.username)
  return send_file(
    buffer,
    mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    as_attachment=True,
    download_name=filename,
  )
