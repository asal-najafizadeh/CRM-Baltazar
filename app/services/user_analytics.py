"""آنالیز عملکرد کاربران برای پنل ادمین."""

from sqlalchemy import and_

from app.models import Lead, User
from app.utils.jalali_dates import today_utc_range


def compute_user_performance(user: User) -> dict:
  start, end = today_utc_range()
  role = user.role

  def _between(column):
    return and_(column >= start, column <= end)

  if role == "lh":
    today_count = Lead.query.filter(
      Lead.created_by_id == user.id,
      _between(Lead.created_at),
    ).count()
    total_count = Lead.query.filter_by(created_by_id=user.id).count()
    return {
      "role": role,
      "today_label": "تعداد لیدهای ثبت شده امروز",
      "today_count": today_count,
      "total_label": "کل لیدهای ثبت شده در کل دوره",
      "total_count": total_count,
    }

  if role == "sdr":
    today_count = Lead.query.filter(
      Lead.sdr_agent_id == user.id,
      Lead.sdr_processed_at.isnot(None),
      _between(Lead.sdr_processed_at),
    ).count()
    total_count = Lead.query.filter(
      Lead.sdr_agent_id == user.id,
      Lead.sdr_processed_at.isnot(None),
    ).count()
    return {
      "role": role,
      "today_label": "تعداد تماس‌های ثبت شده امروز",
      "today_count": today_count,
      "total_label": "کل تماس‌های ثبت شده در کل دوره",
      "total_count": total_count,
    }

  if role == "setter":
    base = Lead.setter_agent_id == user.id
    today_count = Lead.query.filter(
      base,
      Lead.setter_status.isnot(None),
      Lead.setter_status != "",
      _between(Lead.updated_at),
    ).count()
    total_count = Lead.query.filter(
      base,
      Lead.setter_status.isnot(None),
      Lead.setter_status != "",
    ).count()
    return {
      "role": role,
      "today_label": "تعداد جلسات تنظیم شده امروز (همه وضعیت‌ها)",
      "today_count": today_count,
      "total_label": "کل جلسات تنظیم شده در کل دوره",
      "total_count": total_count,
    }

  if role == "pm":
    base = [
      Lead.pm_agent_id == user.id,
      Lead.proposal_status == "sent",
      Lead.pm_proposal_ready.is_(True),
    ]
    today_count = Lead.query.filter(*base, _between(Lead.updated_at)).count()
    total_count = Lead.query.filter(*base).count()
    return {
      "role": role,
      "today_label": "تعداد پروپوزال‌های ارسال شده امروز",
      "today_count": today_count,
      "total_label": "کل پروپوزال‌های ارسال شده در کل دوره",
      "total_count": total_count,
    }

  if role == "closer":
    base = [
      Lead.closer_agent_id == user.id,
      Lead.closer_meeting_status == Lead.CLOSER_MEETING_HELD,
    ]
    today_count = Lead.query.filter(*base, _between(Lead.updated_at)).count()
    total_count = Lead.query.filter(*base).count()
    return {
      "role": role,
      "today_label": "تعداد جلسات برگزار شده امروز",
      "today_count": today_count,
      "total_label": "کل جلسات برگزار شده در کل دوره",
      "total_count": total_count,
    }

  return {
    "role": role,
    "today_label": "فعالیت امروز",
    "today_count": 0,
    "total_label": "فعالیت کل دوره",
    "total_count": 0,
    "unsupported": True,
  }


def compute_employees_daily_report() -> list[dict]:
  """گزارش عملکرد امروز برای همه کارمندان فعال."""
  users = (
    User.query.filter_by(is_active=True)
    .order_by(User.role.asc(), User.username.asc())
    .all()
  )
  rows = []
  for user in users:
    perf = compute_user_performance(user)
    rows.append(
      {
        "user": user,
        "username": user.username,
        "role": user.role,
        "today_count": perf["today_count"],
        "today_label": perf["today_label"],
        "unsupported": perf.get("unsupported", False),
      }
    )
  return rows
