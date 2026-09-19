from flask import current_app, flash, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import current_user
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import joinedload

from app.blueprints.admin import bp
from app.extensions import db
from app.forms.admin_forms import (
  DistributeBacklogLeadsForm,
  DistributeLeadsForm,
  ExcelBulkImportForm,
  LeadEditForm,
  UserEditForm,
  UserForm,
)
from app.services.excel_import import import_leads_from_excel
from app.models import Lead, User, utcnow
from app.services.daily_metrics import compute_daily_metrics
from app.services.excel_export import (
  build_closer_department_rows,
  build_sdr_department_rows,
  build_setter_department_rows,
  export_department_xlsx,
  export_master_xlsx,
)
from app.services.user_analytics import compute_employees_daily_report, compute_user_performance
from app.utils.jalali_dates import jalali_today_label, today_gregorian_date, today_utc_range
from app.utils.decorators import role_required


def _to_persian_digits(value) -> str:
  text = str(value)
  return text.translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def _metric_subtitle(today_count: int) -> str:
  return f"امروز ({_to_persian_digits(jalali_today_label())}): +{_to_persian_digits(today_count)}"


def _compute_hybrid_metrics() -> list[dict]:
  start, end = today_utc_range()
  today = today_gregorian_date()

  def _between_dt(column):
    return and_(column >= start, column <= end)

  lh_total = (
    db.session.query(func.count(Lead.id))
    .join(User, Lead.created_by_id == User.id)
    .filter(User.role == "lh")
    .scalar()
    or 0
  )
  lh_today = (
    db.session.query(func.count(Lead.id))
    .join(User, Lead.created_by_id == User.id)
    .filter(User.role == "lh", _between_dt(Lead.created_at))
    .scalar()
    or 0
  )

  sdr_success_total = Lead.query.filter(Lead.sdr_call_status == "پاسخ داد").count()
  sdr_success_today = Lead.query.filter(
    Lead.sdr_call_status == "پاسخ داد",
    _between_dt(Lead.sdr_processed_at),
  ).count()

  to_setter_total = Lead.query.filter(
    Lead.sdr_next_action == Lead.SDR_NEXT_ACTION_SETTER,
    Lead.current_stage >= 3,
  ).count()
  to_setter_today = Lead.query.filter(
    Lead.sdr_next_action == Lead.SDR_NEXT_ACTION_SETTER,
    Lead.current_stage >= 3,
    _between_dt(Lead.sdr_processed_at),
  ).count()

  wrong_self_total = Lead.query.filter(
    Lead.sdr_call_status == Lead.SDR_CALL_WRONG_NUMBER,
    Lead.wrong_number_type == Lead.WRONG_NUMBER_SELF,
  ).count()
  wrong_owner_total = Lead.query.filter(
    Lead.sdr_call_status == Lead.SDR_CALL_WRONG_NUMBER,
    Lead.wrong_number_type == Lead.WRONG_NUMBER_OWNER,
  ).count()
  wrong_self_today = Lead.query.filter(
    Lead.sdr_call_status == Lead.SDR_CALL_WRONG_NUMBER,
    Lead.wrong_number_type == Lead.WRONG_NUMBER_SELF,
    _between_dt(Lead.sdr_processed_at),
  ).count()
  wrong_owner_today = Lead.query.filter(
    Lead.sdr_call_status == Lead.SDR_CALL_WRONG_NUMBER,
    Lead.wrong_number_type == Lead.WRONG_NUMBER_OWNER,
    _between_dt(Lead.sdr_processed_at),
  ).count()

  setter_done_total = Lead.query.filter(
    Lead.setter_status == Lead.SETTER_STATUS_APPROVED
  ).count()
  setter_done_today = Lead.query.filter(
    Lead.setter_status == Lead.SETTER_STATUS_APPROVED,
    _between_dt(Lead.updated_at),
  ).count()

  closer_held_total = Lead.query.filter(
    Lead.closer_meeting_status == Lead.CLOSER_MEETING_HELD
  ).count()
  closer_held_today = Lead.query.filter(
    Lead.closer_meeting_status == Lead.CLOSER_MEETING_HELD,
    _between_dt(Lead.updated_at),
  ).count()

  proposal_followups_total = Lead.query.filter(
    Lead.sdr_routed_to_pm.is_(True),
    Lead.pm_proposal_ready.is_(True),
  ).count()
  proposal_followups_today = Lead.query.filter(
    Lead.sdr_routed_to_pm.is_(True),
    Lead.pm_proposal_ready.is_(True),
    _between_dt(Lead.updated_at),
  ).count()

  sdr_recall_total = Lead.query.filter(Lead.sdr_followup_date.isnot(None)).count()
  closer_recall_total = Lead.query.filter(Lead.closer_followup_date.isnot(None)).count()
  sdr_recall_today = Lead.query.filter(Lead.sdr_followup_date == today).count()
  closer_recall_today = (
    db.session.query(func.count(Lead.id))
    .filter(
      Lead.closer_followup_date.isnot(None),
      func.date(Lead.closer_followup_date) == today,
    )
    .scalar()
    or 0
  )

  rejected_total = Lead.query.filter(Lead.sdr_result == Lead.SDR_RESULT_REJECTED).count()
  rejected_today = Lead.query.filter(
    Lead.sdr_result == Lead.SDR_RESULT_REJECTED,
    _between_dt(Lead.sdr_processed_at),
  ).count()

  return [
    {
      "title": "کل شماره‌های ثبت شده LH",
      "total": lh_total,
      "today": lh_today,
      "color": "text-indigo-700",
      "endpoint": None,
    },
    {
      "title": "کل تماس‌های موفق SDR",
      "total": sdr_success_total,
      "today": sdr_success_today,
      "color": "text-emerald-700",
      "endpoint": "admin.sdr_success_calls",
    },
    {
      "title": "ارجاع شده به Setter",
      "total": to_setter_total,
      "today": to_setter_today,
      "color": "text-sky-700",
      "endpoint": "admin.setter_performance",
    },
    {
      "title": "شماره‌های اشتباه",
      "total": wrong_self_total + wrong_owner_total,
      "today": wrong_self_today + wrong_owner_today,
      "color": "text-rose-700",
      "endpoint": None,
      "breakdown_total": f"خود شماره: {_to_persian_digits(wrong_self_total)} · صاحب شماره: {_to_persian_digits(wrong_owner_total)}",
      "breakdown_today": f"امروز — خود شماره: {_to_persian_digits(wrong_self_today)} · صاحب شماره: {_to_persian_digits(wrong_owner_today)}",
    },
    {
      "title": "جلسات نهایی شده Setter",
      "total": setter_done_total,
      "today": setter_done_today,
      "color": "text-violet-700",
      "endpoint": "admin.setter_performance",
    },
    {
      "title": "جلسات حضوری برگزار شده (Closer)",
      "total": closer_held_total,
      "today": closer_held_today,
      "color": "text-teal-700",
      "endpoint": "admin.closer_meetings",
    },
    {
      "title": "کل پیگیری‌های امروز",
      "total": proposal_followups_total + sdr_recall_total + closer_recall_total,
      "today": proposal_followups_today + sdr_recall_today + closer_recall_today,
      "color": "text-amber-700",
      "endpoint": "admin.followups",
      "breakdown_total": (
        "پروپوزال: "
        f"{_to_persian_digits(proposal_followups_total)} · "
        "تماس مجدد: "
        f"{_to_persian_digits(sdr_recall_total + closer_recall_total)}"
      ),
      "breakdown_today": (
        "امروز — پروپوزال: "
        f"{_to_persian_digits(proposal_followups_today)} · "
        "تماس مجدد: "
        f"{_to_persian_digits(sdr_recall_today + closer_recall_today)}"
      ),
    },
    {
      "title": "تماس‌های رد شده در بخش SDR",
      "total": rejected_total,
      "today": rejected_today,
      "color": "text-red-700",
      "endpoint": "admin.archived_leads",
    },
  ]


