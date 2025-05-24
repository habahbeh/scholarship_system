# core/templatetags/currency_format.py

from django import template
from django.conf import settings
import locale
from django.utils import translation

register = template.Library()


@register.filter(name='currency')
def currency_format(value, decimal_places=2):
    """
    Format a number as currency with English numerals.
    The locale is already set to English for numbers by the middleware.
    """
    if value is None:
        return "0.00"

    try:
        # Format with specified decimal places
        formatted = f"{float(value):.{decimal_places}f}"

        # Add thousand separators
        parts = formatted.split('.')
        parts[0] = "{:,}".format(int(parts[0]))

        if len(parts) > 1:
            return f"{parts[0]}.{parts[1]}"
        return parts[0]
    except (ValueError, TypeError):
        return str(value)


@register.filter(name='currency_with_symbol')
def currency_with_symbol(value, symbol='JD'):
    """
    Format a number as currency with a specified symbol.
    Usage: {{ value|currency_with_symbol:"JD" }}
    """
    formatted = currency_format(value)

    # Handle RTL/LTR formatting based on current language
    if translation.get_language() == 'ar':
        return f"{formatted} {symbol}"
    else:
        return f"{symbol} {formatted}"