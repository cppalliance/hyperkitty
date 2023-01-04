# -*- coding: utf-8 -*-
# Copyright (C) 2020-2023 by the Free Software Foundation, Inc.
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
# Author: Stasiek Michalski <stasiek@michalski.cc>
#
import re

from django.conf import settings
from django.contrib.syndication.views import Feed
from django.shortcuts import get_object_or_404
from django.urls import reverse

from hyperkitty.models import Email, MailingList


def chr2entity(mo):
    return '&#' + str(ord(mo.group(0))) + ';'


def sanitize(x):
    if isinstance(x, str):
        return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\xa0]',
                      chr2entity, x)
    else:
        return x


class MailingListFeed(Feed):

    def get_object(self, request, mlist_fqdn):
        return get_object_or_404(MailingList, name=mlist_fqdn)

    def title(self, obj):
        return sanitize(obj.display_name)

    def link(self, obj):
        return reverse("hk_list_overview", kwargs={"mlist_fqdn": obj.name})

    def description(self, obj):
        return sanitize(obj.description)

    def items(self, obj):
        len = getattr(settings, 'HYPERKITTY_MLIST_FEED_LENGTH', 30)
        return Email.objects.filter(mailinglist=obj).order_by('-date')[:len]

    def item_title(self, item):
        return sanitize(item.subject)

    def item_link(self, item):
        return reverse("hk_message_index",
                       kwargs={"mlist_fqdn": item.mailinglist.name,
                               "message_id_hash": item.message_id_hash})

    def item_description(self, item):
        return sanitize(item.content.replace("@", "\uff20"))

    def item_author_name(self, item):
        return sanitize(item.sender.name)

    def item_author_email(self, item):
        return sanitize(item.sender.address.replace("@", "\uff20"))

    def item_author_link(self, item):
        return reverse("hk_public_user_profile",
                       kwargs={"user_id": item.sender.mailman_id})

    def item_pubdate(self, item):
        return sanitize(item.date)
