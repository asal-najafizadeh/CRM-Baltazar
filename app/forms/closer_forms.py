from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, ValidationError

from app.forms.jalali_fields import JalaliDateTimeField
from app.models import Lead

MSG_REQUIRED = "این فیلد الزامی است."

CLOSER_MEETING_STATUS_CHOICES = [
  ("", "— انتخاب کنید —"),
  (Lead.CLOSER_MEETING_HELD, Lead.CLOSER_MEETING_HELD),
  (Lead.CLOSER_MEETING_NOT_HELD, Lead.CLOSER_MEETING_NOT_HELD),
]

CLOSER_COOPERATION_STATUS_CHOICES = [
  ("", "— انتخاب کنید —"),
  (Lead.CLOSER_COOP_SUCCESS, Lead.CLOSER_COOP_SUCCESS),
  (Lead.CLOSER_COOP_FOLLOWUP, Lead.CLOSER_COOP_FOLLOWUP),
  (Lead.CLOSER_COOP_REJECT, Lead.CLOSER_COOP_REJECT),
]


class CloserForm(FlaskForm):
  closer_meeting_status = SelectField(
    "وضعیت جلسه",
    choices=CLOSER_MEETING_STATUS_CHOICES,
    validators=[DataRequired(message="وضعیت جلسه را انتخاب کنید.")],
  )
  closer_cooperation_status = SelectField(
    "وضعیت همکاری",
    choices=CLOSER_COOPERATION_STATUS_CHOICES,
    validators=[DataRequired(message="وضعیت همکاری را انتخاب کنید.")],
  )
  closer_followup_date = JalaliDateTimeField(
    "تاریخ پیگیری مجدد (شمسی)",
    validators=[Optional()],
  )
  closer_notes = TextAreaField(
    "یادداشت و توضیحات",
    validators=[
      DataRequired(message=MSG_REQUIRED),
      Length(min=5, message="یادداشت باید حداقل ۵ کاراکتر باشد."),
    ],
    render_kw={"placeholder": "نتیجه نهایی جلسه، توافقات، دلایل رد و...", "rows": 5},
  )
  submit = SubmitField("ثبت نتیجه نهایی")

  def validate_closer_followup_date(self, field):
    if self.closer_cooperation_status.data == Lead.CLOSER_COOP_FOLLOWUP and not field.data:
      raise ValidationError("برای پیگیری مجدد، تاریخ پیگیری الزامی است.")

  def validate_closer_cooperation_status(self, field):
    if field.data == Lead.CLOSER_COOP_SUCCESS:
      if self.closer_meeting_status.data != Lead.CLOSER_MEETING_HELD:
        raise ValidationError(
          "برای وضعیت «موفق»، جلسه باید «برگزار شد» ثبت شده باشد."
        )
