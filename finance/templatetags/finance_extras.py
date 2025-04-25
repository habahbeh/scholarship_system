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