def _agent_choices(role: str) -> list[tuple[int, str]]:
  users = User.query.filter_by(role=role).order_by(User.username.asc()).all()
  return [(0, "— بدون اختصاص —")] + [(u.id, u.username) for u in users]


def _apply_optional_fk(value: int) -> int | None:
  return value if value and value > 0 else None


def _lead_detail_options():
  return (
    joinedload(Lead.created_by),
    joinedload(Lead.assigned_sdr),
    joinedload(Lead.sdr_agent),
    joinedload(Lead.setter_agent),
    joinedload(Lead.closer_agent),
    joinedload(Lead.pm_agent),
    joinedload(Lead.admin_deleted_by),
  )


def _archived_leads_filter():
  """لیدهای حذف/بایگانی‌شده (شامل حذف ادمین)."""
  return or_(
    Lead.admin_deleted_at.isnot(None),
    Lead.sdr_next_action == Lead.SDR_NEXT_ACTION_DELETE,
    Lead.sdr_result == Lead.SDR_RESULT_REJECTED,
    Lead.pipeline_status == "disqualified",
    Lead.pipeline_status == "closed_lost",
    Lead.setter_status == Lead.SETTER_STATUS_REJECTED,
    Lead.closer_cooperation_status == Lead.CLOSER_COOP_REJECT,
  )


