from django.utils.dateparse import parse_date
from django import template
register = template.Library()

@register.filter
def iso_to_date(value):
    return parse_date(value)