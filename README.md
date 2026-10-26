# EventMate AI - GenAI Celebration & Event Planner

EventMate AI is an autonomous, full-stack generative AI celebration and event planning system. Given high-level celebration details (such as event type, date, location, guest count, budget, and aesthetic preferences), EventMate AI synthesizes a comprehensive execution blueprint: mathematically reconciled budgets, milestone schedules with automated overdue detection, curated aesthetic color palettes, culinary suggestions, vendor requirements, and actionable risk mitigation playbooks.

---

## Key Features Completed (Day 1)

1. **Intelligent Event Blueprint Form**:
   - Comprehensive parameters: Event Name, Category (Wedding, Birthday, Community Event), Event Date (strictly future-validated), Location, Guest Count, Budget, Currency, Aesthetic Theme, and Special Preferences.
   - Quick one-click sample presets for instant demonstration (Wedding, Birthday, Community Event).
   - Real-time client-side validation mirroring Pydantic v2 backend constraints with inline error alerts, ARIA attributes, and double-submit prevention.

2. **Official Google GenAI SDK Integration**:
   - Powered by the official `google-genai` SDK (`from google import genai`) with structured output enforcement (`response_mime_type="application/json"` and `response_schema`).
   - Defaults to `gemini-2.5-flash` with dynamic model availability verification.
   - Defensive JSON code fence stripping, single-retry schema repair on malformed responses, asynchronous thread delegation (`asyncio.to_thread`), and unified HTTP status mapping (422, 429, 502, 504, 500).

3. **Deterministic Demo Mode (Zero Key Required)**:
   - When `GEMINI_API_KEY` is omitted or empty, the backend transparently activates a rich, deterministic celebration planning engine (`source: "demo"`).
   - Generates realistic, event-tailored data with a prominent `"Demo Mode"` badge and warning.
   - Secrets are never leaked or committed.

4. **Guaranteed Budget Reconciliation (Hare-Niemeyer Algorithm)**:
   - Never trusts raw LLM arithmetic.
   - Computes allocations in integer units and distributes rounding remainders via the **Largest-Remainder Method**.
   - **Mathematical Invariant**: `sum(items.amount) == total_budget` is guaranteed to 100.00% exact equality for all numbers (even prime or awkward totals like `1`, `7`, `100,001`).
   - Enforces required categories (*Venue, Catering, Decoration, Entertainment, Photography, Miscellaneous*) plus an automatic *Contingency Reserve* fund (target 5–10%).

5. **Chronological Milestone Timeline & Overdue Safeguards**:
   - Calculates milestone due dates from `days_before` integers relative to server clock `date.today()`.
   - Automatically detects tasks with computed due dates in the past, marks them `is_overdue=true` and `is_unrealistic=true`, compresses them to today, and generates urgent warning alerts.
   - Flags events scheduled within a short preparation window (< 7 days).
   - Sorts all execution tasks chronologically by due date and priority (*High*, *Medium*, *Low*).

6. **Responsive SaaS Dashboard**:
   - Designed with modern typography (Inter), glassmorphism, and a cohesive slate/indigo theme.
   - **Executive Overview**: 5 metric summary cards (Budget, Attendance, Countdown, Venue, Theme).
   - **Financial Allocation**: Recharts interactive PieChart with custom tooltip, accessible legend, and an exact tabular breakdown.
   - **Action Checklist**: Interactive checkboxes with dynamic progress percentage calculation.
   - **Creative Directives**: Click-to-copy hex color palette swatches, decorative scenography, and catering/entertainment guides.
   - **Logistics & Risk Analysis**: Vendor load-in specifications and vulnerability mitigation cards.
   - **Working Sidebar**: Deep-link scrolling to each dashboard section on desktop and mobile.

7. **SQLite-Ready Architecture for Day 2**:
   - All response models include unique UUID `id` fields.
   - Clean separation of concerns between API routes (`app/api/routes.py`), schema definitions (`app/schemas.py`), and domain services (`app/services/`). No persistence today, completely prepared for Day 2 SQLite integration.

---

## Architecture Overview

