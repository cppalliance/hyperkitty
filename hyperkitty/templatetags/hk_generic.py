# -*- coding: utf-8 -*-
#
# Copyright (C) 2012-2023 by the Free Software Foundation, Inc.
#
# This file is part of HyperKitty.
#
# HyperKitty is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# HyperKitty is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# HyperKitty.  If not, see <http://www.gnu.org/licenses/>.
#
# Author: Aurelien Bompard <abompard@fedoraproject.org>
#

import datetime
import json
import re
from collections import OrderedDict

from django import template
from django.conf import settings
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from django.utils.timezone import utc

from dateutil.tz import tzoffset
from django_gravatar.templatetags.gravatar import gravatar as gravatar_orig

import hyperkitty.lib.posting
from hyperkitty.lib.utils import stripped_subject


register = template.Library()

MAILTO_RE = re.compile(
    "<a href=['\"]mailto:([^'\"]+)@([^'\"]+)['\"]>[^<]+</a>")
SNIPPED_RE = re.compile(r"^(\s*&gt;).*$", re.M)
SNIPPED_BEGIN_PGP = re.compile("^.*(BEGIN PGP SIGNATURE).*$", re.M)
SNIPPED_END_PGP = re.compile("^.*(END PGP SIGNATURE).*$", re.M)


@register.filter(name='sort')
def listsort(value):
    if isinstance(value, dict):
        new_dict = OrderedDict()
        key_list = sorted(value.keys())
        key_list.reverse()
        for key in key_list:
            values = sorted(value[key])
            values.reverse()
            new_dict[key] = values
        return new_dict.items()
    elif isinstance(value, list):
        return sorted(value)
    else:
        return value
    listsort.is_safe = True


@register.filter(name="monthtodate")
def to_date(month, year):
    return datetime.date(year, month, 1)


# From http://djangosnippets.org/snippets/1259/
@register.filter
def truncatesmart(value, limit=80):
    """
    Truncates a string after a given number of chars keeping whole words.

    Usage:
        {{ string|truncatesmart }}
        {{ string|truncatesmart:50 }}
    """
    try:
        limit = int(limit)
    # invalid literal for int()
    except ValueError:
        # Fail silently.
        return value

    # Return the string itself if length is smaller or equal to the limit
    if len(value) <= limit:
        return value

    # Cut the string
    value = value[:limit]

    # Break into words and remove the last
    words = value.split(' ')[:-1]

    # Join the words and return
    return ' '.join(words) + '...'


@register.filter(is_safe=True)
def escapeemail(text):
    """To escape email addresses"""
    return text.replace("@", "\uff20")


@register.filter(is_safe=True)
def escapeemaillinks(text):
    """To escape email addresses in links"""
    # reverse the effect of urlize() on email addresses
    return MAILTO_RE.sub(r"\1(a)\2", text)


@register.filter()
def date_with_senders_timezone(email):
    """
    Rebuild the date of an email taking the sender's timezone into account.
    """
    # tzoffset requires seconds
    tz = tzoffset(None, email.timezone * 60)
    return email.date.astimezone(tz)


@register.filter(needs_autoescape=True)
def snip_quoted(content, quotemsg="...",
                autoescape=None, add_switch=True, quote_index=0):
    """Snip quoted text in messages.

    This method recursively tries to find quoted text in an email and return
    HTML with proper quotes. We process only 4 levels of indent so as to
    prevent too much processing of text.

    :param content: The content to be quoted.
    :param quotemsg: The content of the switch which shows and hides the
        quoted text.
    :param add_switch: Boolean specifying if we should add the switch to
         show-hide quoted content. To prevent having too many switches,
         we only add a single switch to the top-level quoted text.
    :param quote_index: Which level of nested quote we are in. This is
         incremented on a recursive call and we limit it to a maximum
         of 3, starting from 0.

    """
    # We don't want to go into infinite loop of quoting, so we limit the
    # quoting to 0-3, 4 levels only.

    # XXX(maxking): This function is currently unused since we switched to
    # using markdown rendering from decorate.py. I am going to keep this around
    # for a white till we are sure using the markdown renderer is good to
    # replace this.
    if quote_index > 3 or quote_index < 0:
        return content
    if autoescape:
        content = conditional_escape(content)
    quoted = []
    current_quote = []
    current_quote_orig = []
    for line in content.split("\n"):
        match = SNIPPED_RE.match(line)
        if match is not None:
            current_quote_orig.append(line)
            content_start = len(match.group(1))
            current_quote.append(line[content_start:])
        else:
            if current_quote_orig:
                current_quote_orig.append("")
                quoted.append((current_quote_orig[:], current_quote[:]))
                current_quote = []
                current_quote_orig = []

    for quote_orig, quote in quoted:
        replaced = ''
        # Add a switch if we are needed to, usually, this is used for the first
        # level of quoting. Any further nested levels do not require a switch.
        if add_switch:
            replaced = (
                '<div class="quoted-switch">'
                '<a style="font-weight:normal" href="#">{quotemsg}</a>'
                '</div>').format(quotemsg=quotemsg)
        # Finally, generate the quoted content. We recursively call
        # `snip_quoted` to process further levels of quotes in the message.
        replaced += (
            '<div class="quoted-text quoted-text-{index}"> {quote} </div>'
        ).format(
            quote=snip_quoted("\n".join(quote),
                              add_switch=False, quote_index=quote_index+1),
            index=quote_index)
        # Replace the original content with the new one.
        content = content.replace("\n".join(quote_orig), replaced)
    return mark_safe(content)


