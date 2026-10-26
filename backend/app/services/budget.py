try:
    from app.schemas import BudgetBreakdown, BudgetItem, RawAIBudgetItem
except ImportError:
    from backend.app.schemas import BudgetBreakdown, BudgetItem, RawAIBudgetItem


REQUIRED_CATEGORIES = [
    "Venue",
    "Catering",
    "Decoration",
    "Entertainment",
    "Photography",
    "Miscellaneous",
    "Contingency Reserve",
]

DEFAULT_PERCENTAGES: Dict[str, Dict[str, int]] = {
    "Wedding": {
        "Venue": 30,
        "Catering": 30,
        "Decoration": 15,
        "Photography": 10,
        "Entertainment": 5,
        "Miscellaneous": 3,
        "Contingency Reserve": 7,
    },
    "Birthday": {
        "Venue": 25,
        "Catering": 35,
        "Decoration": 15,
        "Entertainment": 10,
        "Photography": 5,
        "Miscellaneous": 3,
        "Contingency Reserve": 7,
    },
    "Community Event": {
        "Venue": 25,
        "Catering": 30,
        "Decoration": 10,
        "Entertainment": 15,
        "Photography": 5,
        "Miscellaneous": 7,
        "Contingency Reserve": 8,
    },
}


def canonical_category(cat: str) -> str:
    cleaned = cat.strip()
    lower = cleaned.lower()
    if "venue" in lower or "hall" in lower or "space" in lower:
        return "Venue"
    if "cater" in lower or "food" in lower or "beverage" in lower or "dining" in lower:
        return "Catering"
    if "decor" in lower or "flower" in lower or "light" in lower:
        return "Decoration"
    if "entertain" in lower or "music" in lower or "dj" in lower or "sound" in lower:
        return "Entertainment"
    if "photo" in lower or "video" in lower or "media" in lower:
        return "Photography"
    if "conting" in lower or "buffer" in lower or "reserve" in lower or "emergency" in lower:
        return "Contingency Reserve"
    if "misc" in lower or "other" in lower:
        return "Miscellaneous"
    return cleaned.title()


def reconcile_budget(
    total_budget: int,
    raw_items: Optional[List[RawAIBudgetItem]],
    event_type: str,
    currency: str = "INR"
) -> BudgetBreakdown:
    """
    Deterministically reconciles budget items using the Largest-Remainder Method (Hare-Niemeyer).
    Guarantees:
      1. sum(item.amount for item in items) == total_budget exactly.
      2. All amounts are non-negative integers.
      3. All required categories exist (Venue, Catering, Decoration, Entertainment, Photography, Miscellaneous, Contingency Reserve).
      4. Contingency Reserve is present (target 5-10%).
      5. Percentages are recomputed server-side.
    """
    if total_budget <= 0:
        raise ValueError("total_budget must be greater than 0")

    defaults = DEFAULT_PERCENTAGES.get(event_type, DEFAULT_PERCENTAGES["Community Event"])

    # Map raw items by canonical category
    category_weights: Dict[str, int] = {}
    category_notes: Dict[str, str] = {}

    if raw_items:
        for item in raw_items:
            cat = canonical_category(item.category)
            if not cat:
                continue
            amt = max(0, int(item.estimated_amount or 0))
            category_weights[cat] = category_weights.get(cat, 0) + amt
            if item.notes:
                prev_notes = category_notes.get(cat, "")
                category_notes[cat] = f"{prev_notes}; {item.notes}".strip("; ") if prev_notes else item.notes

    # Ensure all required categories exist
    for req_cat in REQUIRED_CATEGORIES:
        if req_cat not in category_weights or category_weights[req_cat] <= 0:
            category_weights[req_cat] = defaults.get(req_cat, 5)
            if req_cat not in category_notes:
                category_notes[req_cat] = f"Estimated allocation for {req_cat.lower()}"

    # Ensure Contingency Reserve is present and has at least ~5% relative weight
    total_weight = sum(category_weights.values())
    if total_weight > 0:
        contingency_weight = category_weights.get("Contingency Reserve", 0)
        min_contingency_weight = int(total_weight * 0.07)
        if contingency_weight < min_contingency_weight:
            category_weights["Contingency Reserve"] = max(min_contingency_weight, defaults.get("Contingency Reserve", 7))
            total_weight = sum(category_weights.values())

    # If all weights are 0 or empty, fall back to default percentages
    if total_weight <= 0:
        category_weights = {k: v for k, v in defaults.items()}
        total_weight = sum(category_weights.values())

    # Largest-Remainder Method (Hare-Niemeyer)
    # 1. Compute exact shares and integer parts
    categories = list(category_weights.keys())
    # Sort categories to preserve consistent ordering (Required first, then others)
    categories.sort(key=lambda c: (0 if c in REQUIRED_CATEGORIES else 1, REQUIRED_CATEGORIES.index(c) if c in REQUIRED_CATEGORIES else c))

    allocated_amounts: Dict[str, int] = {}
    remainders: List[tuple[float, int, str]] = []  # (-remainder, index, category) for max-heap behavior
    current_allocated_sum = 0

    for idx, cat in enumerate(categories):
        weight = category_weights[cat]
        exact_share = (weight * total_budget) / total_weight
        int_part = int(exact_share)
        allocated_amounts[cat] = int_part
        current_allocated_sum += int_part
        remainders.append((exact_share - int_part, idx, cat))

    # 2. Distribute leftover remainder units to categories with largest fractional parts
    diff = total_budget - current_allocated_sum
    # Sort by remainder descending, tie-break by index
    remainders.sort(key=lambda x: (-x[0], x[1]))

    for i in range(min(diff, len(remainders))):
        cat = remainders[i][2]
        allocated_amounts[cat] += 1
        current_allocated_sum += 1

    # In rare cases where diff > len(remainders) (e.g. edge cases), distribute remaining to first item
    while current_allocated_sum < total_budget:
        allocated_amounts[categories[0]] += 1
        current_allocated_sum += 1

    # 3. Assemble final BudgetItem list
    items: List[BudgetItem] = []
    contingency_amount = allocated_amounts.get("Contingency Reserve", 0)

    for cat in categories:
        amt = allocated_amounts[cat]
        pct = round((amt / total_budget) * 100.0, 2)
        notes = category_notes.get(cat, f"Estimated budget allocation for {cat.lower()}")
        if "estimated" not in notes.lower():
            notes = f"{notes} (Estimated)"
        items.append(
            BudgetItem(
                category=cat,
                amount=amt,
                percentage=pct,
                notes=notes
            )
        )

    return BudgetBreakdown(
        items=items,
        total_allocated=total_budget,
        currency=currency,
        contingency=contingency_amount,
        is_estimate=True
    )
