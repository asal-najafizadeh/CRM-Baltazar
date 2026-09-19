from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from app.blueprints.lh import bp
from app.extensions import db
from app.forms.lh_forms import LHLeadForm, LHWrongNumberFixForm
from app.models import Lead
from app.services.lead_workflow import clear_sdr_fields_for_lh_resubmit, send_lead_to_sdr_pool
from app.utils.decorators import role_required
from app.utils.jalali_dates import today_utc_range
from app.utils.phone import (
  DUPLICATE_PHONE_MESSAGE,
  any_phone_exists,
  normalize_phone_list,
)


def _to_persian_digits(value) -> str:
  return str(value).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def _lh_lead_counts() -> dict:
  start, end = today_utc_range()
  today_count = (
    Lead.query.filter(
      Lead.created_by_id == current_user.id,
      Lead.active_only(),
      Lead.created_at >= start,
      Lead.created_at <= end,
    ).count()
  )
  total_count = (
    Lead.query.filter(
      Lead.created_by_id == current_user.id,
      Lead.active_only(),
    ).count()
  )
  return {
    "lh_today_count": today_count,
    "lh_total_count": total_count,
    "to_persian_digits": _to_persian_digits,
  }


def _phones_from_lh_form(form) -> list[str]:
  backup = request.form.getlist("phone_backup[]")
  return normalize_phone_list([form.phone_number.data] + backup)


def _lh_dashboard_lists():
  recent_leads = (
    Lead.query.options(
      joinedload(Lead.created_by),
      joinedload(Lead.assigned_sdr),
      joinedload(Lead.sdr_agent),
    )
    .filter_by(created_by_id=current_user.id)
    .filter(Lead.active_only())
    .order_by(Lead.created_at.desc())
    .limit(20)
    .all()
  )

  followup_needed_leads = (
    Lead.query.options(joinedload(Lead.assigned_sdr), joinedload(Lead.sdr_agent))
    .filter_by(created_by_id=current_user.id)
    .filter(Lead.active_only())
    .filter(
      or_(
        Lead.sdr_call_status == Lead.SDR_CALL_WRONG_NUMBER,
        Lead.current_stage == 1,
      ),
    )
    .order_by(Lead.updated_at.desc())
    .all()
  )

  archived_leads = (
    Lead.query.options(
      joinedload(Lead.sdr_agent),
      joinedload(Lead.setter_agent),
      joinedload(Lead.closer_agent),
      joinedload(Lead.pm_agent),
      joinedload(Lead.admin_deleted_by),
    )
    .filter_by(created_by_id=current_user.id)
    .filter(
      or_(
        Lead.admin_deleted_at.isnot(None),
        Lead.pipeline_status == "disqualified",
        Lead.pipeline_status == "closed_lost",
        Lead.sdr_next_action == Lead.SDR_NEXT_ACTION_DELETE,
        Lead.setter_status == Lead.SETTER_STATUS_REJECTED,
        Lead.closer_cooperation_status == Lead.CLOSER_COOP_REJECT,
      )
    )
    .order_by(Lead.updated_at.desc())
    .all()
  )

  archived_rows = []
  for lead in archived_leads:
    deleted_by = "نامشخص"
    note = None
    if lead.is_admin_deleted:
      deleted_by = f"ادمین ({lead.admin_deleted_by_username})"
      note = "حذف توسط پنل مدیریت"
    elif lead.sdr_next_action == Lead.SDR_NEXT_ACTION_DELETE or lead.sdr_result == Lead.SDR_RESULT_REJECTED:
      deleted_by = f"SDR ({lead.sdr_agent_username})"
      note = lead.sdr_rejection_reason or lead.sdr_summary
    elif lead.setter_status == Lead.SETTER_STATUS_REJECTED:
      deleted_by = f"Setter ({lead.setter_agent_username})"
      note = lead.setter_notes
    elif lead.closer_cooperation_status == Lead.CLOSER_COOP_REJECT:
      deleted_by = f"Closer ({lead.closer_agent_username})"
      note = lead.closer_notes or lead.closing_notes
    elif lead.pipeline_status == "closed_lost":
      deleted_by = "مدیریت نهایی فروش"
      note = lead.closing_notes
    archived_rows.append(
      {"lead": lead, "deleted_by": deleted_by, "note": note or "—"}
    )

  return {
    "recent_leads": recent_leads,
    "followup_needed_leads": followup_needed_leads,
    "archived_rows": archived_rows,
    **_lh_lead_counts(),
  }


