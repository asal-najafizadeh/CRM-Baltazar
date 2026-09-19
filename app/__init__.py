import os
from pathlib import Path

from flask import Flask, redirect, url_for
from flask_login import current_user

from app.config import Config
from app.extensions import bcrypt, csrf, db, login_manager
from app.models import User


def create_app(config_class=Config):
  app = Flask(__name__)
  app.config.from_object(config_class)

  instance_path = Path(app.instance_path)
  instance_path.mkdir(parents=True, exist_ok=True)

  db.init_app(app)
  bcrypt.init_app(app)
  csrf.init_app(app)
  login_manager.init_app(app)

  register_blueprints(app)
  register_root_routes(app)
  register_context_processors(app)

  @login_manager.user_loader
  def load_user(user_id):
    user = db.session.get(User, int(user_id))
    if user is not None and user.is_active:
      return user
    return None

  @app.errorhandler(403)
  def forbidden(_e):
    from flask import render_template

    return render_template("errors/403.html"), 403

  with app.app_context():
    db.create_all()
    from app.utils.db_migrate import apply_schema_patches

    apply_schema_patches()

  return app


def register_blueprints(app):
  from app.blueprints.auth import bp as auth_bp
  from app.blueprints.admin import bp as admin_bp
  from app.blueprints.lh import bp as lh_bp
  from app.blueprints.sdr import bp as sdr_bp
  from app.blueprints.setter import bp as setter_bp
  from app.blueprints.pm import bp as pm_bp
  from app.blueprints.closer import bp as closer_bp
  from app.blueprints.search import bp as search_bp
  from app.blueprints.shared import bp as shared_bp

  app.register_blueprint(auth_bp)
  app.register_blueprint(shared_bp)
  app.register_blueprint(admin_bp)
  app.register_blueprint(lh_bp)
  app.register_blueprint(sdr_bp)
  app.register_blueprint(setter_bp)
  app.register_blueprint(pm_bp)
  app.register_blueprint(closer_bp)
  app.register_blueprint(search_bp)


def register_context_processors(app):
  from flask_login import current_user

  from app.utils.jalali_dates import (
    format_jalali_date,
    format_jalali_datetime,
    jalali_today_label,
  )

  @app.context_processor
  def inject_labels():
    return {
      "STAGE_LABELS": app.config["STAGE_LABELS"],
      "ROLE_LABELS": app.config["ROLE_LABELS"],
      "PIPELINE_STATUS_LABELS": app.config["PIPELINE_STATUS_LABELS"],
      "format_jalali_date": format_jalali_date,
      "format_jalali_datetime": format_jalali_datetime,
      "jalali_today_label": jalali_today_label(),
    }


def register_root_routes(app):
  from app.utils.decorators import redirect_to_role_dashboard

  @app.route("/")
  def index():
    if current_user.is_authenticated:
      return redirect_to_role_dashboard()
    return redirect(url_for("auth.login"))
