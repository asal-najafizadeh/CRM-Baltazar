"""مرتب‌سازی صف SDR: لیدهای rollover (تماس‌نخورده روز قبل) در ابتدای صف."""

from app.models import Lead


def sort_sdr_daily_queue(leads: list[Lead]) -> list[Lead]:
  """
  اولویت ۱: carryover (تماس گرفته نشده از روز قبل)
  اولویت ۲: بقیه لیدهای جدید
  در هر گروه: قدیمی‌تر زودتر (FIFO)
  """

  def _sort_key(lead: Lead):
    carryover = 0 if lead.is_sdr_uncalled_carryover else 1
    since = lead.sdr_queue_since
    ts = since.timestamp() if since else 0
    return (carryover, ts, lead.id)

  return sorted(leads, key=_sort_key)
