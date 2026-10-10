from __future__ import annotations
from typing import Optional
from sqlalchemy import Integer, String, Float, Boolean, ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base
class Domain(Base):
    __tablename__='domains'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    weight: Mapped[int] = mapped_column(Integer)
class Objective(Base):
    __tablename__='objectives'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    domain_id: Mapped[int] = mapped_column(ForeignKey('domains.id'), index=True)
    name: Mapped[str] = mapped_column(String)
class Question(Base):
    __tablename__='questions'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    objective_id: Mapped[str] = mapped_column(ForeignKey('objectives.id'), index=True)
    content: Mapped[dict] = mapped_column(JSON)
    fingerprint: Mapped[str] = mapped_column(String, unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
class Exam(Base):
    __tablename__='exams'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    mode: Mapped[str] = mapped_column(String)
    started_at: Mapped[float] = mapped_column(Float)
    deadline: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    submitted_at: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String, index=True, default='active')
    feedback: Mapped[str] = mapped_column(String, default='end')
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    current_index: Mapped[int] = mapped_column(Integer, default=0)
class ExamItem(Base):
    __tablename__='exam_items'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exam_id: Mapped[str] = mapped_column(ForeignKey('exams.id', ondelete='CASCADE'), index=True)
    position: Mapped[int] = mapped_column(Integer)
    question_id: Mapped[str] = mapped_column(String, index=True)
    snapshot: Mapped[dict] = mapped_column(JSON)
    selected: Mapped[list] = mapped_column(JSON, default=list)
    flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    checked: Mapped[bool] = mapped_column(Boolean, default=False)
    correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
class Revision(Base):
    __tablename__='revision'
    question_id: Mapped[str] = mapped_column(String, primary_key=True)
    bookmarked: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str] = mapped_column(Text, default='')
class Setting(Base):
    __tablename__='settings'
    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[object] = mapped_column(JSON)
class ChallengeAttempt(Base):
    __tablename__='challenge_attempts'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    challenge_id: Mapped[str] = mapped_column(String)
    answer: Mapped[str] = mapped_column(Text)
    correct: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[float] = mapped_column(Float)
