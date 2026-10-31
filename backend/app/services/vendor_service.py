"""
Vendor quotation comparison and analysis service.
Groups vendors by category, computes lowest quotes (excluding Rejected vendors),
identifies selected vendors and multiple selection anomalies, and tracks total selected spend.
"""

from typing import Dict, List, Optional
from app.db.models import Event, Vendor
from app.schemas import (
    VENDOR_CATEGORIES,
    VendorCategoryComparison,
    VendorComparisonItem,
    VendorComparisonResponse,
)
from app.services.currency import from_minor


def compute_vendor_comparison(event: Event) -> VendorComparisonResponse:
    """Computes category-by-category quotation comparison for an event."""
    currency = event.currency
    vendors: List[Vendor] = event.vendors or []

    # Group vendors by known categories
    cats_dict: Dict[str, List[Vendor]] = {cat: [] for cat in VENDOR_CATEGORIES}
    for v in vendors:
        cat = v.category if v.category in cats_dict else "Other"
        cats_dict[cat].append(v)

    category_comparisons: List[VendorCategoryComparison] = []
    selected_total_minor = 0
    missing_quotes_list: List[str] = []

    for cat_name in VENDOR_CATEGORIES:
        cat_vendors = cats_dict.get(cat_name, [])
        if not cat_vendors:
            continue

        # Lowest quote: lowest non-null quote among vendors whose status is NOT Rejected
        non_rejected_quoted = [
            v for v in cat_vendors
            if v.status != "Rejected" and v.quoted_amount is not None
        ]

        lowest_quote_minor: Optional[int] = None
        lowest_vendor_ids: List[str] = []

        if non_rejected_quoted:
            min_val = min(v.quoted_amount for v in non_rejected_quoted)
            lowest_quote_minor = min_val
            lowest_vendor_ids = [v.id for v in non_rejected_quoted if v.quoted_amount == min_val]

        selected_vendors = [v.name for v in cat_vendors if v.status == "Selected"]
        multiple_selected = len(selected_vendors) > 1

        # Sort category vendors: quoted vendors asc (lowest first), null quotes last, then created_at asc
        def vendor_sort_key(v: Vendor):
            has_quote = 0 if v.quoted_amount is not None else 1
            amt = v.quoted_amount if v.quoted_amount is not None else 0
            return (has_quote, amt, v.created_at)

        sorted_vendors = sorted(cat_vendors, key=vendor_sort_key)
        comp_items: List[VendorComparisonItem] = []

        for v in sorted_vendors:
            is_sel = (v.status == "Selected")
            if is_sel:
                if v.quoted_amount is not None:
                    selected_total_minor += v.quoted_amount
                else:
                    missing_quotes_list.append(v.name)

            diff_str = None
            if v.quoted_amount is not None and lowest_quote_minor is not None:
                diff_minor = v.quoted_amount - lowest_quote_minor
                diff_str = from_minor(diff_minor, currency)

            comp_items.append(
                VendorComparisonItem(
                    id=v.id,
                    name=v.name,
                    category=v.category,
                    status=v.status,
                    quoted_amount=from_minor(v.quoted_amount, currency) if v.quoted_amount is not None else None,
                    difference_from_lowest=diff_str,
                    is_lowest=(v.id in lowest_vendor_ids),
                    is_selected=is_sel,
                )
            )

        category_comparisons.append(
            VendorCategoryComparison(
                category=cat_name,
                vendors=comp_items,
                lowest_quote=from_minor(lowest_quote_minor, currency) if lowest_quote_minor is not None else None,
                lowest_vendor_ids=lowest_vendor_ids,
                selected_vendors=selected_vendors,
                multiple_selected=multiple_selected,
            )
        )

    return VendorComparisonResponse(
        event_id=event.id,
        event_total_budget=from_minor(event.total_budget, currency),
        currency=currency,
        selected_total=from_minor(selected_total_minor, currency),
        missing_quotes=missing_quotes_list,
        categories=category_comparisons,
    )

