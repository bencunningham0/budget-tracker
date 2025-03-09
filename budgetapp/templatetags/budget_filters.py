from django import template
from decimal import Decimal
import re

register = template.Library()

@register.filter
def div(value, arg):
    """Divide the value by the argument"""
    try:
        return Decimal(value) / Decimal(arg)
    except (ValueError, ZeroDivisionError):
        return Decimal('0')
        
@register.filter
def mul(value, arg):
    """Multiply the value by the argument"""
    try:
        return Decimal(value) * Decimal(arg)
    except ValueError:
        return Decimal('0')

@register.filter
def abs(value):
    """Return the absolute value"""
    try:
        return abs(Decimal(value))
    except ValueError:
        return Decimal('0')

@register.filter
def intcomma(value):
    """Adds commas to an integer or decimal number for thousand separators"""
    try:
        if isinstance(value, Decimal):
            value_str = str(value)
        else:
            value_str = str(value)
            
        # Handle decimal part separately
        if '.' in value_str:
            int_part, decimal_part = value_str.split('.')
        else:
            int_part, decimal_part = value_str, ''
            
        # Add commas to the integer part
        int_part = re.sub(r"^(-?\d+)(\d{3})", r"\g<1>,\g<2>", int_part)
        while re.search(r"(\d)(\d{3}[,.])", int_part):
            int_part = re.sub(r"(\d)(\d{3}[,.])", r"\1,\2", int_part)
            
        # Return the formatted number
        if decimal_part:
            return f"{int_part}.{decimal_part}"
        return int_part
    except (ValueError, TypeError):
        return value