@bp.route("/")
@role_required("admin")
def dashboard():
  leads = (
    Lead.query.options(
      joinedload(Lead.created_by),
      joinedload(Lead.assigned_sdr),
      joinedload(Lead.sdr_agent),
      joinedload(Lead.setter_agent),
      joinedload(Lead.closer_agent),
      joinedload(Lead.pm_agent),
    )
    .filter(Lead.active_only())
    .order_by(Lead.updated_at.desc())
    .all()
  )
  users = User.query.order_by(User.username).all()

  daily = compute_daily_metrics()
  hybrid_metrics = _compute_hybrid_metrics()

  return render_template(
    "admin/dashboard.html",
    leads=leads,
    users=users,
    daily=daily,
    hybrid_metrics=hybrid_metrics,
    to_persian_digits=_to_persian_digits,
    metric_subtitle=_metric_subtitle,
    return_to=url_for("admin.dashboard"),
  )


@bp.route("/followups")
@role_required("admin")
def followups():
  leads = (
    Lead.query.options(joinedload(Lead.sdr_agent), joinedload(Lead.closer_agent))
    .filter(
      Lead.active_only(),
      or_(
        Lead.sdr_followup_date.isnot(None),
        Lead.closer_followup_date.isnot(None),
        and_(Lead.sdr_routed_to_pm.is_(True), Lead.pm_proposal_ready.is_(True)),
      ),
    )
    .order_by(Lead.updated_at.desc())
    .all()
  )
  return render_template("admin/followups.html", leads=leads)


@bp.route("/archived-leads")
@role_required("admin")
def archived_leads():
  leads = (
    Lead.query.options(*_lead_detail_options())
    .filter(_archived_leads_filter())
    .order_by(Lead.updated_at.desc())
    .all()
  )
  return render_template(
    "admin/archived_leads.html",
    leads=leads,
    return_to=url_for("admin.archived_leads"),
  )


@bp.route("/setter-performance")
@role_required("admin")
def setter_performance():
  leads = (
    Lead.query.options(*_lead_detail_options())
    .filter(
      Lead.active_only(),
      or_(
        Lead.current_stage >= 3,
        Lead.sdr_next_action == Lead.SDR_NEXT_ACTION_SETTER,
      ),
    )
    .order_by(Lead.setter_meeting_date.desc().nullslast(), Lead.updated_at.desc())
    .all()
  )
  return render_template(
    "admin/setter_performance.html",
    leads=leads,
    return_to=url_for("admin.setter_performance"),
  )


@bp.route("/closer-meetings")
@role_required("admin")
def closer_meetings():
  leads = (
    Lead.query.options(*_lead_detail_options())
    .filter(Lead.active_only(), Lead.closer_meeting_status.isnot(None))
    .order_by(Lead.updated_at.desc())
    .all()
  )
  return render_template(
    "admin/closer_meetings.html",
    leads=leads,
    return_to=url_for("admin.closer_meetings"),
  )


