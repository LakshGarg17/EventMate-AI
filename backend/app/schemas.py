from datetime import date, datetime
import re
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


# ==========================================
# Day 3 Assistant, Proposals, Themes, Vendors
# ==========================================

class ChatHistoryItem(BaseModel):
    model_config = {"extra": "forbid"}

    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=2000)

    @field_validator("content", mode="before")
    @classmethod
    def strip_content(cls, v: str) -> str:
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("History message content cannot be empty or whitespace only")
        return v


class AssistantRequest(BaseModel):
    model_config = {"extra": "forbid"}

    message: str = Field(..., min_length=1, max_length=2000)
    history: Optional[List[ChatHistoryItem]] = Field(default_factory=list)

    @field_validator("message", mode="before")
    @classmethod
    def strip_message(cls, v: str) -> str:
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Message cannot be empty or whitespace only")
        return v


class AssistantRecommendationItem(BaseModel):
    title: str = Field(..., max_length=100)
    detail: str = Field(..., max_length=500)


class AssistantResponse(BaseModel):
    reply: str
    recommendations: List[AssistantRecommendationItem] = []
    suggested_modification_prompts: List[str] = []
    changes_applied: Literal[False] = False
    source: Literal["gemini", "demo"]
    model: Optional[str] = None
    generated_at: datetime


class AIAssistantResponse(BaseModel):
    reply: str
    recommendations: List[AssistantRecommendationItem] = Field(default_factory=list)
    suggested_modification_prompts: List[str] = Field(default_factory=list)


# ==========================================
# Day 3 Plan Modification Schemas
# ==========================================

class BudgetAdjustment(BaseModel):
    category_name: str
    delta_amount: str


class TaskToAdd(BaseModel):
    title: str
    description: Optional[str] = None
    category: str
    priority: Literal["High", "Medium", "Low"]
    due_date: str


class TaskToUpdate(BaseModel):
    task_id: str
    priority: Optional[Literal["High", "Medium", "Low"]] = None
    due_date: Optional[str] = None


class AIProposalResponse(BaseModel):
    summary: str
    new_total_budget: Optional[str] = None
    budget_adjustments: List[BudgetAdjustment] = []
    tasks_to_add: List[TaskToAdd] = []
    tasks_to_update: List[TaskToUpdate] = []
    clarification_question: Optional[str] = None


class ProposeChangesRequest(BaseModel):
    model_config = {"extra": "forbid"}

    message: str = Field(..., min_length=1, max_length=2000)

    @field_validator("message", mode="before")
    @classmethod
    def strip_message(cls, v: str) -> str:
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Message cannot be empty or whitespace only")
        return v


class ProposalBudgetCategoryPreview(BaseModel):
    name: str
    before: str
    after: str
    delta: str


class ProposalBudgetPreview(BaseModel):
    categories: List[ProposalBudgetCategoryPreview] = []
    total_before: str
    total_after: str
    allocated_before: str
    allocated_after: str
    balanced: bool


class ProposalTaskAddPreview(BaseModel):
    title: str
    description: Optional[str] = None
    category: str
    priority: str
    due_date: str


class ProposalTaskUpdatePreview(BaseModel):
    task_id: str
    title: str
    old_priority: str
    new_priority: str
    old_due_date: str
    new_due_date: str


class ProposalPreview(BaseModel):
    budget: ProposalBudgetPreview
    tasks_to_add: List[ProposalTaskAddPreview] = []
    tasks_to_update: List[ProposalTaskUpdatePreview] = []
    unchanged: str = "Expenses and the original AI plan are not modified."


class ProposalDetail(BaseModel):
    proposal_id: str
    summary: str
    preview: ProposalPreview
    warnings: List[str] = []
    expires_at: datetime


class ProposeChangesResponse(BaseModel):
    proposal: Optional[ProposalDetail] = None
    clarification: Optional[str] = None


