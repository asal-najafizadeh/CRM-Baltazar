from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, ValidationError

from app.forms.jalali_fields import JalaliDateTimeField
from app.models import Lead

MSG_REQUIRED = "این فیلد الزامی است."

SETTER_STATUS_CHOICES = [
  ("", "— انتخاب کنید —"),
  (Lead.SETTER_STATUS_APPROVED, Lead.SETTER_STATUS_APPROVED),
  (Lead.SETTER_STATUS_REJECTED, Lead.SETTER_STATUS_REJECTED),
  (Lead.SETTER_STATUS_UNCERTAIN, Lead.SETTER_STATUS_UNCERTAIN),
]


class SetterForm(FlaskForm):
  setter_status = SelectField(
    "وضعیت جلسه",
    choices=SETTER_STATUS_CHOICES,
    validators=[DataRequired(message="وضعیت جلسه را انتخاب کنید.")],
  )
  setter_meeting_date = JalaliDateTimeField(
    "تاریخ و ساعت جلسه (شمسی)",
    validators=[Optional()],
  )
  setter_meeting_location = StringField(
    "مکان جلسه",
    validators=[Optional(), Length(max=500)],
    render_kw={"placeholder": "حضوری: آدرس دفتر — آنلاین: لینک جلسه"},
  )
  setter_notes = TextAreaField(
    "یادداشت‌ها و توضیحات",
    validators=[Optional()],
    render_kw={"placeholder": "جزئیات هماهنگی، نکات مهم برای کلوزر...", "rows": 4},
  )
  submit = SubmitField("ذخیره و به‌روزرسانی")

  def validate_setter_meeting_date(self, field):
    if self.setter_status.data == Lead.SETTER_STATUS_APPROVED and not field.data:
      raise ValidationError("برای جلسه تأییدشده، تاریخ و ساعت الزامی است.")

  def validate_setter_meeting_location(self, field):
    if self.setter_status.data == Lead.SETTER_STATUS_APPROVED:
      if not (field.data or "").strip():
        raise ValidationError("برای جلسه تأییدشده، مکان جلسه الزامی است.")
