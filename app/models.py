from datetime import datetime, timezone

from flask_login import UserMixin

from app.extensions import bcrypt, db


def utcnow():
  return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
  __tablename__ = "users"

  id = db.Column(db.Integer, primary_key=True)
  username = db.Column(db.String(80), unique=True, nullable=False, index=True)
  password_hash = db.Column(db.String(128), nullable=False)
  password_plain = db.Column(db.String(128), nullable=True)
  role = db.Column(db.String(20), nullable=False, index=True)
  is_active = db.Column(db.Boolean, default=True, nullable=False)
  score = db.Column(db.Integer, default=0, nullable=False)
  created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

  leads_created = db.relationship(
    "Lead",
    back_populates="created_by",
    foreign_keys="Lead.created_by_id",
    lazy="dynamic",
  )
  sdr_leads_handled = db.relationship(
    "Lead",
    back_populates="sdr_agent",
    foreign_keys="Lead.sdr_agent_id",
    lazy="dynamic",
  )
  setter_leads_handled = db.relationship(
    "Lead",
    back_populates="setter_agent",
    foreign_keys="Lead.setter_agent_id",
    lazy="dynamic",
  )
  closer_leads_handled = db.relationship(
    "Lead",
    back_populates="closer_agent",
    foreign_keys="Lead.closer_agent_id",
    lazy="dynamic",
  )
  sdr_leads_assigned = db.relationship(
    "Lead",
    back_populates="assigned_sdr",
    foreign_keys="Lead.assigned_sdr_id",
    lazy="dynamic",
  )
  pm_leads_handled = db.relationship(
    "Lead",
    back_populates="pm_agent",
    foreign_keys="Lead.pm_agent_id",
    lazy="dynamic",
  )

  ROLES = ("admin", "lh", "sdr", "setter", "pm", "closer")

  def set_password(self, password: str) -> None:
    self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    self.password_plain = password

  def check_password(self, password: str) -> bool:
    return bcrypt.check_password_hash(self.password_hash, password)

  def __repr__(self) -> str:
    return f"<User {self.username} ({self.role})>"


