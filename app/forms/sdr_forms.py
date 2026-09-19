from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, ValidationError

from app.forms.jalali_fields import JalaliDateField
from app.models import Lead

MSG_REQUIRED = "این فیلد الزامی است."

SDR_CALL_STATUS_ANSWERED = "پاسخ داد"
SDR_CALL_WRONG_NUMBER = Lead.SDR_CALL_WRONG_NUMBER
SDR_CALL_NO_ANSWER_STATUSES = ("پاسخ نداد", "تماس قطع شده")

SDR_CALL_STATUS_CHOICES = [
  ("", "— انتخاب کنید —"),
  (SDR_CALL_STATUS_ANSWERED, SDR_CALL_STATUS_ANSWERED),
  ("پاسخ نداد", "پاسخ نداد"),
  (SDR_CALL_WRONG_NUMBER, SDR_CALL_WRONG_NUMBER),
  ("تماس قطع شده", "تماس قطع شده"),
]

WRONG_NUMBER_TYPE_CHOICES = [
  ("", "— انتخاب کنید —"),
  (Lead.WRONG_NUMBER_SELF, Lead.WRONG_NUMBER_SELF),
  (Lead.WRONG_NUMBER_OWNER, Lead.WRONG_NUMBER_OWNER),
]

SDR_RESULT_CHOICES = [
  ("", "— انتخاب کنید —"),
  ("جلسه هماهنگ شود", "جلسه هماهنگ شود"),
  ("رد شده", "رد شده"),
  ("دوباره باید پیگیری شود", "دوباره باید پیگیری شود"),
]

SDR_PAIN_SEVERITY_CHOICES = [
  ("", "— انتخاب کنید —"),
  ("کم", "کم"),
  ("متوسط", "متوسط"),
  ("زیاد", "زیاد"),
]

SDR_BUYING_POWER_CHOICES = [
  ("", "— انتخاب کنید —"),
  ("پایین", "پایین"),
  ("متوسط", "متوسط"),
  ("بالا", "بالا"),
  ("نامشخص", "نامشخص"),
]

SDR_CONTACT_PERSON_CHOICES = [
  ("", "— انتخاب کنید —"),
  ("مدیر", "مدیر"),
  ("مالک", "مالک"),
  ("کارمند", "کارمند"),
  ("نامشخص", "نامشخص"),
]
SDR_CONTACT_NAME_REQUIRED_FOR = {"مدیر", "مالک", "کارمند"}

SDR_INTEREST_LEVEL_CHOICES = [
  ("", "— انتخاب کنید —"),
  ("سرد", "سرد"),
  ("معمولی", "معمولی"),
  ("گرم", "گرم"),
]

SDR_NEXT_ACTION_CHOICES = [
  ("", "— انتخاب کنید —"),
  ("تماس بعدی در تاریخ مشخص", "تماس بعدی در تاریخ مشخص"),
  ("انتقال به setter", "انتقال به setter"),
  ("ارسال اطلاعات (پروپوزال)", "ارسال اطلاعات (پروپوزال)"),
  ("حذف", "حذف"),
]


def _is_empty_choice(value) -> bool:
  return value is None or value == ""


