from flask import render_template
from flask_login import login_required

from app.blueprints.shared import bp
from app.services.leaderboard import get_rating_board_data


@bp.route("/rating-board/modal")
@login_required
def rating_board_modal():
  return render_template(
    "partials/rating_board_modal.html",
    rating_board=get_rating_board_data(),
  )