@bp.route("/sdr-success-calls")
@role_required("admin")
def sdr_success_calls():
  leads = (
    Lead.query.options(*_lead_detail_options())
    .filter(Lead.active_only(), Lead.sdr_call_status == "پاسخ داد")
    .order_by(Lead.sdr_processed_at.desc().nullslast(), Lead.updated_at.desc())
    .all()
  )
  return render_template(
    "admin/sdr_success_calls.html",
    leads=leads,
    return_to=url_for("admin.sdr_success_calls"),
  )


@bp.route("/user/<int:user_id>/analytics")
@role_required("admin")
def user_analytics(user_id):
  user = db.session.get(User, user_id)
  if not user:
    return jsonify({"error": "کاربر یافت نشد."}), 404
  data = compute_user_performance(user)
  data["username"] = user.username
  data["role_label"] = current_app.config["ROLE_LABELS"].get(user.role, user.role)
  return jsonify(data)


@bp.route("/bulk-import", methods=["GET", "POST"])
@role_required("admin")
def bulk_import():
  form = ExcelBulkImportForm()
  if form.validate_on_submit():
    try:
      imported, skipped = import_leads_from_excel(form.excel_file.data)
      flash(
        f"واردسازی انجام شد: {imported} سرنخ جدید ثبت شد و {skipped} ردیف "
        f"(تکراری یا ناقص) نادیده گرفته شد.",
        "success" if imported else "warning",
      )
    except Exception:
      flash(
        "خطا در خواندن فایل اکسل. لطفاً قالب ستون‌ها (B، C، D از ردیف ۲) و فرمت فایل را بررسی کنید.",
        "danger",
      )
      return redirect(url_for("admin.bulk_import"))
    return redirect(url_for("admin.bulk_import"))

  return render_template("admin/bulk_import.html", form=form)


@bp.route("/master-leads")
@role_required("admin")
def master_leads():
  leads = (
    Lead.query.options(*_lead_detail_options())
    .filter(Lead.active_only())
    .order_by(Lead.created_at.desc())
    .all()
  )
  return render_template(
    "admin/master_leads.html",
    leads=leads,
    return_to=url_for("admin.master_leads"),
  )


