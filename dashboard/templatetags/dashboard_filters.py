from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiplies the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''

@register.filter
def sub(value, arg):
    """Subtracts the argument from the value"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return ''

@register.filter
def div(value, arg):
    """Divides the value by the argument"""
    try:
        if float(arg) != 0:
            return float(value) / float(arg)
        return 0
    except (ValueError, TypeError):
        return ''

@register.filter
def percentage(value, arg):
    """Calculates the percentage of value to arg"""
    try:
        if float(arg) != 0:
            return (float(value) / float(arg)) * 100
        return 0
    except (ValueError, TypeError):
        return 0

@register.filter
def get_range(value):
    """Returns a range of numbers from 0 to value-1"""
    return range(int(value))

@register.filter
def index(sequence, position):
    """Returns the item at the given position in the sequence"""
    try:
        return sequence[position]
    except:
        return None

@register.filter
def endswith(value, arg):
    """Checks if the value ends with the specified argument"""
    try:
        return value.endswith(arg)
    except (AttributeError, TypeError):
        return False

@register.filter
def startswith(value, arg):
    """Checks if the value starts with the specified argument"""
    try:
        return value.startswith(arg)
    except (AttributeError, TypeError):
        return False


@register.filter
def yesno(value, arg=None):
    """
    Given a string mapping values for true, false and (optionally) None,
    returns one of those strings according to the value:

    ==========  ======================  ==================================
    Value       Argument                Outputs
    ==========  ======================  ==================================
    ``True``    ``"yeah,no,maybe"``    ``yeah``
    ``False``   ``"yeah,no,maybe"``    ``no``
    ``None``    ``"yeah,no,maybe"``    ``maybe``
    ``None``    ``"yeah,no"``          ``"no"`` (converts None to False)
    ==========  ======================  ==================================
    """
    if arg is None:
        arg = "yes,no,maybe"
    bits = arg.split(',')
    if len(bits) < 2:
        return value  # Invalid arg.

    # Safer way to extract values - avoids unpacking error
    yes = bits[0]
    no = bits[1]
    maybe = bits[2] if len(bits) > 2 else no

    if value is None:
        return maybe
    if value:
        return yes
    return no

@register.filter
def mul(value, arg):
    """Multiplies the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''