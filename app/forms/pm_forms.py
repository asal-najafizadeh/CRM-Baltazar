from datetime import date

from flask_wtf import FlaskForm
from wtforms import DateField, FloatField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

MSG_REQUIRED = "این فیلد الزامی است."


class PMProposalForm(FlaskForm):
  proposal_title = StringField(
    "عنوان پروپوزال",
    validators=[
      DataRequired(message=MSG_REQUIRED),
      Length(max=200, message="حداکثر ۲۰۰ کاراکتر."),
    ],
    render_kw={"placeholder": "مثال: پکیج دیجیتال مارکتینگ ۶ ماهه"},
  )
  proposal_amount = FloatField(
    "مبلغ پیشنهادی (تومان)",
    validators=[
      DataRequired(message=MSG_REQUIRED),
      NumberRange(min=0, message="مبلغ باید عدد مثبت باشد."),
    ],
    render_kw={"placeholder": "150000000", "step": "1000"},
  )
  proposal_date = DateField(
    "تاریخ پروپوزال",
    validators=[DataRequired(message=MSG_REQUIRED)],
    format="%Y-%m-%d",
    default=date.today,
    render_kw={"type": "date"},
  )
  proposal_details = TextAreaField(
    "جزئیات و توضیحات پروپوزال",
    validators=[
      DataRequired(message=MSG_REQUIRED),
      Length(min=10, message="حداقل ۱۰ کاراکتر وارد کنید."),
    ],
    render_kw={
      "placeholder": "شرح کامل خدمات، زمان‌بندی، شرایط پرداخت و...",
      "rows": 6,
    },
  )
  submit = SubmitField("ثبت و ارسال پروپوزال به SDR")
