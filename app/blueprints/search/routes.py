from flask import render_template, request
from flask_login import login_required
from sqlalchemy.orm import joinedload

from app.blueprints.search import bp
from app.forms.search_forms import LeadSearchForm
from app.models import Lead


def _build_lead_query(name: str, business_type: str, source: str):
  query = Lead.query.options(
    joinedload(Lead.created_by),
    joinedload(Lead.sdr_agent),
  )

  name = (name or "").strip()
  if name:
    query = query.filter(Lead.company_name.ilike(f"%{name}%"))

  if business_type:
    query = query.filter(Lead.business_type == business_type)

  if source:
    query = query.filter(Lead.source == source)

  return query.order_by(Lead.updated_at.desc())


def _has_search_params() -> bool:
  return bool(
    request.args.get("submit")
    or (request.args.get("company_name") or "").strip()
    or request.args.get("business_type")
    or request.args.get("source")
  )


@bp.route("/", methods=["GET"])
@login_required
def search_leads():
  form = LeadSearchForm(formdata=request.args)
  leads = []
  searched = _has_search_params()

  if searched:
    leads = _build_lead_query(
      form.company_name.data,
      form.business_type.data,
      form.source.data,
    ).all()

  return render_template(
    "search/results.html",
    form=form,
    leads=leads,
    searched=searched,
    result_count=len(leads),
  )