@register.filter(needs_autoescape=True)
def snip_pgp(content, quotemsg="...PGP SIGNATURE...", autoescape=None):
    """Snip pgp signature in messages"""
    if autoescape:
        content = conditional_escape(content)
    quoted = []
    current_quote = []
    current_quote_orig = []
    pgp_signature = False
    for line in content.split("\n"):
        match_start = SNIPPED_BEGIN_PGP.match(line)
        match_end = SNIPPED_END_PGP.match(line)
        if match_end is not None or match_start is not None or pgp_signature:
            current_quote_orig.append(line)
            current_quote.append(line)
        # start of pgp signature
        if match_start is not None:
            pgp_signature = True
        # end of pgp signature
        elif match_end is not None:
            pgp_signature = False
            if current_quote_orig:
                current_quote_orig.append("")
                quoted.append((current_quote_orig[:], current_quote[:]))
                current_quote = []
                current_quote_orig = []
    for quote_orig, quote in quoted:
        replaced = (
            '<div class="quoted-switch">'
            '<a href="#" class="pgp">{quotemsg}</a></div>'
            '<div class="quoted-text">{quote} </div>'
            ).format(quotemsg=quotemsg, quote="\n".join(quote))
        content = content.replace("\n".join(quote_orig), replaced)
    return mark_safe(content)


@register.filter()
def multiply(num1, num2):
    if int(num2) == float(num2):
        num2 = int(num2)
    else:
        num2 = float(num2)
    return num1 * num2


@register.simple_tag(takes_context=True)
def is_message_new(context, refdate):
    user = context["user"]
    if "last_view" not in context:
        return False  # viewing a single message
    last_view = context["last_view"]
    refdate = refdate.replace(tzinfo=utc)
    return (
        user.is_authenticated and
        (not last_view or refdate > last_view)
        )


@register.filter
def until(value, limit):
    return value.partition(limit)[0]


@register.filter
def to_json(value):
    return json.dumps(value)


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter(is_safe=True)
def num_comments(thread):
    """Returns the number of comments in a thread"""
    try:
        return thread.emails_count - 1
    except (ValueError, TypeError):
        return ''


@register.filter
def reply_subject(value):
    return hyperkitty.lib.posting.reply_subject(value)


@register.filter(name="strip_subject")
def strip_subject(subject, mlist):
    return stripped_subject(mlist, subject)


@register.filter
def is_unread_by(thread, user):
    return thread.is_unread_by(user)


@register.filter
def sort_by_name(p_list):
    return sorted(p_list, key=lambda p: p.name and p.name.lower())


@register.simple_tag()
def gravatar(*args, **kw):
    """A proxy for django-gravatar's template.

    This templatetag allows disabling Gravatar altogether using
    HYPERKITTY_ENABLE_GRAVATAR setting, which is True by default.
    """
    if not getattr(settings, 'HYPERKITTY_ENABLE_GRAVATAR', True):
        return mark_safe('')
    return gravatar_orig(*args, **kw)


@register.simple_tag()
def settings_value_equals(name, value):
    """Get the settings value to use in templates.

    Default value is set to empty string, which might not work for all settings
    types.
    """
    return getattr(settings, name, '') == value


@register.simple_tag()
def export_allowed():
    """Returns the HYPERKITTY_MBOX_EXPORT settings value. Defaults to True."""
    return getattr(settings, 'HYPERKITTY_MBOX_EXPORT', True)