@bp.route("/lead/<int:lead_id>/edit", methods=["GET", "POST"])
@role_required("admin")
def edit_lead(lead_id):
  lead = db.session.get(Lead, lead_id)
  if not lead:
    flash("لید موردنظر یافت نشد.", "danger")
    return redirect(url_for("admin.master_leads"))

  form = LeadEditForm(obj=lead)
  form.assigned_sdr_id.choices = _agent_choices("sdr")
  form.sdr_agent_id.choices = _agent_choices("sdr")
  form.setter_agent_id.choices = _agent_choices("setter")
  form.pm_agent_id.choices = _agent_choices("pm")
  form.closer_agent_id.choices = _agent_choices("closer")

  if request.method == "GET":
    form.phone_number_2.data = lead.phone_number_2 or ""
    form.phone_number_3.data = lead.phone_number_3 or ""
    form.phone_primary.data = lead.phone_primary or 1
    form.assigned_sdr_id.data = lead.assigned_sdr_id or 0
    form.sdr_agent_id.data = lead.sdr_agent_id or 0
    form.setter_agent_id.data = lead.setter_agent_id or 0
    form.pm_agent_id.data = lead.pm_agent_id or 0
    form.closer_agent_id.data = lead.closer_agent_id or 0
    form.proposal_amount.data = (
      str(int(lead.proposal_amount))
      if isinstance(lead.proposal_amount, float) and lead.proposal_amount.is_integer()
      else (str(lead.proposal_amount) if lead.proposal_amount is not None else "")
    )

  if form.validate_on_submit():
    from app.utils.phone import any_phone_exists, DUPLICATE_PHONE_MESSAGE

    phones = [
      (form.phone_number.data or "").strip(),
      (form.phone_number_2.data or "").strip(),
      (form.phone_number_3.data or "").strip(),
    ]
    phones = [p for p in phones if p]
    dup = any_phone_exists(phones, exclude_lead_id=lead.id)
    if dup:
      flash(DUPLICATE_PHONE_MESSAGE, "danger")
      return render_template("admin/edit_lead.html", form=form, lead=lead)

    prev_assigned_sdr = lead.assigned_sdr_id
    lead.company_name = (form.company_name.data or "").strip()
    lead.phone_number = (form.phone_number.data or "").strip()
    lead.phone_number_2 = (form.phone_number_2.data or "").strip() or None
    lead.phone_number_3 = (form.phone_number_3.data or "").strip() or None
    try:
      lead.phone_primary = int(form.phone_primary.data or 1)
    except (TypeError, ValueError):
      lead.phone_primary = 1
    lead.business_type = (form.business_type.data or "").strip()
    lead.source = (form.source.data or "").strip()
    lead.website = (form.website.data or "").strip() or None
    lead.telegram = (form.telegram.data or "").strip() or None
    lead.instagram = (form.instagram.data or "").strip() or None
    lead.address = (form.address.data or "").strip() or None
    lead.description = (form.description.data or "").strip() or None
    lead.current_stage = form.current_stage.data
    lead.pipeline_status = form.pipeline_status.data
    new_assigned_sdr = _apply_optional_fk(form.assigned_sdr_id.data)
    if new_assigned_sdr and new_assigned_sdr != prev_assigned_sdr:
      lead.assigned_sdr_at = utcnow()
    lead.assigned_sdr_id = new_assigned_sdr

    lead.sdr_call_status = (form.sdr_call_status.data or "").strip() or None
    lead.sdr_result = (form.sdr_result.data or "").strip() or None
    lead.sdr_rejection_reason = (form.sdr_rejection_reason.data or "").strip() or None
    lead.sdr_pain_severity = (form.sdr_pain_severity.data or "").strip() or None
    lead.sdr_buying_power = (form.sdr_buying_power.data or "").strip() or None
    lead.sdr_contact_person = (form.sdr_contact_person.data or "").strip() or None
    lead.sdr_contact_name = (form.sdr_contact_name.data or "").strip() or None
    lead.sdr_interest_level = (form.sdr_interest_level.data or "").strip() or None
    lead.sdr_next_action = (form.sdr_next_action.data or "").strip() or None
    lead.sdr_followup_date = form.sdr_followup_date.data
    lead.wrong_number_type = (form.wrong_number_type.data or "").strip() or None
    lead.wrong_number_notes = (form.wrong_number_notes.data or "").strip() or None
    lead.sdr_summary = (form.sdr_summary.data or "").strip() or None
    lead.sdr_agent_id = _apply_optional_fk(form.sdr_agent_id.data)

    lead.setter_status = (form.setter_status.data or "").strip() or None
    lead.setter_meeting_date = form.setter_meeting_date.data
    lead.setter_meeting_location = (form.setter_meeting_location.data or "").strip() or None
    lead.setter_notes = (form.setter_notes.data or "").strip() or None
    lead.setter_agent_id = _apply_optional_fk(form.setter_agent_id.data)

    lead.pm_agent_id = _apply_optional_fk(form.pm_agent_id.data)
    lead.proposal_title = (form.proposal_title.data or "").strip() or None
    try:
      lead.proposal_amount = form.parse_proposal_amount()
    except ValueError:
      form.proposal_amount.errors.append("مبلغ پروپوزال معتبر نیست.")
      return render_template("admin/edit_lead.html", form=form, lead=lead)
    lead.proposal_details = (form.proposal_details.data or "").strip() or None
    lead.proposal_date = form.proposal_date.data

    lead.closer_meeting_status = (form.closer_meeting_status.data or "").strip() or None
    lead.closer_cooperation_status = (form.closer_cooperation_status.data or "").strip() or None
    lead.closer_followup_date = form.closer_followup_date.data
    lead.closer_notes = (form.closer_notes.data or "").strip() or None
    lead.closer_agent_id = _apply_optional_fk(form.closer_agent_id.data)
    lead.deal_outcome = (form.deal_outcome.data or "").strip() or None
    lead.closing_notes = (form.closing_notes.data or "").strip() or None
    lead.closed_at = form.closed_at.data

    db.session.commit()
    flash("لید با موفقیت ویرایش شد.", "success")
    next_url = request.args.get("next") or request.form.get("next")
    if next_url and next_url.startswith("/admin/"):
      return redirect(next_url)
    return redirect(url_for("admin.master_leads"))

  return render_template("admin/edit_lead.html", form=form, lead=lead)


