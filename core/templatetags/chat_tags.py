import re
from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter(name='format_mentions')
def format_mentions(value):
    if not value:
        return ""
    escaped_value = escape(value)
    formatted = re.sub(
        r'@([a-zA-Z0-9_\.\-]+)',
        r'<span style="background: rgba(59, 130, 246, 0.18); color: #2563eb; font-weight: 700; padding: 2px 6px; border-radius: 4px; display: inline-block; font-size: 0.95em; border: 1px solid rgba(59, 130, 246, 0.3);">@\1</span>',
        escaped_value
    )
    return mark_safe(formatted)
