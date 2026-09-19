"""جریان‌های کاری سرنخ (بازگشت LH، پاک‌سازی SDR)."""

from app.models import Lead, utcnow


def clear_sdr_fields_for_lh_resubmit(lead: Lead) -> None:
  """پاک‌سازی داده‌های SDR پس از اصلاح شماره توسط LH."""
  lead.sdr_call_status = None
  lead.sdr_result = None
  lead.sdr_rejection_reason = None
  lead.sdr_pain_severity = None
  lead.sdr_buying_power = None
  lead.sdr_contact_person = None
  lead.sdr_interest_level = None
  lead.sdr_next_action = None
  lead.sdr_followup_date = None
  lead.wrong_number_type = None
  lead.wrong_number_notes = None
  lead.sdr_summary = None
  lead.sdr_agent_id = None
  lead.sdr_processed_at = None
  lead.sdr_routed_to_pm = False
  lead.pm_proposal_ready = False
  lead.proposal_status = "pending"


def send_lead_to_sdr_pool(lead: Lead) -> None:
  """انتقال سرنخ به مرحله ۲ بدون اختصاص خودکار SDR."""
  lead.current_stage = 2
  lead.pipeline_status = "active"
  lead.assigned_sdr_id = None
  lead.updated_at = utcnow()


def return_lead_to_lh_wrong_number(lead: Lead) -> None:
  """بازگرداندن سرنخ به LH پس از ثبت شماره اشتباه."""
  lead.current_stage = 1
  lead.pipeline_status = "active"
  lead.assigned_sdr_id = None
  lead.updated_at = utcnow()
