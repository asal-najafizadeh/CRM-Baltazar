from datetime import datetime

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import (
  PasswordField,
  SelectField,
  SelectMultipleField,
  StringField,
  SubmitField,
  TextAreaField,
)
from wtforms.validators import DataRequired, Length, Optional

from app.forms.jalali_fields import JalaliDateField, JalaliDateTimeField


class UserForm(FlaskForm):
  username = StringField(
    "نام کاربری",
    validators=[
      DataRequired(message="نام کاربری الزامی است."),
      Length(max=80),
    ],
  )
  password = PasswordField(
    "رمز عبور",
    validators=[
      DataRequired(message="رمز عبور الزامی است."),
      Length(min=6, max=128, message="رمز عبور باید حداقل ۶ کاراکتر باشد."),
    ],
  )
  role = SelectField(
    "نقش",
    choices=[
      ("admin", "مدیر سیستم"),
      ("lh", "شکارچی سرنخ (LH)"),
      ("sdr", "SDR"),
      ("setter", "ستر"),
      ("pm", "مدیر پیشنهاد (PM)"),
      ("closer", "کلوزر"),
    ],
    validators=[DataRequired(message="انتخاب نقش الزامی است.")],
  )
  submit = SubmitField("ایجاد کاربر")


class UserEditForm(FlaskForm):
  username = StringField(
    "نام کاربری",
    validators=[DataRequired(message="نام کاربری الزامی است."), Length(max=80)],
  )
  password = PasswordField(
    "رمز عبور جدید",
    validators=[Optional(), Length(min=6, max=128, message="رمز عبور باید حداقل ۶ کاراکتر باشد.")],
  )
  role = SelectField(
    "نقش",
    choices=[
      ("admin", "مدیر سیستم"),
      ("lh", "شکارچی سرنخ (LH)"),
      ("sdr", "SDR"),
      ("setter", "ستر"),
      ("pm", "مدیر پیشنهاد (PM)"),
      ("closer", "کلوزر"),
    ],
    validators=[DataRequired(message="انتخاب نقش الزامی است.")],
  )
  submit = SubmitField("ذخیره تغییرات")


class ExcelBulkImportForm(FlaskForm):
  excel_file = FileField(
    "فایل اکسل",
    validators=[
      FileRequired(message="لطفاً یک فایل اکسل انتخاب کنید."),
      FileAllowed(
        ["xlsx", "xls"],
        message="فقط فایل‌های با پسوند xlsx یا xls مجاز هستند.",
      ),
    ],
  )
  submit = SubmitField("آپلود و واردسازی سرنخ‌ها")