class Lead(db.Model):
  """Lead progresses through stages 1–5; may close as won/lost or disqualify at SDR."""

  __tablename__ = "leads"

  id = db.Column(db.Integer, primary_key=True)
  current_stage = db.Column(db.Integer, default=1, nullable=False, index=True)
  pipeline_status = db.Column(
    db.String(20), default="active", nullable=False, index=True
  )  # active | disqualified | closed_won | closed_lost

  created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
  updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)
  admin_deleted_at = db.Column(db.DateTime, index=True)
  admin_deleted_by_id = db.Column(
    db.Integer, db.ForeignKey("users.id"), nullable=True, index=True
  )
  admin_deleted_by = db.relationship(
    "User",
    foreign_keys=[admin_deleted_by_id],
  )

  created_by_id = db.Column(
    db.Integer, db.ForeignKey("users.id"), nullable=True, index=True
  )
  created_by = db.relationship(
    "User",
    back_populates="leads_created",
    foreign_keys=[created_by_id],
  )

  # --- Stage 1: LH (Headhunter) ---
  company_name = db.Column(db.String(200), nullable=False, index=True)
  phone_number = db.Column(db.String(40), nullable=False)
  phone_number_2 = db.Column(db.String(40))
  phone_number_3 = db.Column(db.String(40))
  phone_primary = db.Column(db.Integer, default=1, nullable=False)
  business_type = db.Column(db.String(80), nullable=False)
  business_type_custom = db.Column(db.String(120))
  source = db.Column(db.String(80), nullable=False)
  source_custom = db.Column(db.String(120))
  website = db.Column(db.String(255))
  telegram = db.Column(db.String(120))
  instagram = db.Column(db.String(120))
  address = db.Column(db.Text)
  description = db.Column(db.Text)

  # --- Stage 2: SDR ---
  assigned_sdr_id = db.Column(
    db.Integer, db.ForeignKey("users.id"), nullable=True, index=True
  )
  assigned_sdr = db.relationship(
    "User",
    back_populates="sdr_leads_assigned",
    foreign_keys=[assigned_sdr_id],
  )
  assigned_sdr_at = db.Column(db.DateTime)
  sdr_call_status = db.Column(db.String(40))
  sdr_result = db.Column(db.String(60))
  sdr_rejection_reason = db.Column(db.Text)
  sdr_pain_severity = db.Column(db.String(20))
  sdr_buying_power = db.Column(db.String(20))
  sdr_contact_person = db.Column(db.String(30))
  sdr_contact_name = db.Column(db.String(120))
  sdr_interest_level = db.Column(db.String(20))
  sdr_next_action = db.Column(db.String(60), index=True)
  sdr_followup_date = db.Column(db.Date)
  wrong_number_type = db.Column(db.String(60))
  wrong_number_notes = db.Column(db.Text)
  sdr_summary = db.Column(db.Text)
  sdr_agent_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
  sdr_agent = db.relationship(
    "User",
    back_populates="sdr_leads_handled",
    foreign_keys=[sdr_agent_id],
  )
  sdr_processed_at = db.Column(db.DateTime)
  sdr_routed_to_pm = db.Column(db.Boolean, default=False, nullable=False)
  pm_proposal_ready = db.Column(db.Boolean, default=False, nullable=False)
  proposal_status = db.Column(
    db.String(20), default="pending", nullable=False, index=True
  )  # pending | sent

  # --- Stage 3: Setter ---
  setter_status = db.Column(db.String(50), index=True)
  setter_meeting_date = db.Column(db.DateTime)
  setter_meeting_location = db.Column(db.Text)
  setter_notes = db.Column(db.Text)
  setter_agent_id = db.Column(
    db.Integer, db.ForeignKey("users.id"), nullable=True, index=True
  )
  setter_agent = db.relationship(
    "User",
    back_populates="setter_leads_handled",
    foreign_keys=[setter_agent_id],
  )

  # --- Stage 4: PM ---
  pm_agent_id = db.Column(
    db.Integer, db.ForeignKey("users.id"), nullable=True, index=True
  )
  pm_agent = db.relationship(
    "User",
    back_populates="pm_leads_handled",
    foreign_keys=[pm_agent_id],
  )
  proposal_title = db.Column(db.String(200))
  proposal_amount = db.Column(db.Float)
  proposal_details = db.Column(db.Text)
  proposal_date = db.Column(db.Date)

  # --- Stage 5: Closer ---
  closer_meeting_status = db.Column(db.String(30))
  closer_cooperation_status = db.Column(db.String(30), index=True)
  closer_followup_date = db.Column(db.DateTime)
  closer_notes = db.Column(db.Text)
  closer_agent_id = db.Column(
    db.Integer, db.ForeignKey("users.id"), nullable=True, index=True
  )
  closer_agent = db.relationship(
    "User",
    back_populates="closer_leads_handled",
    foreign_keys=[closer_agent_id],
  )
  deal_outcome = db.Column(db.String(20))  # won | lost
  closing_notes = db.Column(db.Text)
  closed_at = db.Column(db.DateTime)

  SDR_NEXT_ACTION_DELETE = "حذف"
  SDR_NEXT_ACTION_SETTER = "انتقال به setter"
  SDR_NEXT_ACTION_PROPOSAL = "ارسال اطلاعات (پروپوزال)"
  SDR_NEXT_ACTION_FOLLOWUP = "تماس بعدی در تاریخ مشخص"
  SDR_RESULT_REJECTED = "رد شده"
  SDR_RESULT_RECALL = "دوباره باید پیگیری شود"
  SDR_CALL_WRONG_NUMBER = "شماره اشتباه"
  WRONG_NUMBER_SELF = "خود شماره اشتباه بود"
  WRONG_NUMBER_OWNER = "صاحب شماره اشتباه بود"

  SETTER_STATUS_APPROVED = "تایید شده"
  SETTER_STATUS_REJECTED = "رد شده"
  SETTER_STATUS_UNCERTAIN = "نامشخص نیاز به پیگیری مجدد"

  CLOSER_MEETING_HELD = "برگزار شد"
  CLOSER_MEETING_NOT_HELD = "برگزار نشد"
  CLOSER_COOP_SUCCESS = "موفق"
  CLOSER_COOP_FOLLOWUP = "پیگیری مجدد"
  CLOSER_COOP_REJECT = "رد"

  @classmethod
  def active_only(cls):
    """فیلتر لیدهای حذف‌نشده توسط ادمین (برای لیست‌های عملیاتی)."""
    return cls.admin_deleted_at.is_(None)

  @property
  def is_admin_deleted(self) -> bool:
    return self.admin_deleted_at is not None

  @property
  def lh_creator_username(self) -> str:
    if self.created_by:
      return self.created_by.username
    return "نامشخص"

  @property
  def sdr_agent_username(self) -> str:
    if self.sdr_agent:
      return self.sdr_agent.username
    return "—"

  @property
  def assigned_sdr_username(self) -> str:
    if self.assigned_sdr:
      return self.assigned_sdr.username
    return "—"

  @property
  def needs_lh_wrong_number_fix(self) -> bool:
    return (
      self.current_stage == 1
      and self.sdr_call_status == self.SDR_CALL_WRONG_NUMBER
    )

  @property
  def setter_agent_username(self) -> str:
    if self.setter_agent:
      return self.setter_agent.username
    return "—"

  @property
  def closer_agent_username(self) -> str:
    if self.closer_agent:
      return self.closer_agent.username
    return "—"

  @property
  def admin_deleted_by_username(self) -> str:
    if self.admin_deleted_by:
      return self.admin_deleted_by.username
    return "ادمین"

  @property
  def archive_reason_display(self) -> str:
    """دلیل نمایش در لیست بایگانی."""
    if self.is_admin_deleted:
      return "حذف توسط ادمین"
    if self.sdr_next_action == self.SDR_NEXT_ACTION_DELETE:
      return "حذف SDR"
    if self.sdr_result == self.SDR_RESULT_REJECTED:
      return "رد شده توسط SDR"
    if self.setter_status == self.SETTER_STATUS_REJECTED:
      return "رد Setter"
    if self.closer_cooperation_status == self.CLOSER_COOP_REJECT:
      return "رد Closer"
    if self.pipeline_status == "closed_lost":
      return "بسته‌شده (بازنده)"
    if self.pipeline_status == "disqualified":
      return "رد شده"
    return "بایگانی"

  @property
  def is_closer_new_inbound(self) -> bool:
    return (
      self.current_stage == 5
      and self.pipeline_status == "active"
      and self.closer_cooperation_status != self.CLOSER_COOP_REJECT
      and self.closer_cooperation_status != self.CLOSER_COOP_FOLLOWUP
      and not self.closer_cooperation_status
    )

  @property
  def is_closer_followup_queue(self) -> bool:
    return (
      self.current_stage == 5
      and self.pipeline_status == "active"
      and self.closer_cooperation_status == self.CLOSER_COOP_FOLLOWUP
    )

  @property
  def is_deal_closed(self) -> bool:
    return self.pipeline_status in ("closed_won", "closed_lost")

  @property
  def is_sdr_archived(self) -> bool:
    return self.sdr_next_action == self.SDR_NEXT_ACTION_DELETE

  @property
  def is_sdr_followup_queue(self) -> bool:
    if self.is_sdr_archived:
      return False
    return (
      self.sdr_result == self.SDR_RESULT_RECALL
      or self.sdr_next_action == self.SDR_NEXT_ACTION_FOLLOWUP
    )

  @property
  def is_sdr_new_inbound(self) -> bool:
    return (
      self.current_stage == 2
      and self.pipeline_status == "active"
      and not self.is_admin_deleted
      and not self.is_sdr_archived
      and not self.sdr_next_action
    )

  @property
  def is_qualified_for_setter(self) -> bool:
    return (
      self.sdr_next_action == self.SDR_NEXT_ACTION_SETTER
      and self.current_stage >= 3
    )

  @property
  def is_setter_new_inbound(self) -> bool:
    return (
      self.current_stage == 3
      and self.pipeline_status == "active"
      and self.sdr_next_action == self.SDR_NEXT_ACTION_SETTER
      and self.setter_status != self.SETTER_STATUS_REJECTED
      and not self.setter_status
    )

  @property
  def is_setter_followup_queue(self) -> bool:
    return self.setter_status == self.SETTER_STATUS_UNCERTAIN

  @property
  def is_setter_rejected(self) -> bool:
    return self.setter_status == self.SETTER_STATUS_REJECTED

  @property
  def is_proposal_sent(self) -> bool:
    return self.proposal_status == "sent" and self.pm_proposal_ready

  @property
  def needs_sdr_proposal_followup(self) -> bool:
    return self.sdr_routed_to_pm and self.is_proposal_sent

  @property
  def proposal_link_display(self) -> str:
    if self.website:
      return self.website
    if self.is_proposal_sent and self.proposal_title:
      return self.proposal_title
    return "—"

  @property
  def business_type_display(self) -> str:
    if self.business_type == "سایر" and self.business_type_custom:
      return self.business_type_custom
    return self.business_type

  @property
  def source_display(self) -> str:
    if self.source == "سایر" and self.source_custom:
      return self.source_custom
    return self.source

  @property
  def all_phone_numbers(self) -> list[str]:
    """همه شماره‌های ثبت‌شده (اصلی و پشتیبان) به ترتیب نمایش."""
    nums = []
    for n in (self.phone_number, self.phone_number_2, self.phone_number_3):
      if n and str(n).strip():
        nums.append(str(n).strip())
    return nums

  @property
  def primary_phone_number(self) -> str:
    idx = self.phone_primary or 1
    phones = [
      self.phone_number,
      self.phone_number_2,
      self.phone_number_3,
    ]
    if 1 <= idx <= 3 and phones[idx - 1]:
      return phones[idx - 1]
    return self.phone_number

  @property
  def phones_display(self) -> str:
    """متن نمایشی شماره‌ها با برچسب طلایی برای اصلی."""
    parts = []
    labels = {
      1: ("phone_number", "اصلی (طلایی)"),
      2: ("phone_number_2", "پشتیبان"),
      3: ("phone_number_3", "پشتیبان"),
    }
    primary = self.phone_primary or 1
    for i in (1, 2, 3):
      num = getattr(self, labels[i][0], None)
      if not num:
        continue
      tag = labels[i][1]
      if i == primary:
        tag = "اصلی (طلایی)"
      parts.append(f"{tag}: {num}")
    return " · ".join(parts) if parts else self.phone_number

  @property
  def sdr_queue_since(self):
    """تاریخ ورود لید به صف SDR (برای نمایش در هشدار rollover)."""
    return self.assigned_sdr_at or self.created_at

  @property
  def is_sdr_uncalled_carryover(self) -> bool:
    """لید اختصاص‌یافته در روز قبل که هنوز گزارش تماس ثبت نشده."""
    from datetime import timezone

    from app.utils.jalali_dates import TEHRAN, today_gregorian_date

    if not self.assigned_sdr_id:
      return False
    if self.is_admin_deleted:
      return False
    if self.current_stage != 2 or self.pipeline_status != "active":
      return False
    if self.is_sdr_archived:
      return False
    if self.sdr_next_action:
      return False
    if self.sdr_call_status:
      return False
    entry = self.sdr_queue_since
    if not entry:
      return False
    if entry.tzinfo is None:
      entry = entry.replace(tzinfo=timezone.utc)
    entry_date = entry.astimezone(TEHRAN).date()
    return entry_date < today_gregorian_date()

  @property
  def stage_label(self) -> str:
    from flask import current_app

    if self.pipeline_status.startswith("closed"):
      outcome = "برنده" if self.deal_outcome == "won" else "بازنده"
      return f"بسته‌شده ({outcome})"
    if self.pipeline_status == "disqualified":
      return "رد شده"
    return current_app.config["STAGE_LABELS"].get(self.current_stage, "نامشخص")

  @property
  def master_status_display(self) -> str:
    """نمایش مرحله/وضعیت برای جدول مدیریت کل لیدها."""
    if self.is_admin_deleted:
      return "حذف توسط ادمین"
    if self.pipeline_status == "closed_won":
      return "موفق"
    if self.pipeline_status == "closed_lost":
      return "بازنده"
    if self.pipeline_status == "disqualified":
      return "رد شده"
    from flask import current_app

    stage_name = current_app.config["STAGE_LABELS"].get(
      self.current_stage, "نامشخص"
    )
    return f"مرحله {self.current_stage} — {stage_name}"

  def advance_to_stage(self, stage: int) -> None:
    self.current_stage = stage
    self.updated_at = utcnow()

  def __repr__(self) -> str:
    return f"<Lead {self.company_name} stage={self.current_stage}>"