class ApplyChangesRequest(BaseModel):
    model_config = {"extra": "forbid"}

    proposal_id: str
    confirm: bool

    @field_validator("confirm")
    @classmethod
    def validate_confirm(cls, v: bool) -> bool:
        if v is not True:
            raise ValueError("confirm must be True to apply proposal")
        return v


class ApplyChangesResponse(BaseModel):
    proposal_id: str
    status: Literal["applied"]
    message: str
    budget_summary: BudgetSummaryResponse
    task_summary: TaskSummaryResponse
    categories: List[BudgetCategoryResponse]
    tasks: List[TaskResponse]


class DiscardProposalResponse(BaseModel):
    proposal_id: str
    status: Literal["discarded"]


# ==========================================
# Day 3 Theme Recommendation Schemas
# ==========================================

class ThemePaletteColor(BaseModel):
    name: str = Field(default="Accent", max_length=50)
    hex: str = Field(default="")


class AIThemeItem(BaseModel):
    name: str
    description: str
    color_palette: List[ThemePaletteColor] = Field(default_factory=list)
    decoration_ideas: List[str] = Field(default_factory=list)
    lighting: str = Field(default="")
    venue_style: str = Field(default="")
    budget_share_percent: int = Field(default=20)
    implementation_tips: List[str] = Field(default_factory=list)


class AIThemeResponse(BaseModel):
    themes: List[AIThemeItem] = Field(default_factory=list)


class ThemeRecommendationRequest(BaseModel):
    model_config = {"extra": "forbid"}

    event_type: Literal["Wedding", "Birthday", "Community Event"]
    total_budget: Union[int, float, str]
    currency: str = Field(default="INR")
    guest_count: int = Field(..., ge=1, le=100000)
    location: str = Field(..., min_length=1, max_length=200)
    venue_type: Optional[str] = Field(default=None, max_length=100)
    preferred_style: Optional[str] = Field(default=None, max_length=100)
    additional_preferences: Optional[str] = Field(default=None, max_length=500)
    event_id: Optional[str] = None

    @field_validator("location", mode="before")
    @classmethod
    def strip_location(cls, v: str) -> str:
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Location must not be empty or whitespace only")
        return v

    @field_validator("venue_type", "preferred_style", "additional_preferences", mode="before")
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
            raise ValueError(f"Currency '{v}' is not supported.")
        return v_upper


class ThemeRecommendationItem(BaseModel):
    name: str
    description: str
    color_palette: List[ThemePaletteColor]
    decoration_ideas: List[str]
    lighting: str
    venue_style: str
    budget_share_percent: int
    estimated_decoration_budget: str
    is_estimate: Literal[True] = True
    implementation_tips: List[str]


class ThemeRecommendationResponse(BaseModel):
    themes: List[ThemeRecommendationItem]
    source: Literal["gemini", "demo"]
    model: Optional[str] = None
    generated_at: datetime


# ==========================================
# Day 3 Vendor Management & Comparison Schemas
# ==========================================

VENDOR_CATEGORIES = [
    "Catering",
    "Photography",
    "Decoration",
    "Venue",
    "Entertainment",
    "Makeup",
    "Transportation",
    "Other",
]

VENDOR_STATUSES = [
    "Considering",
    "Contacted",
    "Shortlisted",
    "Selected",
    "Rejected",
]


