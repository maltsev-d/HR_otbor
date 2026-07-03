import sys
import os
from flask import session, request, redirect, url_for

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from flask import Blueprint, render_template, redirect, request, url_for, flash
from db.session import SessionLocal
from db.models import Candidate, Interview, Vacancy, Application, HRMessage, AutoRejectRule, HRAdmin
from admin.telegram import send_telegram_message, send_interview_invite, send_resume_to_hr
from bot.rag.index import upsert_vacancy, delete_vacancy
from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import subqueryload, joinedload
import requests
from flask import Response, abort

admin_bp = Blueprint("admin", __name__, template_folder="templates")

ADMIN_LOGIN    = os.getenv("ADMIN_LOGIN", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme")

@admin_bp.before_request
def require_login():
    if request.endpoint == "admin.login_page":
        return  # логин-страницу пускаем без проверки
    if not session.get("logged_in"):
        return redirect(url_for("admin.login_page"))

@admin_bp.route("/login", methods=["GET", "POST"])
def login_page():
    error = None
    if request.method == "POST":
        login = request.form.get("login", "").strip()
        password = request.form.get("password", "").strip()
        if login == ADMIN_LOGIN and password == ADMIN_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("admin.dashboard"))
        error = "Неверный логин или пароль"
    return render_template("login.html", error=error)

@admin_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("admin.login_page"))

STATUS_LABELS = {
    "draft":     "Черновик",
    "new":       "Новый",
    "invited":   "Приглашён",
    "confirmed": "Подтвердил",
    "declined":  "Отказался",
    "rejected":  "Отклонён",
}

FIELD_LABELS = {
    "salary_expectation": "ЗП ожидание",
    "age": "Возраст",
}

CONDITION_LABELS = {
    "gt": "больше чем",
    "lt": "меньше чем",
}

@admin_bp.app_template_filter("status_ru")
def status_ru(status):
    return STATUS_LABELS.get(status, status)


@admin_bp.app_template_filter("field_ru")
def field_ru(field):
    return FIELD_LABELS.get(field, field)


@admin_bp.app_template_filter("cond_ru")
def cond_ru(condition):
    return CONDITION_LABELS.get(condition, condition)


# ── DASHBOARD ──────────────────────────────────────────────
@admin_bp.route("/")
@admin_bp.route("/dashboard")
def dashboard():
    with SessionLocal() as session:
        total            = session.query(func.count(Candidate.id)).scalar() or 0
        new_count        = session.query(func.count(Candidate.id)).filter(Candidate.status == "new").scalar() or 0
        invited          = session.query(func.count(Candidate.id)).filter(Candidate.status == "invited").scalar() or 0
        confirmed        = session.query(func.count(Candidate.id)).filter(Candidate.status == "confirmed").scalar() or 0
        week_ago         = datetime.utcnow() - timedelta(days=7)
        week_new         = session.query(func.count(Candidate.id)).filter(Candidate.created_at >= week_ago).scalar() or 0
        vacancies_active = session.query(func.count(Vacancy.id)).filter(Vacancy.is_active == True).scalar() or 0

        vac_stats = (
            session.query(Vacancy.title, func.count(Application.id).label("cnt"))
            .outerjoin(Application, Application.vacancy_id == Vacancy.id)
            .group_by(Vacancy.id, Vacancy.title)
            .order_by(func.count(Application.id).desc())
            .all()
        )

        # Грузим recent с нужными связями ДО expunge
        recent_raw = (
            session.query(Candidate)
            .options(
                subqueryload(Candidate.applications).joinedload(Application.vacancy),
            )
            .order_by(Candidate.id.desc())
            .limit(5)
            .all()
        )

        # Сериализуем нужное до закрытия сессии
        recent = []
        for c in recent_raw:
            app = c.applications[0] if c.applications else None
            recent.append({
                "id":         c.id,
                "full_name":  c.full_name,
                "status":     c.status,
                "salary":     c.salary_expectation,
                "vacancy":    app.vacancy.title if app and app.vacancy else None,
                "ai_summary": c.ai_summary,
            })

    stats = {
        "total": total, "new": new_count, "invited": invited,
        "confirmed": confirmed, "week_new": week_new,
        "vacancies_active": vacancies_active,
    }
    return render_template("dashboard.html", stats=stats, vac_stats=vac_stats, recent=recent)


