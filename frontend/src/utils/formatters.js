export function formatCurrency(amount, currency = 'INR') {
  const num = Number(amount) || 0;
  const currUpper = String(currency || 'INR').toUpperCase();
  const isZeroDecimal = ['JPY', 'KRW'].includes(currUpper);
  const localeMap = {
    INR: 'en-IN',
    USD: 'en-US',
    EUR: 'de-DE',
    GBP: 'en-GB',
    CAD: 'en-CA',
    AUD: 'en-AU',
    AED: 'ar-AE',
    SGD: 'en-SG',
    JPY: 'ja-JP',
  };

  const locale = localeMap[currUpper] || 'en-US';

  try {
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency: currUpper,
      minimumFractionDigits: isZeroDecimal ? 0 : 2,
      maximumFractionDigits: isZeroDecimal ? 0 : 2,
    }).format(num);
  } catch {
    return `${currUpper} ${num.toLocaleString(locale, {
      minimumFractionDigits: isZeroDecimal ? 0 : 2,
      maximumFractionDigits: isZeroDecimal ? 0 : 2,
    })}`;
  }
}

export function formatDate(dateStr) {
  if (!dateStr) return '';
  try {
    const parts = String(dateStr).split('T')[0].split('-');
    if (parts.length === 3) {
      const year = parseInt(parts[0], 10);
      const month = parseInt(parts[1], 10) - 1;
      const day = parseInt(parts[2], 10);
      const d = new Date(year, month, day);
      return new Intl.DateTimeFormat('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      }).format(d);
    }
    const d = new Date(dateStr);
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    }).format(d);
  } catch {
    return String(dateStr);
  }
}
