from datetime import date, datetime

from wtforms import StringField

from app.utils.jalali_dates import (
  gregorian_to_jalali_datetime_input,
  gregorian_to_jalali_input,
  parse_jalali_date,
  parse_jalali_datetime,
)


class JalaliDateField(StringField):
  is_jalali_date = True

  def __init__(self, *args, **kwargs):
    render_kw = kwargs.pop("render_kw", None) or {}
    render_kw.setdefault("autocomplete", "off")
    render_kw.setdefault("placeholder", "۱۴۰۳/۰۱/۰۱")
    render_kw.setdefault("data-jdp", "")
    kwargs["render_kw"] = render_kw
    super().__init__(*args, **kwargs)

  def _value(self):
    if self.data is None:
      return ""
    if isinstance(self.data, date) and not isinstance(self.data, datetime):
      return gregorian_to_jalali_input(self.data)
    if isinstance(self.data, datetime):
      return gregorian_to_jalali_datetime_input(self.data)
    return str(self.data)

  def process_formdata(self, valuelist):
    if valuelist and valuelist[0]:
      self.data = parse_jalali_date(valuelist[0])
    else:
      self.data = None


class JalaliDateTimeField(StringField):
  is_jalali_datetime = True

  def __init__(self, *args, **kwargs):
    render_kw = kwargs.pop("render_kw", None) or {}
    render_kw.setdefault("autocomplete", "off")
    render_kw.setdefault("placeholder", "۱۴۰۳/۰۱/۰۱ ۱۴:۳۰")
    render_kw.setdefault("data-jdp", "")
    render_kw.setdefault("data-jdp-time", "true")
    kwargs["render_kw"] = render_kw
    super().__init__(*args, **kwargs)

  def _value(self):
    if self.data is None:
      return ""
    if isinstance(self.data, (date, datetime)):
      return gregorian_to_jalali_datetime_input(
        self.data if isinstance(self.data, datetime) else datetime.combine(self.data, datetime.min.time())
      )
    return str(self.data)

  def process_formdata(self, valuelist):
    if valuelist and valuelist[0]:
      self.data = parse_jalali_datetime(valuelist[0])
    else:
      self.data = None
