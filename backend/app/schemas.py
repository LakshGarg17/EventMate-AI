from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional, Union
from uuid import uuid4
from pydantic import BaseModel, Field, field_validator


SUPPORTED_CURRENCIES = ["INR", "USD", "EUR", "GBP", "CAD", "AUD", "AED", "SGD", "JPY"]
EVENT_TYPES = ["Wedding", "Birthday", "Community Event"]


class EventRequest(BaseModel):
    event_name: str = Field(..., min_length=1, max_length=100, description="Name of the event")
    event_type: Literal["Wedding", "Birthday", "Community Event"] = Field(..., description="Type of event")
    event_date: date = Field(..., description="Date of the event (must be today or later)")
    location: str = Field(..., min_length=1, max_length=200, description="City or venue location")
    guest_count: int = Field(..., ge=1, le=100000, description="Estimated number of attendees")
    total_budget: int = Field(..., gt=0, description="Total budget in currency minor or major units")
    currency: str = Field(default="INR", description="3-letter currency code")
    theme: Optional[str] = Field(default=None, max_length=100, description="Optional theme or style preference")
    additional_preferences: Optional[str] = Field(default=None, max_length=500, description="Additional notes or constraints")

    @field_validator("event_name", "location", mode="before")
    @classmethod
    def strip_and_validate_nonempty(cls, v: str) -> str:
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Must not be empty or whitespace only")
        return v

    @field_validator("theme", "additional_preferences", mode="before")
    @classmethod
    def strip_optional(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            v = v.strip()
            return v if v else None
        return v

    @field_validator("event_date")
    @classmethod
    def validate_event_date(cls, v: date) -> date:
        today = date.today()
        if v < today:
            raise ValueError(f"Event date must be today ({today.isoformat()}) or later")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        v_upper = v.strip().upper()
        if v_upper not in SUPPORTED_CURRENCIES:
            raise ValueError(f"Currency '{v}' is not supported. Supported: {', '.join(SUPPORTED_CURRENCIES)}")
        return v_upper


# Response Schemas
class ThemeInfo(BaseModel):
    name: str
    description: str
    color_palette: List[str]


class BudgetItem(BaseModel):
    category: str
    amount: int
    percentage: float
    notes: str


class BudgetBreakdown(BaseModel):
    items: List[BudgetItem]
    total_allocated: int
    currency: str
    contingency: int
    is_estimate: bool = True


class TimelineItem(BaseModel):
    task: str
    description: str
    priority: Literal["High", "Medium", "Low"]
    category: str
    due_date: date
    days_before: int
    is_overdue: bool = False
    is_unrealistic: bool = False
    warning: Optional[str] = None


class RiskItem(BaseModel):
    risk: str
    likelihood: Literal["High", "Medium", "Low"]
    mitigation: str


class EventPlanResponse(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    source: Literal["gemini", "demo"]
    model: Optional[str] = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    event_details: EventRequest
    overview: str
    recommended_theme: ThemeInfo
    budget: BudgetBreakdown
    checklist: List[str]
    timeline: List[TimelineItem]
    decoration_suggestions: List[str]
    catering_suggestions: List[str]
    entertainment_suggestions: List[str]
    vendor_requirements: List[str]
    risks: List[RiskItem]
    warnings: List[str] = []


# AI Generation Raw Schemas
class RawAIBudgetItem(BaseModel):
    category: str
    estimated_amount: int
    notes: str


class RawAITimelineItem(BaseModel):
    task: str
    description: str
    priority: Literal["High", "Medium", "Low"]
    category: str
    days_before: int


class RawAIRisk(BaseModel):
    risk: str
    likelihood: Literal["High", "Medium", "Low"]
    mitigation: str


class RawAIPlan(BaseModel):
    overview: str
    recommended_theme: ThemeInfo
    budget_items: List[RawAIBudgetItem]
    checklist: List[str]
    timeline: List[RawAITimelineItem]
    decoration_suggestions: List[str]
    catering_suggestions: List[str]
    entertainment_suggestions: List[str]
    vendor_requirements: List[str]
    risks: List[RawAIRisk]
    warnings: List[str] = []


# ==========================================
# Day 2 Persistence & Management Schemas
# ==========================================

class EventCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Event name")
    event_type: Literal["Wedding", "Birthday", "Community Event"]
    event_date: date
    location: str = Field(..., min_length=1, max_length=200)
    guest_count: int = Field(..., ge=1, le=100000)
    total_budget: Union[int, float, str]
    currency: str = Field(default="INR")
    preferred_theme: Optional[str] = Field(default=None, max_length=100)
    additional_preferences: Optional[str] = Field(default=None, max_length=500)
    generated_plan: Optional[Dict[str, Any]] = None

    @field_validator("name", "location", mode="before")
    @classmethod
    def strip_and_validate_nonempty(cls, v: str) -> str:
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Must not be empty or whitespace only")
        return v

    @field_validator("preferred_theme", "additional_preferences", mode="before")
    @classmethod
    def strip_optional(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            v = v.strip()
            return v if v else None
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        v_upper = v.strip().upper()
        if v_upper not in SUPPORTED_CURRENCIES:
            raise ValueError(f"Currency '{v}' is not supported. Supported: {', '.join(SUPPORTED_CURRENCIES)}")
        return v_upper


class EventUpdate(BaseModel):
    model_config = {"extra": "forbid"}

    name: Optional[str] = Field(default=None, max_length=100)
    event_type: Optional[Literal["Wedding", "Birthday", "Community Event"]] = None
    event_date: Optional[date] = None
    location: Optional[str] = Field(default=None, max_length=200)
    guest_count: Optional[int] = Field(default=None, ge=1, le=100000)
    total_budget: Optional[Union[int, float, str]] = None
    currency: Optional[str] = None
    preferred_theme: Optional[str] = Field(default=None, max_length=100)
    additional_preferences: Optional[str] = Field(default=None, max_length=500)

    @field_validator("name", "location", mode="before")
    @classmethod
    def strip_and_validate_nonempty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Must not be empty or whitespace only")
        return v

    @field_validator("preferred_theme", "additional_preferences", mode="before")
    @classmethod
    def strip_optional(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            v = v.strip()
            return v if v else None
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_upper = v.strip().upper()
            if v_upper not in SUPPORTED_CURRENCIES:
                raise ValueError(f"Currency '{v}' is not supported. Supported: {', '.join(SUPPORTED_CURRENCIES)}")
            return v_upper
        return v


class BudgetCategoryResponse(BaseModel):
    id: str
    event_id: str
    category_name: str
    estimated_amount: str
    description: Optional[str] = None


class ExpenseCreate(BaseModel):
    description: str = Field(..., min_length=1, max_length=255)
    estimated_amount: Union[int, float, str]
    actual_amount: Optional[Union[int, float, str]] = None
    budget_category_id: Optional[str] = None
    payment_status: Literal["Pending", "Partial", "Paid"] = "Pending"
    expense_date: Optional[date] = None
    notes: Optional[str] = None

    @field_validator("description", mode="before")
    @classmethod
    def strip_description(cls, v: str) -> str:
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Description must not be empty or whitespace only")
        return v


class ExpenseUpdate(BaseModel):
    model_config = {"extra": "forbid"}

    description: Optional[str] = Field(default=None, max_length=255)
    estimated_amount: Optional[Union[int, float, str]] = None
    actual_amount: Optional[Union[int, float, str]] = None
    budget_category_id: Optional[str] = None
    payment_status: Optional[Literal["Pending", "Partial", "Paid"]] = None
    expense_date: Optional[date] = None
    notes: Optional[str] = None

    @field_validator("description", mode="before")
    @classmethod
    def strip_description(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Description must not be empty or whitespace only")
        return v


class ExpenseResponse(BaseModel):
    id: str
    event_id: str
    budget_category_id: Optional[str] = None
    description: str
    estimated_amount: str
    actual_amount: Optional[str] = None
    payment_status: str
    expense_date: Optional[date] = None
    notes: Optional[str] = None
    created_at: datetime


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    category: str = Field(..., min_length=1, max_length=50)
    priority: Literal["High", "Medium", "Low"] = "Medium"
    due_date: date
    description: Optional[str] = None
    status: Literal["Pending", "In Progress", "Completed"] = "Pending"

    @field_validator("title", "category", mode="before")
    @classmethod
    def strip_text(cls, v: str) -> str:
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Must not be empty or whitespace only")
        return v


class TaskUpdate(BaseModel):
    model_config = {"extra": "forbid"}

    title: Optional[str] = Field(default=None, max_length=120)
    category: Optional[str] = Field(default=None, max_length=50)
    priority: Optional[Literal["High", "Medium", "Low"]] = None
    due_date: Optional[date] = None
    description: Optional[str] = None
    status: Optional[Literal["Pending", "In Progress", "Completed"]] = None

    @field_validator("title", "category", mode="before")
    @classmethod
    def strip_text(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Must not be empty or whitespace only")
        return v


class TaskResponse(BaseModel):
    id: str
    event_id: str
    title: str
    description: Optional[str] = None
    category: str
    priority: str
    due_date: date
    status: str
    is_overdue: bool
    is_upcoming: bool
    after_event_date: bool
    created_at: datetime
    updated_at: datetime


class CategoryBreakdownItem(BaseModel):
    category_id: Optional[str] = None
    category_name: str
    allocated_estimate: str
    expense_estimated_total: str
    expense_actual_total: str


class PendingPaymentItem(BaseModel):
    expense_id: str
    description: str
    payment_status: str
    estimated_amount: str
    actual_amount: str
    outstanding: str


class BudgetSummaryResponse(BaseModel):
    total_budget: str
    total_estimated: str
    total_actual: str
    remaining: str
    utilization_percent: float
    over_budget: bool
    unallocated: str
    category_breakdown: List[CategoryBreakdownItem] = []
    pending_payments: List[PendingPaymentItem] = []
    pending_total: str


class TaskSummaryResponse(BaseModel):
    total: int
    pending: int
    in_progress: int
    completed: int
    overdue: int
    upcoming: int
    progress_percent: float


class NextDeadlineInfo(BaseModel):
    title: str
    due_date: date


class TaskCounts(BaseModel):
    total: int
    completed: int
    overdue: int


class EventSummaryResponse(BaseModel):
    id: str
    name: str
    event_type: str
    event_date: date
    location: str
    guest_count: int
    total_budget: str
    currency: str
    budget_utilization_percent: float
    total_actual: str
    task_progress_percent: float
    task_counts: TaskCounts
    next_deadline: Optional[NextDeadlineInfo] = None
    total_tasks: int
    completed_tasks: int
    overdue_tasks: int


class EventDetailResponse(BaseModel):
    id: str
    name: str
    event_type: str
    event_date: date
    location: str
    guest_count: int
    total_budget: str
    currency: str
    preferred_theme: Optional[str] = None
    additional_preferences: Optional[str] = None
    generated_plan: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    budget_categories: List[BudgetCategoryResponse] = []
    expenses: List[ExpenseResponse] = []
    tasks: List[TaskResponse] = []
    budget_summary: Optional[BudgetSummaryResponse] = None
    task_summary: Optional[TaskSummaryResponse] = None
    warnings: List[str] = []

