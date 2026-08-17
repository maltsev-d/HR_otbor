from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


class Candidate(Base):
    """
    Анкета кандидата. Только личные данные + статус воронки.
    Резюме → Application, интервью → Interview, переписка → HRMessage.
    """
    __tablename__ = 'candidates'

    id               = Column(Integer, primary_key=True)
    tg_id            = Column(BigInteger, unique=True, nullable=False, index=True)
    full_name        = Column(String)
    contact          = Column(String)
    location         = Column(String)
    age              = Column(Integer, nullable=True)
    languages        = Column(String, nullable=True)       # было english_level
    experience       = Column(String, nullable=True)       # новое
    salary_amount    = Column(Integer, nullable=True)      # было salary_expectation
    salary_currency  = Column(String(3), nullable=True)    # новое, из .env
    start_date       = Column(String)
    work_type        = Column(String, nullable=True)       # было contract_type
    consent          = Column(Boolean, default=False)
    status           = Column(String, default="draft")     # draft|new|invited|confirmed|declined|rejected
    nudge_sent       = Column(Boolean, default=False)
    ai_summary       = Column(Text, nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow)

    applications = relationship("Application", back_populates="candidate", cascade="all, delete-orphan")
    interviews   = relationship("Interview",   back_populates="candidate", cascade="all, delete-orphan")
    hr_messages  = relationship("HRMessage",  back_populates="candidate", cascade="all, delete-orphan")


class Vacancy(Base):
    __tablename__ = 'vacancies'

    id          = Column(Integer, primary_key=True)
    title       = Column(String, nullable=False)      # дефолтный title (для обратной совместимости и RAG fallback)
    description = Column(Text)                        # дефолтный description
    is_active   = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)

    applications = relationship("Application", back_populates="vacancy")
    translations = relationship("VacancyTranslation", back_populates="vacancy", cascade="all, delete-orphan")


class VacancyTranslation(Base):
    """
    Переводы вакансий по языкам.
    lang: ru | en | lo | th
    При создании вакансии в админке — создаём запись для всех 4 языков с одним текстом.
    HR редактирует переводы вручную при необходимости.
    RAG индексирует только переводы на BOT_LANG из .env.
    """
    __tablename__ = 'vacancy_translations'

    id          = Column(Integer, primary_key=True)
    vacancy_id  = Column(Integer, ForeignKey('vacancies.id', ondelete='CASCADE'), nullable=False)
    lang        = Column(String(5), nullable=False)   # ru | en | lo | th
    title       = Column(String, nullable=False)
    description = Column(Text)

    __table_args__ = (
        UniqueConstraint('vacancy_id', 'lang', name='uq_vacancy_lang'),
    )

    vacancy = relationship("Vacancy", back_populates="translations")


#class QuestionTranslation(Base):
    """
    Тексты вопросов анкеты по языкам.
    key: vacancy | full_name | consent | resume | contact |
         location | age | languages | experience | salary | start_date | work_type
    lang: ru | en | lo | th
    
    __tablename__ = 'question_translations'

    id        = Column(Integer, primary_key=True)
    key       = Column(String(50), nullable=False)
    lang      = Column(String(5), nullable=False)
    text      = Column(Text, nullable=False)
    order     = Column(Integer, nullable=False)   # порядок в анкете
    is_active = Column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint('key', 'lang', name='uq_question_key_lang'),
    )
    """

class Application(Base):
    """
    Связка кандидат ↔ вакансия + резюме.
    Один кандидат может откликаться на несколько вакансий.
    """
    __tablename__ = 'applications'

    id             = Column(Integer, primary_key=True)
    candidate_id   = Column(Integer, ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False)
    vacancy_id     = Column(Integer, ForeignKey('vacancies.id', ondelete='SET NULL'), nullable=True)
    resume_file_id = Column(String, nullable=True)   # Telegram file_id
    resume_url     = Column(String, nullable=True)   # если кандидат прислал ссылку
    created_at     = Column(DateTime, default=datetime.utcnow)

    candidate = relationship("Candidate", back_populates="applications")
    vacancy   = relationship("Vacancy",   back_populates="applications")


class Interview(Base):
    """Одно собеседование на кандидата."""
    __tablename__ = 'interviews'

    id                = Column(Integer, primary_key=True)
    candidate_id      = Column(Integer, ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False)
    scheduled_at      = Column(DateTime, nullable=True)
    confirmed         = Column(Boolean, default=False)
    declined          = Column(Boolean, default=False)
    invite_nudge_sent = Column(Boolean, default=False)
    created_at        = Column(DateTime, default=datetime.utcnow)

    candidate = relationship("Candidate", back_populates="interviews")


class HRMessage(Base):
    """
    История переписки HR ↔ кандидат через бота.
    question заполняется сразу, answer — когда кандидат ответил.
    """
    __tablename__ = 'hr_messages'

    id           = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False)
    hr_tg_id     = Column(BigInteger, nullable=False)
    question     = Column(Text, nullable=False)
    answer       = Column(Text, nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow)

    candidate = relationship("Candidate", back_populates="hr_messages")


class AutoRejectRule(Base):
    """Правила автоотсева."""
    __tablename__ = 'auto_reject_rules'

    id        = Column(Integer, primary_key=True)
    field     = Column(String)      # salary_amount | age | languages | work_type
    condition = Column(String)      # gt | lt | eq | contains
    value     = Column(String)
    is_active = Column(Boolean, default=True)


class HRAdmin(Base):
    """HR-администраторы."""
    __tablename__ = 'hr_admins'

    id    = Column(Integer, primary_key=True)
    tg_id = Column(BigInteger, unique=True, nullable=False)