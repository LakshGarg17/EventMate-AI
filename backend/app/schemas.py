from datetime import date, datetime
from typing import List, Literal, Optional
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