@bp.route("/lead/<int:lead_id>/delete", methods=["POST"])
@role_required("admin")
def delete_lead(lead_id):
  lead = db.session.get(Lead, lead_id)
  if not lead:
    flash("لید موردنظر یافت نشد.", "danger")
    return redirect(url_for("admin.master_leads"))
  company_name = lead.company_name
  if lead.is_admin_deleted:
    db.session.delete(lead)
    db.session.commit()
    flash(f"لید «{company_name}» به‌طور دائمی از سیستم حذف شد.", "success")
  else:
    lead.admin_deleted_at = utcnow()
    lead.admin_deleted_by_id = current_user.id
    lead.assigned_sdr_id = None
    lead.updated_at = utcnow()
    db.session.commit()
    flash(
      f"لید «{company_name}» بایگانی شد و در لیست لیدهای حذف‌شده نمایش داده می‌شود.",
      "success",
    )
  next_url = request.form.get("next")
  if next_url and next_url.startswith("/admin/"):
    return redirect(next_url)
  return redirect(url_for("admin.master_leads"))


@bp.route("/daily-report")
@role_required("admin")
def daily_report():
  daily = compute_daily_metrics()
  return render_template("admin/daily_report_print.html", daily=daily)


@bp.route("/employee-daily-report")
@role_required("admin")
def employee_daily_report():
  employees = compute_employees_daily_report()
  role_labels = current_app.config["ROLE_LABELS"]
  for row in employees:
    row["role_label"] = role_labels.get(row["role"], row["role"])
    row["today_count_display"] = _to_persian_digits(row["today_count"])
  return render_template(
    "admin/employee_daily_report_print.html",
    employees=employees,
    jalali_date=jalali_today_label(),
    to_persian_digits=_to_persian_digits,
  )


@bp.route("/export/excel/master")
@role_required("admin")
def export_excel_master():
  leads = Lead.query.options(*_lead_detail_options()).order_by(Lead.id.asc()).all()
  buffer, filename = export_master_xlsx(leads)
  return send_file(
    buffer,
    mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    as_attachment=True,
    download_name=filename,
  )


@bp.route("/export/excel/sdr")
@role_required("admin")
def export_excel_sdr():
  leads = (
    Lead.query.options(*_lead_detail_options())
    .filter(Lead.current_stage >= 2)
    .order_by(Lead.updated_at.desc())
    .all()
  )
  buffer, filename = export_department_xlsx(leads, "SDR", build_sdr_department_rows)
  return send_file(
    buffer,
    mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    as_attachment=True,
    download_name=filename,
  )


@bp.route("/export/excel/setter")
@role_required("admin")
def export_excel_setter():
  leads = (
    Lead.query.options(*_lead_detail_options())
    .filter(
      or_(
        Lead.current_stage >= 3,
        Lead.setter_status.isnot(None),
        Lead.setter_meeting_date.isnot(None),
      )
    )
    .order_by(Lead.setter_meeting_date.desc().nullslast(), Lead.updated_at.desc())
    .all()
  )
  buffer, filename = export_department_xlsx(leads, "Setter", build_setter_department_rows)
  return send_file(
    buffer,
    mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    as_attachment=True,
    download_name=filename,
  )


