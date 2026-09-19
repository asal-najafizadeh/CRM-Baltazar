from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, ValidationError

from app.utils.phone import (
  DUPLICATE_PHONE_MESSAGE,
  format_phone_for_storage,
  phone_number_exists,
)

MSG_REQUIRED = "این فیلد الزامی است."
MSG_MAX = "حداکثر %(max)d کاراکتر مجاز است."

BUSINESS_TYPE_CHOICES = [
  ("", "— انتخاب کنید —"),
  ("کلینیک زیبایی", "کلینیک زیبایی"),
  ("رستوران", "رستوران"),
  ("کافه", "کافه"),
  ("فروشگاه", "فروشگاه"),
  ("خدماتی", "خدماتی"),
  ("آموزشی", "آموزشی"),
  ("تولیدی", "تولیدی"),
  ("سایر", "سایر"),
]

SOURCE_CHOICES = [
  ("", "— انتخاب کنید —"),
  ("نشان", "نشان"),
  ("دیوار", "دیوار"),
  ("گوگل مپ", "گوگل مپ"),
  ("معرفی", "معرفی"),
  ("سایر", "سایر"),
]

INPUT_CLASS = (
  "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm "
  "focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
)
SELECT_CLASS = INPUT_CLASS
TEXTAREA_CLASS = INPUT_CLASS + " min-h-[100px]"


class LHLeadForm(FlaskForm):
  _exclude_lead_id = None

  company_name = StringField(
    "نام کسب و کار",
    validators=[
      DataRequired(message=MSG_REQUIRED),
      Length(max=200, message=MSG_MAX),
    ],
    render_kw={"placeholder": "مثال: کلینیک زیبای رز"},
  )
  phone_number = StringField(
    "شماره تماس اصلی (طلایی)",
    validators=[
      DataRequired(message=MSG_REQUIRED),
      Length(max=40, message=MSG_MAX),
    ],
    render_kw={"placeholder": "۰۹۱۲۱۲۳۴۵۶۷", "id": "phone_primary_input"},
  )
  business_type = SelectField(
    "نوع کسب و کار",
    choices=BUSINESS_TYPE_CHOICES,
    validators=[DataRequired(message="لطفاً نوع کسب و کار را انتخاب کنید.")],
  )
  business_type_custom = StringField(
    "نوع کسب و کار جدید",
    validators=[Optional(), Length(max=120, message=MSG_MAX)],
    render_kw={"placeholder": "نوع کسب‌وکار را وارد کنید"},
  )
  source = SelectField(
    "منبع",
    choices=SOURCE_CHOICES,
    validators=[DataRequired(message="لطفاً منبع را انتخاب کنید.")],
  )
  source_custom = StringField(
    "نام منبع جدید",
    validators=[Optional(), Length(max=120, message=MSG_MAX)],
    render_kw={"placeholder": "نام منبع را وارد کنید"},
  )
  website = StringField(
    "آدرس سایت",
    validators=[Optional(), Length(max=255, message=MSG_MAX)],
    render_kw={"placeholder": "https://example.com"},
  )
  telegram = StringField(
    "تلگرام",
    validators=[Optional(), Length(max=120, message=MSG_MAX)],
    render_kw={"placeholder": "@username"},
  )
  instagram = StringField(
    "اینستاگرام",
    validators=[Optional(), Length(max=120, message=MSG_MAX)],
    render_kw={"placeholder": "@username"},
  )
  address = TextAreaField(
    "آدرس محل",
    validators=[Optional()],
    render_kw={"placeholder": "آدرس کامل محل کسب و کار", "rows": 3},
  )
  description = TextAreaField(
    "توضیحات کلی",
    validators=[Optional()],
    render_kw={"placeholder": "هر توضیح تکمیلی درباره این سرنخ...", "rows": 4},
  )
  submit = SubmitField("ثبت و ارسال به SDR")

  def validate_phone_number(self, field):
    field.data = format_phone_for_storage(field.data)
    if phone_number_exists(field.data, exclude_lead_id=self._exclude_lead_id):
      raise ValidationError(DUPLICATE_PHONE_MESSAGE)

  def validate_business_type_custom(self, field):
    if self.business_type.data == "سایر" and not (field.data or "").strip():
      raise ValidationError("وقتی نوع کسب‌وکار «سایر» است، وارد کردن نوع کسب‌وکار جدید الزامی است.")

  def validate_source_custom(self, field):
    if self.source.data == "سایر" and not (field.data or "").strip():
      raise ValidationError("وقتی منبع «سایر» است، وارد کردن نام منبع جدید الزامی است.")


class LHWrongNumberFixForm(FlaskForm):
  _exclude_lead_id = None

  phone_number = StringField(
    "شماره تماس اصلاح‌شده",
    validators=[
      DataRequired(message=MSG_REQUIRED),
      Length(max=40, message=MSG_MAX),
    ],
    render_kw={"placeholder": "شماره صحیح را وارد کنید"},
  )
  submit = SubmitField("ثبت مجدد و ارسال به SDR")

  def validate_phone_number(self, field):
    field.data = format_phone_for_storage(field.data)
    if phone_number_exists(field.data, exclude_lead_id=self._exclude_lead_id):
      raise ValidationError(DUPLICATE_PHONE_MESSAGE)
