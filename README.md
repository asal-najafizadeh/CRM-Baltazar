<div align="center">

# Baltazar CRM

**A sequential sales pipeline CRM with role-based dashboards — LH → SDR → Setter → PM → Closer, plus Admin.**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0.3-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)
[![Version](https://img.shields.io/badge/Version-1.0.0-blue.svg?style=for-the-badge)](https://github.com/WhileTrue0087/CRM-Baltazar)
[![Build](https://img.shields.io/badge/Build-Passing-brightgreen.svg?style=for-the-badge)](https://github.com/WhileTrue0087/CRM-Baltazar)


</div>

---

## 📖 About The Project

Baltazar CRM solves the problem of **unstructured, multi-stage sales pipelines** by providing a single, sequential workflow where every lead moves through clearly defined stages — **Lead Hunter (LH) → SDR → Setter → PM → Closer** — with a dedicated, role-based dashboard for each team.

Instead of juggling spreadsheets, phone notes, and scattered follow-ups, each role sees exactly the leads they own, in the right queue, with the right actions. Admins get a real-time overview of the entire funnel, daily metrics, and one-click Excel import/export.

**Core value proposition:** A lightweight, self-hosted CRM that enforces pipeline discipline, tracks every touchpoint, and gives management full visibility — without the bloat of enterprise CRMs.

---

## ✨ Key Features

- **Sequential 5-stage pipeline** — LH → SDR → Setter → PM → Closer with enforced stage transitions.
- **Role-based dashboards** — Each role (LH, SDR, Setter, PM, Closer, Admin) gets a tailored view and queue.
- **Lead intake with duplicate detection** — LH form supports up to 3 phone numbers, primary-phone marking, and automatic duplicate-phone rejection.
- **SDR call workflow** — Handle answered / unanswered / wrong-number calls; route to Setter, PM, follow-up, or disqualify.
- **Wrong-number correction loop** — Wrong numbers are returned to LH for correction and re-queued to the SDR pool.
- **Setter meeting management** — Approve, reject, or mark uncertain; approved meetings auto-advance to Closer and award **+1 score** to the responsible LH & SDR.
- **PM proposal submission** — Jalali (Persian) date input, amount validation, and proposal tracking.
- **Closer deal closing** — Mark deals as **won / lost / follow-up** with full closing notes.
- **Admin analytics dashboard** — Hybrid daily + total metrics: LH registrations, SDR success calls, Setter referrals, wrong numbers, held meetings, follow-ups, and rejections.
- **Automated lead distribution** — Equally distribute today's and backlog unassigned leads among active SDRs.
- **Excel bulk import** — Admin can import leads from `.xlsx` files (pandas + openpyxl).
- **Excel export** — Master, SDR, Setter, and Closer department reports, plus per-SDR daily exports.
- **User management** — Create, edit, suspend, and delete users with role assignment.
- **Lead search** — Filter by company name, business type, and source.
- **Rating board / leaderboard** — Track team performance with a scoring system.
- **Jalali (Persian) calendar** — Full Persian date support via `jdatetime`.
- **Security** — Bcrypt password hashing, Flask-Login sessions, and CSRF protection.
- **Soft-delete / archive** — Leads are archived (not hard-deleted) with full audit trail.

---

## 🛠️ Built With

| Category       | Technology                                                                                                                              |
|----------------|-----------------------------------------------------------------------------------------------------------------------------------------|
| **Language**   | [![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)                       |
| **Framework**  | [![Flask](https://img.shields.io/badge/Flask-3.0.3-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)               |
| **ORM**        | [![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.x-D71F00?logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)         |
| **Database**   | [![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/) · [![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/) |
| **Forms**      | [![WTForms](https://img.shields.io/badge/WTForms-3.1.2-00B4AB?logo=python&logoColor=white)](https://wtforms.readthedocs.io/)            |
| **Auth**       | [![Flask-Login](https://img.shields.io/badge/Flask--Login-0.6.3-000000?logo=flask&logoColor=white)](https://flask-login.readthedocs.io/) · [![Flask-Bcrypt](https://img.shields.io/badge/Flask--Bcrypt-1.0.1-000000?logo=flask&logoColor=white)](https://flask-bcrypt.readthedocs.io/) |
| **Dates**      | [![jdatetime](https://img.shields.io/badge/jdatetime-5.0.0-4B8BBE?logo=python&logoColor=white)](https://pypi.org/project/jdatetime/)    |
| **Excel**      | [![pandas](https://img.shields.io/badge/pandas-2.0+-150458?logo=pandas&logoColor=white)](https://pandas.pydata.org/) · [![openpyxl](https://img.shields.io/badge/openpyxl-3.1+-217346?logo=python&logoColor=white)](https://openpyxl.readthedocs.io/) |
| **Server**     | [![Gunicorn](https://img.shields.io/badge/Gunicorn-499848?logo=gunicorn&logoColor=white)](https://gunicorn.org/)                         |

---

## 🚀 Getting Started

### Prerequisites

- **Python** 3.10 or higher
- **pip** (Python package manager)
- **Git** (for cloning)
- *(Optional)* **Docker** for containerized deployment
- *(Optional)* **PostgreSQL** — the app defaults to SQLite, but supports any SQLAlchemy-compatible DB via `DATABASE_URL`

### Installation

Clone the repository and set up a virtual environment:

```bash
# Clone the repository
git clone https://github.com/WhileTrue0087/CRM-Baltazar.git
cd CRM-Baltazar
```

#### Windows (PowerShell)

```powershell
# Create virtual environment
python -m venv venv

# Activate (PowerShell)
.\venv\Scripts\Activate.ps1

# If execution policy blocks activation:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Seed database (users + sample leads)
python seed.py

# After model/schema changes, reset DB:
python seed.py --reset

# Run development server
python run.py
```

#### macOS / Linux

```bash
# Create virtual environment
python3 -m venv venv

# Activate
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Seed database (users + sample leads)
python seed.py

# After model/schema changes, reset DB:
python seed.py --reset

# Run development server
python run.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

### Environment Setup

Create a `.env` file in the project root (or set environment variables directly):

```env
# Flask
SECRET_KEY=your-production-secret-key
FLASK_DEBUG=0

# Database (optional — defaults to SQLite at instance/crm.db)
# DATABASE_URL=postgresql://user:password@localhost:5432/crm_db
```

> **Note:** `SECRET_KEY` is required in production. Never commit real secrets to version control.

---

## 🔑 Demo Logins

After running `python seed.py`, the following users are created:

| Username     | Password     | Role   |
|--------------|--------------|--------|
| `admin`      | `admin123`   | Admin  |
| `lh_user`    | `lh12345`    | LH     |
| `sdr_user`   | `sdr12345`   | SDR    |
| `setter_user`| `setter12345`| Setter |
| `pm_user`    | `pm12345`    | PM     |
| `closer_user`| `closer12345`| Closer |

> ⚠️ **Security warning:** These credentials are for **development/demo only**. Change all passwords in production.

---

## 🧪 Usage Examples

### Run the development server

```bash
python run.py
```

### Seed / reset the database

```bash
# Seed with demo users and sample leads
python seed.py

# Drop all tables and re-create (after schema changes)
python seed.py --reset
```

### Run with Gunicorn (production)

```bash
gunicorn run:app --bind 0.0.0.0:8000 --workers 3
```

### Pipeline flow

| Stage | Role   | Action                                                       |
|-------|--------|--------------------------------------------------------------|
| 1     | LH     | Intake form → lead enters SDR pool                           |
| 2     | SDR    | Call form → route to Setter / PM / follow-up / disqualify    |
| 3     | Setter | Meeting form → approve (→ Closer) / reject / uncertain       |
| 4     | PM     | Proposal form → mark proposal sent                           |
| 5     | Closer | Outcome form → close as **won** / **lost** / follow-up       |

---

## 🤝 Contributing

Contributions are welcome! To contribute:

1. **Fork** the repository.
2. Create a **feature branch** (`git checkout -b feature/amazing-feature`).
3. **Commit** your changes (`git commit -m 'Add amazing feature'`).
4. **Push** to the branch (`git push origin feature/amazing-feature`).
5. Open a **Pull Request**.

Please ensure your code follows the existing style, includes tests where applicable, and passes all checks before submitting.

---

## 📄 License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for more information.

---

## 📬 Contact

**Project:** [CRM-Baltazar](https://github.com/WhileTrue0087/CRM-Baltazar)  
**Live Demo:** [https://crm-baltazar.onrender.com/](https://crm-baltazar.onrender.com/)

---

<div align="center">
  Made with ❤️ and Flask
</div>