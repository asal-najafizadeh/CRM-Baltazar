from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Length


class LoginForm(FlaskForm):
  username = StringField(
    "نام کاربری",
    validators=[
      DataRequired(message="نام کاربری الزامی است."),
      Length(max=80),
    ],
    render_kw={"placeholder": "نام کاربری خود را وارد کنید"},
  )
  password = PasswordField(
    "رمز عبور",
    validators=[DataRequired(message="رمز عبور الزامی است.")],
    render_kw={"placeholder": "رمز عبور"},
  )
  submit = SubmitField("ورود به سیستم")
