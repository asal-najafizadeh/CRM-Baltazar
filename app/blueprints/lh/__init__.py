from flask import Blueprint

bp = Blueprint("lh", __name__, url_prefix="/lh")

from app.blueprints.lh import routes  # noqa: E402, F401
