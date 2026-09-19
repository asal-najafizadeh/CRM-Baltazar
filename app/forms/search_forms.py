from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField
from wtforms.validators import Optional

from app.choices import BUSINESS_TYPE_FILTER_CHOICES, SOURCE_FILTER_CHOICES


class LeadSearchForm(FlaskForm):
  company_name = StringField(
    "نام کسب و کار",
    validators=[Optional()],
    render_kw={"placeholder": "جستجوی متنی (بخشی از نام)..."},
  )
  business_type = SelectField(
    "نوع کسب و کار",
    choices=BUSINESS_TYPE_FILTER_CHOICES,
    validators=[Optional()],
  )
  source = SelectField(
    "منبع",
    choices=SOURCE_FILTER_CHOICES,
    validators=[Optional()],
  )
  submit = SubmitField("جستجو و فیلتر")
