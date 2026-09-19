from flask import Blueprint

bp = Blueprint("closer", __name__, url_prefix="/closer")

from app.blueprints.closer import routes  # noqa: E402, F401
