from contextlib import suppress

from django import template
from django.utils.safestring import mark_safe

from hyperkitty.lib.renderer import markdown_renderer, text_renderer
from hyperkitty.models.mailinglist import ArchiveRenderingMode


register = template.Library()


@register.filter()
def render(email, mlist):
    """Render the email content based on MailingList settings.

    This enables MailingList owners to choose between the two available
    renderer using MailingList settings in Postorius.

    In case the display is rendered in fixed_width font because there is
    a patch in it, do not use markdown mode since that mucks with the
    code.

    :param value: The text value to render.
    :param mlist: The MailingList object this email belongs to.
    :returns: The rendered HTML form the input value text.
    """
    try:
        content = email.content
        display_fixed = email.display_fixed
    except AttributeError:
        content = email.get('content', '')
        display_fixed = email.get('display_fixed', False)

    if (
        mlist.archive_rendering_mode == ArchiveRenderingMode.markdown.name and
        not display_fixed
    ):
        with suppress(TypeError):
            return mark_safe(markdown_renderer(content))
    try:
        return mark_safe(text_renderer(content))
    except (KeyError, ValueError):
        return mark_safe('<pre>' + content + '</pre>')