@bp.route("/export/excel/closer")
@role_required("admin")
def export_excel_closer():
  leads = (
    Lead.query.options(*_lead_detail_options())
    .filter(
      or_(
        Lead.current_stage >= 5,
        Lead.closer_meeting_status.isnot(None),
        Lead.closer_cooperation_status.isnot(None),
      )
    )
    .order_by(Lead.updated_at.desc())
    .all()
  )
  buffer, filename = export_department_xlsx(leads, "Closer", build_closer_department_rows)
  return send_file(
    buffer,
    mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    as_attachment=True,
    download_name=filename,
  )


@bp.route("/users/new", methods=["GET", "POST"])
@role_required("admin")
def create_user():
  form = UserForm()
  if form.validate_on_submit():
    if User.query.filter_by(username=form.username.data).first():
      flash("این نام کاربری قبلاً ثبت شده است.", "danger")
    else:
      user = User(username=form.username.data, role=form.role.data)
      user.set_password(form.password.data)
      db.session.add(user)
      db.session.commit()
      flash(f"کاربر «{user.username}» با موفقیت ایجاد شد.", "success")
      return redirect(url_for("admin.dashboard"))
  return render_template("admin/create_user.html", form=form)


@bp.route("/user/<int:user_id>/edit", methods=["GET", "POST"])
@role_required("admin")
def edit_user(user_id):
  user = db.session.get(User, user_id)
  if not user:
    flash("کاربر یافت نشد.", "danger")
    return redirect(url_for("admin.dashboard"))

  form = UserEditForm(obj=user)
  if form.validate_on_submit():
    existing = User.query.filter(
      User.username == form.username.data,
      User.id != user.id,
    ).first()
    if existing:
      flash("این نام کاربری قبلاً استفاده شده است.", "danger")
      return render_template("admin/edit_user.html", form=form, user=user)

    user.username = form.username.data
    user.role = form.role.data
    new_password = (form.password.data or "").strip()
    if new_password:
      user.set_password(new_password)
    db.session.commit()
    flash("اطلاعات کاربر با موفقیت ویرایش شد.", "success")
    return redirect(url_for("admin.dashboard"))

  if request.method == "GET":
    form.password.data = ""

  return render_template("admin/edit_user.html", form=form, user=user)


@bp.route("/user/<int:user_id>/toggle-active", methods=["POST"])
@role_required("admin")
def toggle_user_active(user_id):
  user = db.session.get(User, user_id)
  if not user:
    flash("کاربر یافت نشد.", "danger")
    return redirect(url_for("admin.dashboard"))

  if user.id == current_user.id:
    flash("نمی‌توانید وضعیت حساب خودتان را تغییر دهید.", "warning")
    return redirect(url_for("admin.dashboard"))

  user.is_active = not user.is_active
  db.session.commit()

  if user.is_active:
    flash(f"کاربر «{user.username}» با موفقیت فعال شد.", "success")
  else:
    flash(f"کاربر «{user.username}» با موفقیت تعلیق شد.", "success")

  return redirect(url_for("admin.dashboard"))


@bp.route("/user/<int:user_id>/delete", methods=["POST"])
@role_required("admin")
def delete_user(user_id):
  user = db.session.get(User, user_id)
  if not user:
    flash("کاربر یافت نشد.", "danger")
    return redirect(url_for("admin.dashboard"))

  if user.id == current_user.id:
    flash("نمی‌توانید حساب کاربری خودتان را حذف کنید.", "warning")
    return redirect(url_for("admin.dashboard"))

  username = user.username
  Lead.query.filter_by(created_by_id=user.id).update(
    {Lead.created_by_id: None}, synchronize_session=False
  )
  db.session.delete(user)
  db.session.commit()
  flash(f"کاربر «{username}» با موفقیت حذف گردید.", "success")
  return redirect(url_for("admin.dashboard"))


def _unassigned_leads_base_query():
  return Lead.query.filter(
    Lead.active_only(),
    Lead.current_stage == 2,
    Lead.assigned_sdr_id.is_(None),
  )