# ── CANDIDATES LIST ────────────────────────────────────────
@admin_bp.route("/candidates")
def index():
    status_filter = request.args.get("status")
    with SessionLocal() as session:
        q = (
            session.query(Candidate)
            .options(
                subqueryload(Candidate.applications).joinedload(Application.vacancy),
                subqueryload(Candidate.interviews),
            )
        )
        if status_filter:
            q = q.filter(Candidate.status == status_filter)
        candidates_raw = q.order_by(Candidate.id.desc()).all()

        candidates = []
        for c in candidates_raw:
            app = c.applications[0] if c.applications else None
            itv = c.interviews[0] if c.interviews else None
            candidates.append({
                "id":                 c.id,
                "full_name":          c.full_name,
                "status":             c.status,
                "contact":            c.contact,
                "location":           c.location,
                "age":                c.age,
                "salary_expectation": c.salary_expectation,
                "ai_summary":         c.ai_summary,
                "vacancy_title":      app.vacancy.title if app and app.vacancy else None,
                "resume_url":         app.resume_url if app else None,
                "resume_file_id":     app.resume_file_id if app else None,
                "interview_at":       itv.scheduled_at if itv else None,
            })

    return render_template("candidates.html", candidates=candidates)


# ── CANDIDATE DETAIL ───────────────────────────────────────
@admin_bp.route("/candidates/<int:candidate_id>")
def candidate_detail(candidate_id):
    with SessionLocal() as session:
        c = (
            session.query(Candidate)
            .options(
                subqueryload(Candidate.applications).joinedload(Application.vacancy),
                subqueryload(Candidate.interviews),
                subqueryload(Candidate.hr_messages),
            )
            .filter(Candidate.id == candidate_id)
            .first()
        )
        if not c:
            return "Кандидат не найден", 404

        app = c.applications[0] if c.applications else None
        itv = c.interviews[0] if c.interviews else None

        data = {
            "id":                 c.id,
            "full_name":          c.full_name,
            "status":             c.status,
            "contact":            c.contact,
            "location":           c.location,
            "age":                c.age,
            "english_level":      c.english_level,
            "salary_expectation": c.salary_expectation,
            "start_date":         c.start_date,
            "contract_type":      c.contract_type,
            "consent":            c.consent,
            "ai_summary":         c.ai_summary,
            "created_at":         c.created_at,
            "tg_id":              c.tg_id,
            "vacancy_title":      app.vacancy.title if app and app.vacancy else None,
            "app_created_at":     app.created_at if app else None,
            "resume_url":         app.resume_url if app else None,
            "resume_file_id":     app.resume_file_id if app else None,
            "interview_at":       itv.scheduled_at if itv else None,
            "interview_confirmed":itv.confirmed if itv else False,
            "interview_declined": itv.declined if itv else False,
            "hr_messages": [
                {
                    "question":   m.question,
                    "answer":     m.answer,
                    "created_at": m.created_at,
                }
                for m in c.hr_messages
            ],
        }

    return render_template("candidate_detail.html", c=data)