class VendorCreate(BaseModel):
    model_config = {"extra": "forbid"}

    name: str = Field(..., min_length=1, max_length=100)
    category: Literal[
        "Catering",
        "Photography",
        "Decoration",
        "Venue",
        "Entertainment",
        "Makeup",
        "Transportation",
        "Other",
    ]
    contact_info: Optional[str] = Field(default=None, max_length=200)
    quoted_amount: Optional[Union[int, float, str]] = None
    notes: Optional[str] = Field(default=None, max_length=1000)
    status: Literal["Considering", "Contacted", "Shortlisted", "Selected", "Rejected"] = "Considering"

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, v: str) -> str:
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Vendor name cannot be empty or whitespace only")
        return v

    @field_validator("contact_info", "notes", mode="before")
    @classmethod
    def strip_optional(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            v = v.strip()
            return v if v else None
        return v


class VendorUpdate(BaseModel):
    model_config = {"extra": "forbid"}

    name: Optional[str] = Field(default=None, max_length=100)
    category: Optional[
        Literal[
            "Catering",
            "Photography",
            "Decoration",
            "Venue",
            "Entertainment",
            "Makeup",
            "Transportation",
            "Other",
        ]
    ] = None
    contact_info: Optional[str] = Field(default=None, max_length=200)
    quoted_amount: Optional[Union[int, float, str]] = None
    notes: Optional[str] = Field(default=None, max_length=1000)
    status: Optional[
        Literal["Considering", "Contacted", "Shortlisted", "Selected", "Rejected"]
    ] = None

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Vendor name cannot be empty or whitespace only")
        return v

    @field_validator("contact_info", "notes", mode="before")
    @classmethod
    def strip_optional(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            v = v.strip()
            return v if v else None
        return v


class VendorResponse(BaseModel):
    id: str
    event_id: str
    name: str
    category: str
    contact_info: Optional[str] = None
    quoted_amount: Optional[str] = None
    notes: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime


class VendorComparisonItem(BaseModel):
    id: str
    name: str
    category: str
    status: str
    quoted_amount: Optional[str] = None
    difference_from_lowest: Optional[str] = None
    is_lowest: bool = False
    is_selected: bool = False


class VendorCategoryComparison(BaseModel):
    category: str
    vendors: List[VendorComparisonItem] = []
    lowest_quote: Optional[str] = None
    lowest_vendor_ids: List[str] = []
    selected_vendors: List[str] = []
    multiple_selected: bool = False


class VendorComparisonResponse(BaseModel):
    event_id: str
    event_total_budget: str
    currency: str
    selected_total: str
    missing_quotes: List[str] = []
    categories: List[VendorCategoryComparison] = []


# ==========================================
# Day 3 Invitation Generator Schemas
# ==========================================

class InvitationRequest(BaseModel):
    model_config = {"extra": "forbid"}

    event_type: Literal["Wedding", "Birthday", "Community Event"]
    host_name: str = Field(..., min_length=1, max_length=80)
    event_date: date
    event_time: str = Field(..., description="24-hour HH:MM time format")
    location: str = Field(..., min_length=1, max_length=200)
    language: Literal["English", "Hindi"] = "English"
    tone: Literal["Formal", "Elegant", "Friendly", "Traditional", "Fun"] = "Elegant"
    additional_instructions: Optional[str] = Field(default=None, max_length=500)

    @field_validator("host_name", "location", mode="before")
    @classmethod
    def strip_text(cls, v: str) -> str:
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Must not be empty or whitespace only")
        return v

    @field_validator("additional_instructions", mode="before")
    @classmethod
    def strip_instructions(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            v = v.strip()
            return v if v else None
        return v

    @field_validator("event_date")
    @classmethod
    def validate_date(cls, v: date) -> date:
        try:
            from app.services.today import get_today
        except ImportError:
            from backend.app.services.today import get_today
        today = get_today()
        if v < today:
            raise ValueError(f"Event date must be today ({today.isoformat()}) or later")
        return v

    @field_validator("event_time")
    @classmethod
    def validate_time(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("event_time must be a string")
        clean_v = v.strip()
        time_match = re.match(r"^([01]\d|2[0-3]):([0-5]\d)$", clean_v)
        if not time_match:
            raise ValueError(f"event_time '{v}' must be in 24-hour HH:MM format (00:00 to 23:59)")
        hours, minutes = int(time_match.group(1)), int(time_match.group(2))
        if not (0 <= hours <= 23 and 0 <= minutes <= 59):
            raise ValueError(f"Invalid time range in '{v}'")
        return clean_v


class AIInvitationResponse(BaseModel):
    invitation_text: str


class InvitationResponse(BaseModel):
    invitation_text: str
    language: str
    tone: str
    source: Literal["gemini", "demo"]
    model: Optional[str] = None
    generated_at: datetime






