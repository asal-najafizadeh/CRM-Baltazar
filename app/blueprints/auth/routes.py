from flask import flash, redirect, render_template, url_for
from flask_login import current_user, login_user, logout_user

from app.blueprints.auth import bp
from app.forms.auth_forms import LoginForm
from app.models import User
from app.utils.decorators import redirect_to_role_dashboard


@bp.route("/login", methods=["GET", "POST"])
def login():
  if current_user.is_authenticated:
    if not current_user.is_active:
      logout_user()
    else:
      return redirect_to_role_dashboard()

  form = LoginForm()
  if form.validate_on_submit():
    user = User.query.filter_by(username=form.username.data).first()
    if user and user.check_password(form.password.data):
      if not user.is_active:
        flash(
          "حساب کاربری شما تعلیق شده است. لطفاً با مدیر سیستم تماس بگیرید.",
          "danger",
        )
        return render_template("auth/login.html", form=form)
      login_user(user)
      flash("ورود با موفقیت انجام شد.", "success")
      return redirect_to_role_dashboard()
    flash("نام کاربری یا رمز عبور اشتباه است.", "danger")

  return render_template("auth/login.html", form=form)


@bp.route("/logout")
def logout():
  logout_user()
  flash("از حساب کاربری خارج شدید.", "info")
  return redirect(url_for("auth.login"))
