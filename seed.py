"""
Seed the database with an admin user, one user per pipeline role, and sample leads.

Usage (from project root, with venv activated):
  python seed.py
  python seed.py --reset   # drop all tables and re-create (schema changes)
"""

import sys

from app import create_app
from app.extensions import db
from datetime import datetime, timedelta, timezone

from app.models import Lead, User
from app.services.sdr_assignment import assign_sdr_to_lead


def seed(reset: bool = False):
  app = create_app()
  with app.app_context():
    if reset:
      print("  ! Dropping all tables...")
      db.drop_all()
      db.create_all()

    users_spec = [
      ("admin", "admin", "admin123"),
      ("lh_user", "lh", "lh12345"),
      ("sdr_user", "sdr", "sdr12345"),
      ("setter_user", "setter", "setter12345"),
      ("pm_user", "pm", "pm12345"),
      ("closer_user", "closer", "closer12345"),
    ]

    created_users = {}
    for username, role, password in users_spec:
      user = User.query.filter_by(username=username).first()
      if not user:
        user = User(username=username, role=role)
        user.set_password(password)
        db.session.add(user)
        print(f"  + Created user: {username} ({role})")
      else:
        if reset or not user.password_plain:
          user.set_password(password)
          print(f"  ~ Updated password for: {username}")
        else:
          print(f"  = User exists: {username}")
      created_users[role] = user

    db.session.flush()

    if Lead.query.count() == 0:
      lh = created_users["lh"]
      samples = [
        Lead(
          company_name="کلینیک زیبای رز",
          phone_number="09121234567",
          business_type="کلینیک زیبایی",
          source="نشان",
          website="https://rose-clinic.example",
          description="سرنخ نمونه برای تست SDR",
          current_stage=2,
          pipeline_status="active",
          created_by_id=lh.id,
        ),
        Lead(
          company_name="کافه آرت",
          phone_number="02188776655",
          business_type="کافه",
          source="دیوار",
          current_stage=2,
          pipeline_status="active",
          created_by_id=lh.id,
        ),
        Lead(
          company_name="فروشگاه مد و لباس",
          phone_number="09129876543",
          business_type="فروشگاه",
          source="معرفی",
          website="https://mode-shop.example",
          description="آماده تست Setter",
          current_stage=3,
          pipeline_status="active",
          sdr_next_action=Lead.SDR_NEXT_ACTION_SETTER,
          sdr_result="جلسه هماهنگ شود",
          sdr_pain_severity="متوسط",
          sdr_buying_power="بالا",
          sdr_contact_person="مالک",
          sdr_interest_level="گرم",
          sdr_summary="مشتری علاقه‌مند به جلسه حضوری برای پکیج مارکتینگ است.",
          sdr_call_status="پاسخ داد",
          created_by_id=lh.id,
        ),
        Lead(
          company_name="استودیو طراحی پلاس",
          phone_number="09131112233",
          business_type="خدماتی",
          source="گوگل مپ",
          website="https://design-plus.example",
          instagram="@designplus",
          description="آماده تست Closer",
          current_stage=5,
          pipeline_status="active",
          sdr_next_action=Lead.SDR_NEXT_ACTION_SETTER,
          sdr_result="جلسه هماهنگ شود",
          sdr_pain_severity="زیاد",
          sdr_buying_power="متوسط",
          sdr_contact_person="مدیر",
          sdr_interest_level="گرم",
          sdr_summary="نیاز فوری به راه‌اندازی کمپین برندینگ.",
          sdr_call_status="پاسخ داد",
          setter_status=Lead.SETTER_STATUS_APPROVED,
          setter_meeting_location="دفتر مرکزی — خیابان ولیعصر",
          setter_notes="جلسه حضوری با مدیرعامل هماهنگ شد.",
          setter_meeting_date=datetime.now(timezone.utc) + timedelta(days=3),
          created_by_id=lh.id,
        ),
      ]
      sdr = created_users["sdr"]
      for lead in samples:
        if lead.current_stage >= 2:
          assign_sdr_to_lead(lead)
        if lead.sdr_call_status:
          lead.sdr_agent_id = sdr.id
      db.session.add_all(samples)
      print(f"  + Created {len(samples)} sample leads (with SDR assignment)")
    else:
      print("  = Leads already present, skipping samples")

    db.session.commit()
    print("\nSeed complete. Login credentials (change in production):")
    print("  admin / admin123")
    print("  lh_user / lh12345  |  sdr_user / sdr12345  |  setter_user / setter12345")
    print("  pm_user / pm12345  |  closer_user / closer12345")


if __name__ == "__main__":
  reset = "--reset" in sys.argv
  seed(reset=reset)
