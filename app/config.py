import os
from pathlib import Path


class Config:
  """Base configuration."""

  BASE_DIR = Path(__file__).resolve().parent.parent
  SECRET_KEY = os.environ.get("SECRET_KEY", "dev-change-me-in-production")
  SQLALCHEMY_DATABASE_URI = os.environ.get(
    "DATABASE_URL",
    "sqlite:///" + str(BASE_DIR / "instance" / "crm.db"),
  )
  SQLALCHEMY_TRACK_MODIFICATIONS = False
  WTF_CSRF_ENABLED = True
  MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB for Excel uploads

  STAGE_LABELS = {
    1: "شکارچی سرنخ (LH)",
    2: "SDR",
    3: "ستر",
    4: "مدیر پیشنهاد (PM)",
    5: "کلوزر",
  }

  ROLE_LABELS = {
    "admin": "مدیر سیستم",
    "lh": "شکارچی سرنخ",
    "sdr": "SDR",
    "setter": "ستر",
    "pm": "مدیر پیشنهاد",
    "closer": "کلوزر",
  }

  PIPELINE_STATUS_LABELS = {
    "active": "فعال",
    "disqualified": "رد شده",
    "closed_won": "برنده",
    "closed_lost": "بازنده",
  }

  ROLE_DASHBOARD = {
    "admin": "admin.dashboard",
    "lh": "lh.dashboard",
    "sdr": "sdr.dashboard",
    "setter": "setter.dashboard",
    "pm": "pm.dashboard",
    "closer": "closer.dashboard",
  }
