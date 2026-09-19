"""داده‌های جدول برترین‌ها."""

from flask_login import current_user

from app.models import User


def get_rating_board_data() -> dict:
  """همه کاربران فعال دارای امتیاز (به‌جز ادمین)، مرتب‌شده بر اساس امتیاز."""
  agents = (
    User.query.filter(
      User.is_active.is_(True),
      User.role.in_(("lh", "sdr", "setter", "pm", "closer")),
    )
    .order_by(User.score.desc(), User.username.asc())
    .all()
  )

  my_rank = None
  if current_user.is_authenticated and current_user.role != "admin":
    for i, u in enumerate(agents, start=1):
      if u.id == current_user.id:
        my_rank = i
        break

  return {
    "agents": agents,
    "my_rank": my_rank,
    "my_score": current_user.score if current_user.is_authenticated else 0,
  }
