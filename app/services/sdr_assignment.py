"""توزیع عادلانه خودکار سرنخ بین SDRهای فعال."""

from app.models import Lead, User


def _active_sdr_users():
  return (
    User.query.filter_by(role="sdr", is_active=True)
    .order_by(User.id.asc())
    .all()
  )


def count_assigned_sdr_pool(sdr_user_id: int) -> int:
  """تعداد سرنخ‌های فعال مرحله ۲ اختصاص‌یافته به یک SDR."""
  return Lead.query.filter(
    Lead.assigned_sdr_id == sdr_user_id,
    Lead.current_stage == 2,
    Lead.pipeline_status == "active",
  ).count()


def assign_sdr_to_lead(lead: Lead) -> User | None:
  """
  اختصاص سرنخ به SDR با کمترین بار کاری در صف مرحله ۲.
  در صورت تساوی، کاربر با id کمتر (چرخش پایدار).
  """
  sdrs = _active_sdr_users()
  if not sdrs:
    lead.assigned_sdr_id = None
    return None

  if len(sdrs) == 1:
    lead.assigned_sdr_id = sdrs[0].id
    return sdrs[0]

  counts = {sdr.id: count_assigned_sdr_pool(sdr.id) for sdr in sdrs}
  min_count = min(counts.values())
  chosen = next(sdr for sdr in sdrs if counts[sdr.id] == min_count)
  lead.assigned_sdr_id = chosen.id
  return chosen


def release_sdr_assignment(lead: Lead) -> None:
  lead.assigned_sdr_id = None
