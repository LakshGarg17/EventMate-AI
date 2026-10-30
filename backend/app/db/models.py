import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

try:
    from app.db.database import Base
except ImportError:
    from backend.app.db.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    event_type: Mapped[str] = mapped_column(
        String(50),
        CheckConstraint("event_type IN ('Wedding', 'Birthday', 'Community Event')", name="chk_event_type"),
        nullable=False,
    )
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    guest_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_budget: Mapped[int] = mapped_column(Integer, nullable=False)  # stored in integer minor units
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    preferred_theme: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    additional_preferences: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    generated_plan: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=get_utc_now,
        onupdate=get_utc_now,
        nullable=False,
    )

    budget_categories: Mapped[List["BudgetCategory"]] = relationship(
        "BudgetCategory",
        back_populates="event",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    expenses: Mapped[List["Expense"]] = relationship(
        "Expense",
        back_populates="event",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    tasks: Mapped[List["Task"]] = relationship(
        "Task",
        back_populates="event",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class BudgetCategory(Base):
    __tablename__ = "budget_categories"
    __table_args__ = (
        UniqueConstraint("event_id", "category_name", name="uq_event_category_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    event_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_name: Mapped[str] = mapped_column(String(100), nullable=False)
    estimated_amount: Mapped[int] = mapped_column(Integer, nullable=False)  # minor units
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    event: Mapped["Event"] = relationship("Event", back_populates="budget_categories")
    expenses: Mapped[List["Expense"]] = relationship("Expense", back_populates="budget_category")


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    event_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    budget_category_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("budget_categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    estimated_amount: Mapped[int] = mapped_column(Integer, nullable=False)  # minor units
    actual_amount: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # minor units
    payment_status: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint("payment_status IN ('Pending', 'Partial', 'Paid')", name="chk_expense_payment_status"),
        nullable=False,
        default="Pending",
    )
    expense_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    event: Mapped["Event"] = relationship("Event", back_populates="expenses")
    budget_category: Mapped[Optional["BudgetCategory"]] = relationship("BudgetCategory", back_populates="expenses")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    event_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    priority: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint("priority IN ('High', 'Medium', 'Low')", name="chk_task_priority"),
        nullable=False,
        default="Medium",
    )
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint("status IN ('Pending', 'In Progress', 'Completed')", name="chk_task_status"),
        nullable=False,
        default="Pending",
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=get_utc_now,
        onupdate=get_utc_now,
        nullable=False,
    )

    event: Mapped["Event"] = relationship("Event", back_populates="tasks")