class SDRLeadForm(FlaskForm):
  sdr_call_status = SelectField(
    "وضعیت تماس",
    choices=SDR_CALL_STATUS_CHOICES,
    validators=[DataRequired(message="وضعیت تماس را انتخاب کنید.")],
  )
  wrong_number_type = SelectField(
    "نوع خطای شماره",
    choices=WRONG_NUMBER_TYPE_CHOICES,
    validators=[Optional()],
  )
  wrong_number_notes = TextAreaField(
    "توضیحات شماره اشتباه",
    validators=[Optional()],
    render_kw={"placeholder": "جزئیات شماره اشتباه...", "rows": 4},
  )
  sdr_result = SelectField(
    "نتیجه تماس",
    choices=SDR_RESULT_CHOICES,
    validators=[Optional()],
  )
  sdr_rejection_reason = TextAreaField(
    "علت رد شدن",
    validators=[Optional()],
    render_kw={"placeholder": "در صورت رد شدن، علت را بنویسید...", "rows": 3},
  )
  sdr_pain_severity = SelectField(
    "شدت مشکل",
    choices=SDR_PAIN_SEVERITY_CHOICES,
    validators=[Optional()],
  )
  sdr_buying_power = SelectField(
    "بودجه / قدرت خرید",
    choices=SDR_BUYING_POWER_CHOICES,
    validators=[Optional()],
  )
  sdr_contact_person = SelectField(
    "تصمیم‌گیرنده",
    choices=SDR_CONTACT_PERSON_CHOICES,
    validators=[Optional()],
  )
  sdr_contact_name = StringField(
    "نام شخص",
    validators=[Optional(), Length(max=120)],
    render_kw={"placeholder": "نام شخص تصمیم‌گیرنده"},
  )
  sdr_interest_level = SelectField(
    "سطح علاقه‌مندی",
    choices=SDR_INTEREST_LEVEL_CHOICES,
    validators=[Optional()],
  )
  sdr_next_action = SelectField(
    "اقدام بعدی",
    choices=SDR_NEXT_ACTION_CHOICES,
    validators=[Optional()],
  )
  sdr_followup_date = JalaliDateField(
    "تاریخ پیگیری (شمسی)",
    validators=[Optional()],
  )
  sdr_summary = TextAreaField(
    "خلاصه مکالمه",
    validators=[Optional()],
    render_kw={"placeholder": "خلاصه‌ای از مکالمه با مشتری...", "rows": 5},
  )
  submit = SubmitField("ذخیره و به‌روزرسانی سرنخ")

  @property
  def call_was_answered(self) -> bool:
    return self.sdr_call_status.data == SDR_CALL_STATUS_ANSWERED

  @property
  def call_was_wrong_number(self) -> bool:
    return self.sdr_call_status.data == SDR_CALL_WRONG_NUMBER

  @property
  def call_was_unanswered(self) -> bool:
    return self.sdr_call_status.data in SDR_CALL_NO_ANSWER_STATUSES

  def _require_if_answered(self, field, message: str) -> None:
    if self.call_was_answered and _is_empty_choice(field.data):
      raise ValidationError(message)

  def validate_wrong_number_type(self, field):
    if self.call_was_wrong_number and _is_empty_choice(field.data):
      raise ValidationError("نوع خطای شماره را انتخاب کنید.")

  def validate_wrong_number_notes(self, field):
    if self.call_was_wrong_number and not (field.data or "").strip():
      raise ValidationError("توضیحات شماره اشتباه الزامی است.")

  def validate_sdr_result(self, field):
    if self.call_was_wrong_number:
      return
    self._require_if_answered(field, "نتیجه تماس را انتخاب کنید.")

  def validate_sdr_pain_severity(self, field):
    if self.call_was_wrong_number:
      return
    self._require_if_answered(field, "شدت مشکل را انتخاب کنید.")

  def validate_sdr_buying_power(self, field):
    if self.call_was_wrong_number:
      return
    self._require_if_answered(field, "قدرت خرید را انتخاب کنید.")

  def validate_sdr_contact_person(self, field):
    if self.call_was_wrong_number:
      return
    self._require_if_answered(field, "تصمیم‌گیرنده را انتخاب کنید.")

  def validate_sdr_interest_level(self, field):
    if self.call_was_wrong_number:
      return
    self._require_if_answered(field, "سطح علاقه‌مندی را انتخاب کنید.")

  def validate_sdr_contact_name(self, field):
    if self.call_was_wrong_number:
      return
    if not self.call_was_answered:
      return
    person = (self.sdr_contact_person.data or "").strip()
    name = (field.data or "").strip()
    if person in SDR_CONTACT_NAME_REQUIRED_FOR and not name:
      raise ValidationError("وارد کردن نام شخص برای تصمیم‌گیرنده انتخاب‌شده الزامی است.")

  def validate_sdr_next_action(self, field):
    if self.call_was_wrong_number:
      return
    self._require_if_answered(field, "اقدام بعدی را انتخاب کنید.")

  def validate_sdr_summary(self, field):
    if self.call_was_wrong_number or not self.call_was_answered:
      return
    text = (field.data or "").strip()
    if len(text) < 10:
      raise ValidationError("خلاصه مکالمه باید حداقل ۱۰ کاراکتر باشد.")

  def validate_sdr_rejection_reason(self, field):
    if (
      self.call_was_answered
      and self.sdr_result.data == "رد شده"
      and not (field.data or "").strip()
    ):
      raise ValidationError("در صورت رد شدن، علت رد شدن الزامی است.")

  def validate_sdr_followup_date(self, field):
    if (
      self.call_was_answered
      and self.sdr_next_action.data == "تماس بعدی در تاریخ مشخص"
      and not field.data
    ):
      raise ValidationError("برای تماس بعدی، تاریخ پیگیری الزامی است.")
