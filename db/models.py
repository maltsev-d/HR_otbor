from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


class Candidate(Base):
    """
    Анкета кандидата. Только личные данные + статус воронки.
    Резюме → Application, интервью → Interview, переписка → HRMessage.
    """
    __tablename__ = 'candidates'

    id                  = Column(Integer, primary_key=True)
    tg_id               = Column(BigInteger, unique=True, nullable=False, index=True)
    full_name           = Column(String)
    contact             = Column(String)
    location            = Column(String)
    age                 = Column(Integer, nullable=True)
    english_level       = Column(String)
    salary_expectation  = Column(Integer)
    start_date          = Column(String)
    contract_type       = Column(String)
    consent             = Column(Boolean, default=False)
    status              = Column(String, default="draft")   # draft|new|invited|confirmed|declined|rejected
    nudge_sent          = Column(Boolean, default=False)    # напоминание о брошенной анкете
    ai_summary          = Column(Text, nullable=True)
    created_at          = Column(DateTime, default=datetime.utcnow)

    applications        = relationship("Application", back_populates="candidate", cascade="all, delete-orphan")
    interviews          = relationship("Interview",   back_populates="candidate", cascade="all, delete-orphan")
    hr_messages         = relationship("HRMessage",  back_populates="candidate", cascade="all, delete-orphan")


class Vacancy(Base):
    __tablename__ = 'vacancies'

    id          = Column(Integer, primary_key=True)
    title       = Column(String, nullable=False)
    description = Column(Text)
    is_active   = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)

    applications = relationship("Application", back_populates="vacancy")


class Application(Base):
    """
    Связка кандидат ↔ вакансия + резюме.
    Один кандидат может откликаться на несколько вакансий.
    """
    __tablename__ = 'applications'

    id              = Column(Integer, primary_key=True)
    candidate_id    = Column(Integer, ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False)
    vacancy_id      = Column(Integer, ForeignKey('vacancies.id', ondelete='SET NULL'), nullable=True)
    resume_file_id  = Column(String, nullable=True)   # Telegram file_id
    resume_url      = Column(String, nullable=True)   # если кандидат прислал ссылку
    created_at      = Column(DateTime, default=datetime.utcnow)

    candidate   = relationship("Candidate", back_populates="applications")
    vacancy     = relationship("Vacancy",   back_populates="applications")


class Interview(Base):
    """
    Одно собеседование на кандидата (пока 1:1, в будущем можно 1:N).
    """
    __tablename__ = 'interviews'

    id                  = Column(Integer, primary_key=True)
    candidate_id        = Column(Integer, ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False)
    scheduled_at        = Column(DateTime, nullable=True)
    confirmed           = Column(Boolean, default=False)
    declined            = Column(Boolean, default=False)
    invite_nudge_sent   = Column(Boolean, default=False)
    created_at          = Column(DateTime, default=datetime.utcnow)

    candidate = relationship("Candidate", back_populates="interviews")


class HRMessage(Base):
    """
    История переписки HR ↔ кандидат через бота.
    question заполняется сразу, answer — когда кандидат ответил (nullable).
    """
    __tablename__ = 'hr_messages'

    id              = Column(Integer, primary_key=True)
    candidate_id    = Column(Integer, ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False)
    hr_tg_id        = Column(BigInteger, nullable=False)
    question        = Column(Text, nullable=False)
    answer          = Column(Text, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)

    candidate = relationship("Candidate", back_populates="hr_messages")


class AutoRejectRule(Base):
    """Правила автоотсева — будущий функционал."""
    __tablename__ = 'auto_reject_rules'

    id          = Column(Integer, primary_key=True)
    field       = Column(String)
    condition   = Column(String)   # gt|lt|eq|contains
    value       = Column(String)
    is_active   = Column(Boolean, default=True)


class HRAdmin(Base):
    """Авторизация HR в админке — будущий функционал."""
    __tablename__ = 'hr_admins'

    id      = Column(Integer, primary_key=True)
    tg_id   = Column(BigInteger, unique=True, nullable=False)