def _distribute_leads_equally(leads, selected_sdrs) -> dict[int, int]:
  assigned_counter = {u.id: 0 for u in selected_sdrs}
  for idx, lead in enumerate(leads):
    user = selected_sdrs[idx % len(selected_sdrs)]
    lead.assigned_sdr_id = user.id
    lead.assigned_sdr_at = utcnow()
    assigned_counter[user.id] += 1
  return assigned_counter


def _distribution_summary(selected_sdrs, assigned_counter: dict[int, int]) -> str:
  return "، ".join(
    f"{user.username}: {_to_persian_digits(assigned_counter[user.id])}"
    for user in selected_sdrs
  )


@bp.route("/lead-distribution", methods=["GET", "POST"])
@role_required("admin")
def lead_distribution():
  today_form = DistributeLeadsForm(prefix="today")
  backlog_form = DistributeBacklogLeadsForm(prefix="backlog")
  active_sdrs = (
    User.query.filter_by(role="sdr", is_active=True)
    .order_by(User.username.asc())
    .all()
  )
  sdr_choices = [(user.id, user.username) for user in active_sdrs]
  today_form.sdr_ids.choices = sdr_choices
  backlog_form.sdr_ids.choices = sdr_choices

  start, end = today_utc_range()
  today_unassigned_query = (
    _unassigned_leads_base_query()
    .filter(Lead.created_at >= start, Lead.created_at <= end)
    .order_by(Lead.created_at.asc(), Lead.id.asc())
  )
  backlog_unassigned_query = (
    _unassigned_leads_base_query()
    .filter(Lead.created_at < start)
    .order_by(Lead.created_at.asc(), Lead.id.asc())
  )
  today_unassigned_count = today_unassigned_query.count()
  backlog_unassigned_count = backlog_unassigned_query.count()

  if today_form.submit.data and today_form.validate_on_submit():
    selected_sdrs = [u for u in active_sdrs if u.id in today_form.sdr_ids.data]
    if not selected_sdrs:
      flash("حداقل یک SDR فعال انتخاب کنید.", "warning")
      return redirect(url_for("admin.lead_distribution"))

    leads = today_unassigned_query.all()
    if not leads:
      flash("هیچ لید توزیع‌نشده‌ای برای امروز وجود ندارد.", "warning")
      return redirect(url_for("admin.lead_distribution"))

    assigned_counter = _distribute_leads_equally(leads, selected_sdrs)
    db.session.commit()
    summary = _distribution_summary(selected_sdrs, assigned_counter)
    flash(
      f"توزیع لیدهای امروز انجام شد. مجموع {_to_persian_digits(len(leads))} لید بین SDRها تقسیم شد ({summary}).",
      "success",
    )
    return redirect(url_for("admin.lead_distribution"))

  if backlog_form.submit.data and backlog_form.validate_on_submit():
    selected_sdrs = [u for u in active_sdrs if u.id in backlog_form.sdr_ids.data]
    if not selected_sdrs:
      flash("حداقل یک SDR فعال انتخاب کنید.", "warning")
      return redirect(url_for("admin.lead_distribution"))

    leads = backlog_unassigned_query.all()
    if not leads:
      flash("هیچ لید معوقه و پخش‌نشده‌ای از روزهای گذشته وجود ندارد.", "warning")
      return redirect(url_for("admin.lead_distribution"))

    assigned_counter = _distribute_leads_equally(leads, selected_sdrs)
    db.session.commit()
    summary = _distribution_summary(selected_sdrs, assigned_counter)
    flash(
      f"توزیع لیدهای معوقه انجام شد. مجموع {_to_persian_digits(len(leads))} لید از روزهای گذشته بین SDRها تقسیم شد ({summary}).",
      "success",
    )
    return redirect(url_for("admin.lead_distribution"))

  return render_template(
    "admin/lead_distribution.html",
    today_form=today_form,
    backlog_form=backlog_form,
    today_unassigned_count=today_unassigned_count,
    backlog_unassigned_count=backlog_unassigned_count,
    jalali_today=jalali_today_label(),
    to_persian_digits=_to_persian_digits,
  )