```
EventMate AI/
├── backend/
│   ├── app/
│   │   ├── __init__.py          # sys.path resolution helper
│   │   ├── config.py            # Pydantic BaseSettings (.env loader)
│   │   ├── schemas.py           # Pydantic v2 Request, Response & AI schemas
│   │   ├── main.py              # FastAPI app, CORS, custom exception handlers
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── routes.py        # /health and /api/events/generate routes
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── ai_service.py    # Google GenAI SDK structured output & retry
│   │       ├── budget.py        # Largest-Remainder budget reconciliation
│   │       ├── timeline.py      # Timeline calculation & overdue validator
│   │       └── demo.py          # Deterministic demo engine
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_health.py       # Health checks and key leakage guard
│   │   ├── test_schemas.py      # Pydantic v2 validation rules
│   │   ├── test_budget.py       # Exact sum math and edge case tests
│   │   ├── test_timeline.py     # Date calculation and overdue checks
│   │   ├── test_demo.py         # Demo plan generation and warnings
│   │   ├── test_ai_service.py   # Mocked Gemini API errors, timeouts, repair
│   │   └── test_api_integration.py # Live client integration and CORS preflight
│   ├── requirements.txt         # Pinned backend dependencies
│   ├── .env.example             # Template for backend settings
│   └── .env                     # Local configuration
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Navbar.jsx       # Header with live health pill
│   │   │   ├── Sidebar.jsx      # Functional navigation links & drawer
│   │   │   ├── EventForm.jsx    # Accessible validated input form
│   │   │   ├── PlanOverview.jsx # Metrics cards & warnings banner
│   │   │   ├── BudgetSection.jsx# Recharts PieChart & tabular fallback
│   │   │   ├── TimelineSection.jsx # Chronological tasks & interactive checklist
│   │   │   ├── CreativeSection.jsx # Theme swatches & sensory directives
│   │   │   ├── LogisticsAndRisks.jsx # Vendors & mitigation playbook
│   │   │   ├── LoadingSkeleton.jsx # Pulsing loading progression
│   │   │   ├── ErrorBanner.jsx  # Dismissible error card with retry
│   │   │   └── EmptyState.jsx   # Guided starter screen
│   │   ├── services/
│   │   │   └── api.js           # Fetch wrapper with AbortController timeout
│   │   ├── utils/
│   │   │   └── formatters.js    # Intl.NumberFormat & date utilities
│   │   ├── App.jsx              # Application state coordinator
│   │   ├── main.jsx             # React 19 entrypoint
│   │   └── index.css            # Tailwind v4 import & design tokens
│   ├── package.json             # Frontend dependencies & scripts
│   ├── vite.config.js           # Vite 8 + @tailwindcss/vite configuration
│   ├── .env.example             # Template for frontend settings
│   └── .env                     # Local frontend configuration
├── .gitignore                   # Excludes env, venvs, caches, db, dist
└── README.md                    # Documentation & verification report
```

---

## Environment Variables

### Backend (`backend/.env`)
| Variable | Description | Default |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | Google Gemini API key. If omitted or blank, runs in Demo Mode. | *(empty)* |
| `GEMINI_MODEL` | Gemini model name. | `gemini-2.5-flash` |
| `ALLOWED_ORIGINS`| Comma-separated list of allowed CORS origins. | `http://localhost:5173,http://127.0.0.1:5173` |
| `HOST` | Backend host address. | `127.0.0.1` |
| `PORT` | Backend port number. | `8000` |

### Frontend (`frontend/.env`)
| Variable | Description | Default |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | Backend URL for API calls. | `http://localhost:8000` |

---

## Exact Windows PowerShell Setup & Run Commands

All commands below are strictly Windows PowerShell compatible.

### 1. Backend Setup & Run

Open a PowerShell terminal in the repository root (`EventMate AI`):

```powershell
# Navigate to backend directory
cd backend

# If script execution is restricted on your system:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install pinned dependencies
pip install -r requirements.txt

# Create .env from template
Copy-Item .env.example .env

# Run FastAPI backend server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Backend will be live at: **`http://127.0.0.1:8000`** (Swagger docs at `/docs`, health check at `/health`).

---

### 2. Frontend Setup & Run

Open a separate PowerShell terminal in the repository root (`EventMate AI`):

```powershell
# Navigate to frontend directory
cd frontend

# Install node dependencies
npm.cmd install

# Create .env from template
Copy-Item .env.example .env

# Start Vite development server
npm.cmd run dev
```
Frontend will be live at: **`http://127.0.0.1:5173`**.

---

### 3. Running Automated Tests & Verification

From the repository root (`EventMate AI`):

```powershell
# Run the complete Pytest suite (37 tests across health, schemas, math, timeline, AI, API)
.\backend\.venv\Scripts\pytest -v backend\tests

# Run frontend build verification
cd frontend
npm.cmd run build

# Run frontend linter
npm.cmd run lint
```

---

## Demo Mode vs. Live Gemini AI

- **Demo Mode (Default)**: Out-of-the-box, no external API key is needed. When `GEMINI_API_KEY` is not provided in `backend/.env`, EventMate AI uses a deterministic generation engine to create realistic, production-grade celebration plans for Weddings, Birthdays, and Community Events.
- **Enabling Live Gemini AI**:
  1. Obtain a Gemini API key from Google AI Studio.
  2. In `backend/.env`, set:
     ```env
     GEMINI_API_KEY=your_actual_gemini_api_key_here
     GEMINI_MODEL=gemini-2.5-flash
     ```
  3. Restart the backend service. The frontend Navbar and plan badge will dynamically switch to display **`Gemini Live (gemini-2.5-flash)`**.
