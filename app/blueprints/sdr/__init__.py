from flask import Blueprint

bp = Blueprint("sdr", __name__, url_prefix="/sdr")

from app.blueprints.sdr import routes  # noqa: E402, F401
