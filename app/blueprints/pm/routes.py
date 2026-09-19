from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy.orm import joinedload

from app.blueprints.pm import bp
from app.extensions import db
from app.models import Lead, utcnow
from app.utils.decorators import role_required
from app.utils.jalali_dates import parse_jalali_date


def _pm_leads_query():
  return (
    Lead.query.options(
      joinedload(Lead.created_by),
      joinedload(Lead.sdr_agent),
    )
    .filter(
      Lead.current_stage == 4,
      Lead.pipeline_status == "active",
    )
    .order_by(Lead.updated_at.desc())
  )


@bp.route("/")
@role_required("pm")
def dashboard():
  leads = _pm_leads_query().all()
  return render_template("pm/dashboard.html", leads=leads)


@bp.route("/lead/<int:lead_id>/submit-proposal", methods=["POST"])
@role_required("pm")
def submit_proposal(lead_id):
  lead = (
    Lead.query.options(joinedload(Lead.sdr_agent), joinedload(Lead.created_by))
    .filter_by(id=lead_id, current_stage=4)
    .first()
  )
  if not lead:
    abort(404)

  if lead.is_proposal_sent:
    flash("پروپوزال این سرنخ قبلاً ارسال شده است.", "warning")
    return redirect(url_for("pm.dashboard"))

  title = (request.form.get("proposal_title") or "").strip()
  details = (request.form.get("proposal_details") or "").strip()
  amount_raw = request.form.get("proposal_amount")
  proposal_date = parse_jalali_date(request.form.get("proposal_date"))

  if not title:
    flash("عنوان پروپوزال الزامی است.", "danger")
    return redirect(url_for("pm.dashboard") + f"#lead-{lead_id}")
  try:
    amount = float(amount_raw)
    if amount < 0:
      raise ValueError
  except (TypeError, ValueError):
    flash("مبلغ پیشنهادی معتبر نیست.", "danger")
    return redirect(url_for("pm.dashboard") + f"#lead-{lead_id}")
  if not proposal_date:
    flash("تاریخ پروپوزال (شمسی) را به‌درستی وارد کنید.", "danger")
    return redirect(url_for("pm.dashboard") + f"#lead-{lead_id}")
  if len(details) < 10:
    flash("جزئیات پروپوزال باید حداقل ۱۰ کاراکتر باشد.", "danger")
    return redirect(url_for("pm.dashboard") + f"#lead-{lead_id}")

  lead.proposal_title = title
  lead.proposal_amount = amount
  lead.proposal_date = proposal_date
  lead.proposal_details = details
  lead.proposal_status = "sent"
  lead.pm_proposal_ready = True
  lead.pm_agent_id = current_user.id
  lead.updated_at = utcnow()

  db.session.commit()
  flash(
    f"پروپوزال «{lead.company_name}» با موفقیت ثبت و برای پیگیری SDR ارسال شد.",
    "success",
  )
  return redirect(url_for("pm.dashboard"))


@bp.route("/lead/<int:lead_id>/proposal-ready", methods=["POST"])
@role_required("pm")
def mark_proposal_ready(lead_id):
  """مسیر قدیمی — هدایت به فرم کامل پروپوزال."""
  return redirect(url_for("pm.dashboard") + f"#lead-{lead_id}")