class LeadEditForm(FlaskForm):
  company_name = StringField("نام کسب‌وکار", validators=[DataRequired(), Length(max=200)])
  phone_number = StringField("شماره تماس اصلی (طلایی)", validators=[DataRequired(), Length(max=40)])
  phone_number_2 = StringField("شماره پشتیبان ۲", validators=[Optional(), Length(max=40)])
  phone_number_3 = StringField("شماره پشتیبان ۳", validators=[Optional(), Length(max=40)])
  phone_primary = SelectField(
    "شماره اصلی (طلایی)",
    choices=[("1", "شماره ۱"), ("2", "شماره ۲"), ("3", "شماره ۳")],
    validators=[Optional()],
    coerce=int,
    default=1,
  )
  business_type = StringField("نوع کسب‌وکار", validators=[DataRequired(), Length(max=80)])
  source = StringField("منبع", validators=[DataRequired(), Length(max=80)])
  website = StringField("وب‌سایت", validators=[Optional(), Length(max=255)])
  telegram = StringField("تلگرام", validators=[Optional(), Length(max=120)])
  instagram = StringField("اینستاگرام", validators=[Optional(), Length(max=120)])
  address = TextAreaField("آدرس", validators=[Optional()])
  description = TextAreaField("توضیحات اولیه", validators=[Optional()])
  current_stage = SelectField(
    "مرحله جاری",
    choices=[("1", "مرحله ۱"), ("2", "مرحله ۲"), ("3", "مرحله ۳"), ("4", "مرحله ۴"), ("5", "مرحله ۵")],
    validators=[DataRequired()],
    coerce=int,
  )
  pipeline_status = SelectField(
    "وضعیت پایپ‌لاین",
    choices=[
      ("active", "فعال"),
      ("disqualified", "رد شده"),
      ("closed_won", "موفق"),
      ("closed_lost", "ناموفق"),
    ],
    validators=[DataRequired()],
  )
  assigned_sdr_id = SelectField("SDR اختصاص داده‌شده", validators=[Optional()], coerce=int, choices=[])

  sdr_call_status = StringField("وضعیت تماس SDR", validators=[Optional(), Length(max=40)])
  sdr_result = StringField("نتیجه SDR", validators=[Optional(), Length(max=60)])
  sdr_rejection_reason = TextAreaField("علت رد شدن SDR", validators=[Optional()])
  sdr_pain_severity = StringField("شدت مشکل", validators=[Optional(), Length(max=20)])
  sdr_buying_power = StringField("قدرت خرید", validators=[Optional(), Length(max=20)])
  sdr_contact_person = StringField("تصمیم‌گیرنده", validators=[Optional(), Length(max=30)])
  sdr_contact_name = StringField("نام شخص تصمیم‌گیرنده", validators=[Optional(), Length(max=120)])
  sdr_interest_level = StringField("سطح علاقه‌مندی", validators=[Optional(), Length(max=20)])
  sdr_next_action = StringField("اقدام بعدی SDR", validators=[Optional(), Length(max=60)])
  sdr_followup_date = JalaliDateField("تاریخ پیگیری SDR", validators=[Optional()])
  wrong_number_type = StringField("نوع خطای شماره", validators=[Optional(), Length(max=60)])
  wrong_number_notes = TextAreaField("توضیحات شماره اشتباه", validators=[Optional()])
  sdr_summary = TextAreaField("خلاصه مکالمه SDR", validators=[Optional()])
  sdr_agent_id = SelectField("عامل SDR", validators=[Optional()], coerce=int, choices=[])

  setter_status = StringField("وضعیت Setter", validators=[Optional(), Length(max=50)])
  setter_meeting_date = JalaliDateTimeField("زمان جلسه Setter", validators=[Optional()])
  setter_meeting_location = TextAreaField("مکان جلسه Setter", validators=[Optional()])
  setter_notes = TextAreaField("یادداشت Setter", validators=[Optional()])
  setter_agent_id = SelectField("عامل Setter", validators=[Optional()], coerce=int, choices=[])

  pm_agent_id = SelectField("عامل PM", validators=[Optional()], coerce=int, choices=[])
  proposal_title = StringField("عنوان پروپوزال", validators=[Optional(), Length(max=200)])
  proposal_amount = StringField("مبلغ پروپوزال (عدد)", validators=[Optional(), Length(max=50)])
  proposal_details = TextAreaField("جزئیات پروپوزال", validators=[Optional()])
  proposal_date = JalaliDateField("تاریخ پروپوزال", validators=[Optional()])

  closer_meeting_status = StringField("وضعیت جلسه Closer", validators=[Optional(), Length(max=30)])
  closer_cooperation_status = StringField("وضعیت همکاری", validators=[Optional(), Length(max=30)])
  closer_followup_date = JalaliDateTimeField("تاریخ پیگیری Closer", validators=[Optional()])
  closer_notes = TextAreaField("یادداشت Closer", validators=[Optional()])
  closer_agent_id = SelectField("عامل Closer", validators=[Optional()], coerce=int, choices=[])
  deal_outcome = SelectField(
    "نتیجه نهایی قرارداد",
    choices=[("", "—"), ("won", "موفق"), ("lost", "ناموفق")],
    validators=[Optional()],
  )
  closing_notes = TextAreaField("یادداشت نهایی", validators=[Optional()])
  closed_at = JalaliDateTimeField("زمان بسته‌شدن پرونده", validators=[Optional()])
  submit = SubmitField("ذخیره تغییرات لید")

  def parse_proposal_amount(self):
    text = (self.proposal_amount.data or "").strip()
    if not text:
      return None
    cleaned = text.replace(",", "").replace("،", "")
    return float(cleaned)


class DistributeLeadsForm(FlaskForm):
  sdr_ids = SelectMultipleField("انتخاب SDRها", coerce=int, validators=[DataRequired(message="حداقل یک SDR انتخاب کنید.")], choices=[])
  submit = SubmitField("تقسیم و توزیع مساوی لیدهای امروز")


class DistributeBacklogLeadsForm(FlaskForm):
  sdr_ids = SelectMultipleField("انتخاب SDRها", coerce=int, validators=[DataRequired(message="حداقل یک SDR انتخاب کنید.")], choices=[])
  submit = SubmitField("تقسیم و توزیع مساوی لیدهای معوقه")
