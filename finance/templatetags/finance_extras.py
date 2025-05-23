from django import template
from django.template.defaultfilters import floatformat

register = template.Library()

@register.filter(name='mul')
def mul(value, arg):
    """Multiplies the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return value

@register.filter(name='div')
def div(value, arg):
    """Divides the value by the argument"""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter(name='sub')
def sub(value, arg):
    """Subtracts the argument from the value"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return value

@register.filter(name='add')
def add(value, arg):
    """Adds the argument to the value"""
    try:
        return float(value) + float(arg)
    except (ValueError, TypeError):
        return value

@register.filter(name='abs')
def abs_filter(value):
    """Returns the absolute value"""
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return value

@register.filter(name='get_item')
def get_item(dictionary, key):
    """Gets an item from a dictionary"""
    return dictionary.get(key)

@register.filter(name='filter_by_status')
def filter_by_status(queryset, status):
    """Filters a queryset by status"""
    return [item for item in queryset if item.status == status]


@register.filter
def currency(value):
    """عرض المبلغ بتنسيق العملة مع تقريب دقيق"""
    if not value:
        return "0.00 د.أ"

    try:
        decimal_value = Decimal(str(value))
        rounded_value = decimal_value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return f"{rounded_value:.2f} د.أ"
    except:
        return f"{value} د.أ"


@register.filter
def percentage(value):
    """عرض النسبة المئوية مع تقريب دقيق"""
    if not value:
        return "0.0%"

    try:
        decimal_value = Decimal(str(value))
        rounded_value = decimal_value.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
        return f"{rounded_value:.1f}%"
    except:
        return f"{value}%"