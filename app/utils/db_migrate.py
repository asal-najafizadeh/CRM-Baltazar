"""افزودن ستون‌های جدید به SQLite بدون حذف داده (create_all فقط جدول جدید می‌سازد)."""

from sqlalchemy import inspect, text

from app.extensions import db


# (table, column, SQL type for SQLite ALTER)
SCHEMA_PATCHES = [
  ("users", "score", "INTEGER NOT NULL DEFAULT 0"),
  ("users", "password_plain", "VARCHAR(128)"),
  ("users", "is_active", "BOOLEAN NOT NULL DEFAULT 1"),
  ("leads", "assigned_sdr_id", "INTEGER"),
  ("leads", "wrong_number_type", "VARCHAR(60)"),
  ("leads", "wrong_number_notes", "TEXT"),
  ("leads", "sdr_contact_name", "VARCHAR(120)"),
  ("leads", "business_type_custom", "VARCHAR(120)"),
  ("leads", "source_custom", "VARCHAR(120)"),
  ("leads", "phone_number_2", "VARCHAR(40)"),
  ("leads", "phone_number_3", "VARCHAR(40)"),
  ("leads", "phone_primary", "INTEGER NOT NULL DEFAULT 1"),
  ("leads", "assigned_sdr_at", "DATETIME"),
  ("leads", "pm_agent_id", "INTEGER"),
  ("leads", "admin_deleted_at", "DATETIME"),
  ("leads", "admin_deleted_by_id", "INTEGER"),
]


def _existing_columns(table: str) -> set[str]:
  bind = db.engine
  if bind.dialect.name == "sqlite":
    rows = db.session.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return {row[1] for row in rows}
  inspector = inspect(bind)
  if table not in inspector.get_table_names():
    return set()
  return {col["name"] for col in inspector.get_columns(table)}


def apply_schema_patches() -> None:
  """ستون‌های تعریف‌شده در مدل ولی غایب در DB را اضافه می‌کند."""
  for table, column, col_type in SCHEMA_PATCHES:
    if table not in inspect(db.engine).get_table_names():
      continue
    if column in _existing_columns(table):
      continue
    db.session.execute(
      text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
    )
  db.session.commit()
