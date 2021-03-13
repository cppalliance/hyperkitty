from django import template
from django.utils.safestring import mark_safe

from hyperkitty.lib.renderer import markdown_renderer


register = template.Library()


@register.filter()
def markdownify(value):
    return mark_safe(markdown_renderer(value))