@bp.route("/", methods=["GET", "POST"])
@role_required("lh")
def dashboard():
  form = LHLeadForm()
  lists = _lh_dashboard_lists()

  if form.validate_on_submit():
    phones = _phones_from_lh_form(form)
    if not phones:
      flash("حداقل یک شماره تماس اصلی الزامی است.", "danger")
      return render_template("lh/dashboard.html", form=form, **lists)

    duplicate = any_phone_exists(phones)
    if duplicate:
      flash(DUPLICATE_PHONE_MESSAGE, "danger")
      return render_template("lh/dashboard.html", form=form, **lists)

    source = form.source.data
    source_custom = (form.source_custom.data or "").strip() or None
    business_type = form.business_type.data
    business_type_custom = (form.business_type_custom.data or "").strip() or None

    lead = Lead(
      company_name=form.company_name.data.strip(),
      phone_number=phones[0],
      phone_number_2=phones[1] if len(phones) > 1 else None,
      phone_number_3=phones[2] if len(phones) > 2 else None,
      phone_primary=1,
      business_type=business_type,
      business_type_custom=business_type_custom,
      source=source,
      source_custom=source_custom,
      website=(form.website.data or "").strip() or None,
      telegram=(form.telegram.data or "").strip() or None,
      instagram=(form.instagram.data or "").strip() or None,
      address=(form.address.data or "").strip() or None,
      description=(form.description.data or "").strip() or None,
      current_stage=2,
      pipeline_status="active",
    )
    lead.created_by_id = current_user.id
    send_lead_to_sdr_pool(lead)
    db.session.add(lead)
    db.session.commit()
    flash(
      "اطلاعات کسب و کار با موفقیت ثبت شد و در صف توزیع SDR قرار گرفت.",
      "success",
    )
    return redirect(url_for("lh.dashboard"))

  return render_template("lh/dashboard.html", form=form, **lists)


@bp.route("/lead/<int:lead_id>/fix-wrong-number", methods=["GET", "POST"])
@role_required("lh")
def fix_wrong_number(lead_id):
  lead = Lead.query.filter_by(id=lead_id, created_by_id=current_user.id).first()
  if not lead:
    abort(404)

  if lead.sdr_call_status != Lead.SDR_CALL_WRONG_NUMBER or lead.current_stage != 1:
    flash("این سرنخ در لیست اصلاح شماره نیست.", "warning")
    return redirect(url_for("lh.dashboard"))

  form = LHWrongNumberFixForm()
  form._exclude_lead_id = lead.id
  if form.validate_on_submit():
    lead.phone_number = form.phone_number.data.strip()
    clear_sdr_fields_for_lh_resubmit(lead)
    send_lead_to_sdr_pool(lead)
    db.session.commit()
    flash(
      f"شماره «{lead.company_name}» اصلاح شد و مجدداً در صف توزیع SDR قرار گرفت.",
      "success",
    )
    return redirect(url_for("lh.dashboard"))

  if not form.is_submitted():
    form.phone_number.data = lead.phone_number

  return render_template(
    "lh/fix_wrong_number.html",
    form=form,
    lead=lead,
  )


@bp.route("/leads/new")
@role_required("lh")
def new_lead():
  return redirect(url_for("lh.dashboard"))
