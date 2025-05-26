from django import template
from django.template.defaultfilters import floatformat
from decimal import Decimal, ROUND_HALF_UP
import re

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


@register.filter
def format_number(value, decimal_places=2):
    """
    تنسيق الرقم مع نقطة عشرية (.) وفواصل للآلاف (,)
    مثال: 1,234.56
    """
    if value is None:
        return "0.00"

    try:
        # تحويل القيمة إلى Decimal للتعامل الدقيق
        decimal_value = Decimal(str(value))

        # تقريب القيمة
        rounded_value = decimal_value.quantize(
            Decimal('0.' + '0' * int(decimal_places)),
            rounding=ROUND_HALF_UP
        )

        # تحويل إلى نص مع تحديد عدد المنازل العشرية
        formatted = f"{rounded_value:.{decimal_places}f}"

        # إضافة فواصل للآلاف يدوياً
        parts = formatted.split('.')
        integer_part = parts[0]
        decimal_part = parts[1] if len(parts) > 1 else ""

        # إضافة الفواصل للآلاف (كل 3 أرقام)
        integer_with_commas = ""
        for i in range(len(integer_part), 0, -3):
            start = max(0, i - 3)
            if i == len(integer_part):
                integer_with_commas = integer_part[start:i] + integer_with_commas
            else:
                integer_with_commas = integer_part[start:i] + "," + integer_with_commas

        # إعادة تجميع الرقم
        if decimal_part:
            return f"{integer_with_commas}.{decimal_part}"
        else:
            return integer_with_commas
    except:
        # في حالة الخطأ، إرجاع القيمة كما هي
        return str(value)


@register.filter
def amount_with_currency(value, decimal_places=2):
    """
    تنسيق المبلغ مع نقطة عشرية (.) وفواصل للآلاف (,) مع إضافة رمز العملة
    مثال: 1,234.56 د.أ
    """
    formatted = format_number(value, decimal_places)
    return f"{formatted} د.أ"


@register.filter
def multiply(value, arg):
    """
    Multiplica el valor por el argumento.

    Ejemplo: {{ value|multiply:10 }}
    """
    try:
        value = Decimal(str(value))
        arg = Decimal(str(arg))
        result = value * arg
        # Redondear a 2 decimales
        return result.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except (ValueError, TypeError):
        return value


@register.filter
def divide(value, arg):
    """
    Divide el valor por el argumento.

    Ejemplo: {{ value|divide:10 }}
    """
    try:
        value = Decimal(str(value))
        arg = Decimal(str(arg))
        if arg == 0:
            return 0
        result = value / arg
        # Redondear a 2 decimales
        return result.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except (ValueError, TypeError):
        return value


@register.filter
def subtract(value, arg):
    """
    Resta el argumento del valor.

    Ejemplo: {{ value|subtract:10 }}
    """
    try:
        value = Decimal(str(value))
        arg = Decimal(str(arg))
        result = value - arg
        # Redondear a 2 decimales
        return result.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except (ValueError, TypeError):
        return value