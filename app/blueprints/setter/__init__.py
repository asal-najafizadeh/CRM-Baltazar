from flask import Blueprint

bp = Blueprint("setter", __name__, url_prefix="/setter")

from app.blueprints.setter import routes  # noqa: E402, F401
