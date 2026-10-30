from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Union

# Exponent table for currencies: 0 for zero-decimal currencies, default is 2
CURRENCY_EXPONENTS: Dict[str, int] = {
    "JPY": 0,
    "KRW": 0,
    "BHD": 3,
    "KWD": 3,
    "OMR": 3,
}

DEFAULT_EXPONENT = 2
MAX_MAJOR_UNITS = Decimal("100000000000")  # 10^11 sane cap


def get_currency_exponent(currency: str) -> int:
    """Returns number of decimal digits for a given currency code."""
    return CURRENCY_EXPONENTS.get(currency.strip().upper(), DEFAULT_EXPONENT)


def validate_and_parse_money(
    value: Any,
    currency: str = "INR",
    field_name: str = "amount"
) -> Decimal:
    """
    Parses money input via Decimal(str(value)) and rejects:
    - Non-numeric formats
    - Negative values
    - Values exceeding the sane cap (10^11 major units)
    - Values with more decimal places than allowed for the currency
    """
    if value is None:
        raise ValueError(f"{field_name} is required")

    val_str = str(value).strip()
    if not val_str:
        raise ValueError(f"{field_name} cannot be empty")

    try:
        dec = Decimal(val_str)
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"{field_name} must be a valid numeric amount")

    if dec.is_nan() or dec.is_infinite():
        raise ValueError(f"{field_name} must be a finite number")

    if dec < 0:
        raise ValueError(f"{field_name} cannot be negative")

    if dec > MAX_MAJOR_UNITS:
        raise ValueError(f"{field_name} exceeds maximum permitted limit")

    exp = get_currency_exponent(currency)
    # Check decimal places
    if dec.as_tuple().exponent < -exp:
        raise ValueError(
            f"{field_name} has more decimal places than allowed for currency '{currency}' ({exp} allowed)"
        )

    return dec


def to_minor(amount: Union[Decimal, str, int, float], currency: str = "INR") -> int:
    """Converts a major units Decimal amount to integer minor units."""
    if not isinstance(amount, Decimal):
        amount = validate_and_parse_money(amount, currency)
    exp = get_currency_exponent(currency)
    factor = Decimal(10 ** exp)
    return int((amount * factor).to_integral_exact())


def from_minor(minor: int, currency: str = "INR") -> str:
    """Converts integer minor units to a formatted decimal string with correct precision."""
    if minor is None:
        minor = 0
    exp = get_currency_exponent(currency)
    if exp == 0:
        return str(minor)
    factor = Decimal(10 ** exp)
    d = Decimal(minor) / factor
    return f"{d:.{exp}f}"
