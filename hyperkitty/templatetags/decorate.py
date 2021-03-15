from django import template
from django.utils.safestring import mark_safe

from hyperkitty.lib.renderer import markdown_renderer, text_renderer
from hyperkitty.models.mailinglist import ArchiveRenderingMode


register = template.Library()


@register.filter()
def render(value, mlist):
    """Render the email content based on MailingList settings.

    This enables MailingList owners to choose between the two available
    renderer using MailingList settings in Postorius.

    :param value: The text value to render.
    :param mlist: The MailingList object this email belongs to.
    :returns: The rendered HTML form the input value text.
    """
    if mlist.archive_rendering_mode == ArchiveRenderingMode.markdown.name:
        return mark_safe(markdown_renderer(value))
    return mark_safe(text_renderer(value))