# ── DOWNLOAD RESUME ─────────────────────────────────────────
@admin_bp.route("/resume/<int:candidate_id>")
def download_resume(candidate_id):
    with SessionLocal() as session:
        c = (
            session.query(Candidate)
            .options(subqueryload(Candidate.applications))
            .filter(Candidate.id == candidate_id)
            .first()
        )
        if not c:
            abort(404)
        app_ = c.applications[0] if c.applications else None
        if not app_:
            abort(404)

        if app_.resume_url:
            return redirect(app_.resume_url)

        if not app_.resume_file_id:
            abort(404)

        bot_token = os.getenv("BOT_TOKEN")
        r = requests.get(
            f"https://api.telegram.org/bot{bot_token}/getFile",
            params={"file_id": app_.resume_file_id},
            timeout=10,
        )
        r.raise_for_status()
        file_path = r.json()["result"]["file_path"]

        file_resp = requests.get(
            f"https://api.telegram.org/file/bot{bot_token}/{file_path}",
            timeout=15,
        )
        file_resp.raise_for_status()

        filename = file_path.split("/")[-1]
        return Response(
            file_resp.content,
            mimetype="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )


# ── REQUEST RESUME → HR Telegram ──────────────────────────
@admin_bp.route("/candidates/<int:candidate_id>/request-resume", methods=["POST"])
def request_resume(candidate_id):
    with SessionLocal() as session:
        c = (
            session.query(Candidate)
            .options(subqueryload(Candidate.applications))
            .filter(Candidate.id == candidate_id)
            .first()
        )
        if not c:
            return "Кандидат не найден", 404
        app = c.applications[0] if c.applications else None
        file_id = app.resume_file_id if app else None
        name    = c.full_name

    if file_id:
        admin_ids_raw = os.getenv("ADMIN_IDS", "")
        try:
            hr_id = int(admin_ids_raw.split(",")[0].strip())
        except (ValueError, IndexError):
            hr_id = 0
        if hr_id:
            send_resume_to_hr(hr_id, file_id, name)
            flash("Резюме отправлено вам в Telegram", "success")
    else:
        flash("У кандидата нет файла резюме", "error")

    return redirect(f"/candidates/{candidate_id}")


# ── SCHEDULE INTERVIEW ─────────────────────────────────────
@admin_bp.route("/schedule/<int:candidate_id>", methods=["POST"])
def schedule(candidate_id):
    time_str = request.form.get("interview_time", "").strip()
    try:
        interview_dt = datetime.strptime(time_str, "%Y-%m-%dT%H:%M")
    except ValueError:
        flash("Неверный формат даты", "error")
        return redirect(f"/candidates/{candidate_id}")

    with SessionLocal() as session:
        candidate = session.get(Candidate, candidate_id)
        if not candidate:
            return "Кандидат не найден", 404
        tg_id = candidate.tg_id
        candidate.status = "invited"
        interview = session.query(Interview).filter_by(candidate_id=candidate_id).first()
        if interview:
            interview.scheduled_at      = interview_dt
            interview.confirmed         = False
            interview.declined          = False
            interview.invite_nudge_sent = False
        else:
            session.add(Interview(candidate_id=candidate_id, scheduled_at=interview_dt))
        session.commit()

    if tg_id:
        send_interview_invite(tg_id, interview_dt)

    flash("Интервью назначено", "success")
    return redirect(f"/candidates/{candidate_id}")


# ── REJECT ─────────────────────────────────────────────────
@admin_bp.route("/reject/<int:candidate_id>", methods=["POST"])
def reject(candidate_id):
    with SessionLocal() as session:
        candidate = session.get(Candidate, candidate_id)
        if not candidate:
            return "Кандидат не найден", 404
        tg_id = candidate.tg_id
        candidate.status = "rejected"
        session.commit()

    if tg_id:
        send_telegram_message(tg_id, "😔 Спасибо за отклик, но по данной позиции мы не можем продолжить с вами процесс.")

    flash("Кандидат отклонён", "error")
    return redirect(f"/candidates/{candidate_id}")


# ── CLARIFY ────────────────────────────────────────────────
@admin_bp.route("/clarify/<int:candidate_id>", methods=["POST"])
def clarify(candidate_id):
    hr_message_text = request.form.get("hr_message", "").strip()
    if not hr_message_text:
        flash("Сообщение не может быть пустым", "error")
        return redirect(f"/candidates/{candidate_id}")

    try:
        first_admin_id = int(os.getenv("ADMIN_IDS", "0").split(",")[0].strip())
    except (ValueError, IndexError):
        first_admin_id = 0

    with SessionLocal() as session:
        candidate = session.get(Candidate, candidate_id)
        if not candidate:
            return "Кандидат не найден", 404
        tg_id = candidate.tg_id
        session.add(HRMessage(
            candidate_id=candidate_id,
            hr_tg_id=first_admin_id,
            question=hr_message_text,
        ))
        session.commit()

    if tg_id:
        send_telegram_message(tg_id, f"📩 Сообщение от HR-менеджера:\n\n{hr_message_text}\n\nВы можете ответить прямо в этот чат.")

    flash("Сообщение отправлено кандидату", "info")
    return redirect(f"/candidates/{candidate_id}")


# ── VACANCIES ──────────────────────────────────────────────
@admin_bp.route("/vacancies")
def vacancies():
    with SessionLocal() as session:
        vacs_raw = (
            session.query(Vacancy)
            .options(subqueryload(Vacancy.applications))
            .order_by(Vacancy.id)
            .all()
        )
        vacs = [
            {
                "id":          v.id,
                "title":       v.title,
                "description": v.description,
                "is_active":   v.is_active,
                "is_featured": v.is_featured,
                "app_count":   len(v.applications),
            }
            for v in vacs_raw
        ]
    return render_template("vacancies.html", vacancies=vacs)


@admin_bp.route("/vacancy/add", methods=["POST"])
def vacancy_add():
    title       = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    if not title:
        flash("Название не может быть пустым", "error")
        return redirect("/vacancies")
    with SessionLocal() as session:
        vac = Vacancy(title=title, description=description, is_active=True)
        session.add(vac)
        session.commit()
        upsert_vacancy(vac)
    flash("Вакансия создана", "success")
    return redirect("/vacancies")


@admin_bp.route("/vacancy/toggle/<int:vacancy_id>", methods=["POST"])
def vacancy_toggle(vacancy_id):
    with SessionLocal() as session:
        vac = session.get(Vacancy, vacancy_id)
        if vac:
            vac.is_active = not vac.is_active
            session.commit()
            if vac.is_active:
                upsert_vacancy(vac)
            else:
                delete_vacancy(vac.id)
    flash("Статус вакансии обновлён", "success")
    return redirect("/vacancies")


@admin_bp.route("/vacancy/toggle-featured/<int:vacancy_id>", methods=["POST"])
def vacancy_toggle_featured(vacancy_id):
    with SessionLocal() as session:
        vac = session.get(Vacancy, vacancy_id)
        if vac:
            vac.is_featured = not vac.is_featured
            session.commit()
    flash("Featured-статус обновлён", "success")
    return redirect("/vacancies")


@admin_bp.route("/vacancy/delete/<int:vacancy_id>", methods=["POST"])
def vacancy_delete(vacancy_id):
    with SessionLocal() as session:
        vac = session.get(Vacancy, vacancy_id)
        if vac:
            vacancy_id_to_delete = vac.id
            session.delete(vac)
            session.commit()
            delete_vacancy(vacancy_id_to_delete)
    flash("Вакансия удалена", "error")
    return redirect("/vacancies")


# ── AUTORULES ──────────────────────────────────────────────
@admin_bp.route("/autorules")
def autorules():
    with SessionLocal() as session:
        rules = session.query(AutoRejectRule).order_by(AutoRejectRule.id).all()
        rules_data = [
            {
                "id":        r.id,
                "field":     r.field,
                "condition": r.condition,
                "value":     r.value,
                "is_active": r.is_active,
            }
            for r in rules
        ]
    return render_template("autorules.html", rules=rules_data)


@admin_bp.route("/autorules/add", methods=["POST"])
def autorules_add():
    field     = request.form.get("field", "").strip()
    condition = request.form.get("condition", "").strip()
    value     = request.form.get("value", "").strip()
    if not field or not condition or not value:
        flash("Все поля обязательны", "error")
        return redirect("/autorules")
    with SessionLocal() as session:
        session.add(AutoRejectRule(field=field, condition=condition, value=value, is_active=True))
        session.commit()
    flash("Правило создано", "success")
    return redirect("/autorules")


@admin_bp.route("/autorules/toggle/<int:rule_id>", methods=["POST"])
def autorules_toggle(rule_id):
    with SessionLocal() as session:
        rule = session.get(AutoRejectRule, rule_id)
        if rule:
            rule.is_active = not rule.is_active
            session.commit()
    flash("Статус правила обновлён", "success")
    return redirect("/autorules")


@admin_bp.route("/autorules/delete/<int:rule_id>", methods=["POST"])
def autorules_delete(rule_id):
    with SessionLocal() as session:
        rule = session.get(AutoRejectRule, rule_id)
        if rule:
            session.delete(rule)
            session.commit()
    flash("Правило удалено", "error")
    return redirect("/autorules")


# ── HR ADMINS ──────────────────────────────────────────────
@admin_bp.route("/hr-admins")
def hr_admins():
    with SessionLocal() as session:
        admins = session.query(HRAdmin).order_by(HRAdmin.id).all()
        admins_data = [{"id": a.id, "tg_id": a.tg_id} for a in admins]
    return render_template("hr_admins.html", admins=admins_data)


@admin_bp.route("/hr-admins/add", methods=["POST"])
def hr_admins_add():
    tg_id_str = request.form.get("tg_id", "").strip()
    try:
        tg_id = int(tg_id_str)
    except ValueError:
        flash("Некорректный Telegram ID", "error")
        return redirect("/hr-admins")
    with SessionLocal() as session:
        session.add(HRAdmin(tg_id=tg_id))
        session.commit()
    flash("Админ добавлен", "success")
    return redirect("/hr-admins")


@admin_bp.route("/hr-admins/delete/<int:admin_id>", methods=["POST"])
def hr_admins_delete(admin_id):
    with SessionLocal() as session:
        admin = session.get(HRAdmin, admin_id)
        if admin:
            session.delete(admin)
            session.commit()
    flash("Админ удалён", "error")
    return redirect("/hr-admins")