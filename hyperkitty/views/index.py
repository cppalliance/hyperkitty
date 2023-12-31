# -*- coding: utf-8 -*-
#
# Copyright (C) 2014-2023 by the Free Software Foundation, Inc.
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

import json
import re

from django.conf import settings
from django.db.models import Q
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render

from django_mailman3.lib.mailman import get_subscriptions
from django_mailman3.lib.paginator import paginate
from django_mailman3.models import MailDomain

from hyperkitty.models import ArchivePolicy, MailingList


class SortMode:
    """All the Sort modes the Index page supports."""
    CREATION = "creation"
    POPULAR = "popular"
    NAME = "name"
    ACTIVE = "active"

    DEFAULT = POPULAR

    @classmethod
    def all(self):
        """Return all the Sort modes."""
        return (self.NAME, self.ACTIVE, self.POPULAR, self.CREATION)


def index(request):
    mlists = MailingList.objects.all()
    sort_mode = request.GET.get("sort", SortMode.DEFAULT)

    if sort_mode not in SortMode.all():
        return HttpResponseBadRequest("Wrong sort mode parameter")

    # Domain filtering
    if getattr(settings, 'FILTER_VHOST', False):
        our_lists = MailingList.objects.none()
        domain = request.get_host().split(":")[0]
        mail_hosts = []
        for mlist in mlists:
            mail_host = re.sub('^.*@', '', mlist.name)
            try:
                if (MailDomain.objects.get(
                        mail_domain=mail_host).site.domain == domain):
                    if mail_host not in mail_hosts:
                        mail_hosts.append(mail_host)
            except MailDomain.DoesNotExist:
                pass
        if len(mail_hosts) == 0:
            mail_hosts = [domain]
        for domain in mail_hosts:
            domain = '@%s' % domain
            our_lists = our_lists | mlists.filter(name__iendswith=domain)
        mlists = our_lists

    # Name filtering
    name_filter = request.GET.get('name')
    if name_filter:
        sort_mode = SortMode.NAME
        mlists = mlists.filter(
            Q(name__icontains=name_filter) |
            Q(display_name__icontains=name_filter)
            )
        if mlists.count() == 1:
            return redirect(
                'hk_list_overview', mlist_fqdn=mlists.first().name)

    # Access Filtering
    if request.user.is_superuser:
        # Superusers see everything
        pass
    elif request.user.is_authenticated:
        # For authenticated users show only their subscriptions
        # and public lists
        mlists = mlists.filter(
            Q(list_id__in=get_subscriptions(request.user)) |
            Q(archive_policy=ArchivePolicy.public.value)
        )
    else:
        # Unauthenticated users only see public lists
        mlists = mlists.filter(
            archive_policy=ArchivePolicy.public.value)

    # Sorting
    if sort_mode == SortMode.NAME:
        mlists = mlists.order_by(SortMode.NAME)
    elif sort_mode == SortMode.ACTIVE:
        mlists = list(mlists)
        mlists.sort(key=lambda lk: lk.recent_threads_count, reverse=True)
    elif sort_mode == SortMode.POPULAR:
        mlists = list(mlists)
        mlists.sort(key=lambda lk: lk.recent_participants_count, reverse=True)
    elif sort_mode == SortMode.CREATION:
        mlists = mlists.order_by("-created_at")

    # Inactive List Setting
    show_inactive = getattr(settings, 'SHOW_INACTIVE_LISTS_DEFAULT', False)

    mlists = paginate(mlists, request.GET.get('page'),
                      request.GET.get('count'))

    context = {
        'view_name': 'all_lists',
        'all_lists': mlists,
        'sort_mode': sort_mode,
        'show_inactive': show_inactive
    }
    return render(request, "hyperkitty/index.html", context)


def find_list(request):
    """Get a list of mailing list matching the query parameter 'term'.

    This serves the API that the list search uses, powered by jquery's
    autocomplete.

    The default returned content_type is `application/javascript`.
    """
    term = request.GET.get('term')
    result = []
    if term:
        query = MailingList.objects.filter(
            Q(name__icontains=term) | Q(display_name__icontains=term)
            )
        if not request.user.is_superuser:
            query = query.filter(
                archive_policy=ArchivePolicy.public.value)
        query = query.order_by("name").values("name", "display_name")
        for line in query[:20]:
            result.append({
                "value": line["name"],
                "label": line["display_name"] or line["name"],
            })
    return HttpResponse(
        json.dumps(result), content_type='application/javascript')
