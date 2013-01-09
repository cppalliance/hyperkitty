# -*- coding: utf-8 -*-
# Copyright (C) 1998-2012 by the Free Software Foundation, Inc.
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
# Author: Aamir Khan <syst3m.w0rm@gmail.com>
# Author: Aurelien Bompard <abompard@fedoraproject.org>
#

import datetime

import django.utils.simplejson as simplejson

from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.template import RequestContext, loader
from django.conf import settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger, InvalidPage
from django.core.urlresolvers import reverse
from django.utils.datastructures import SortedDict
from django.contrib.auth.decorators import (login_required,
                                            permission_required,
                                            user_passes_test)

from hyperkitty.models import Rating, Tag
#from hyperkitty.lib.mockup import *
from forms import *
from hyperkitty.lib import get_months, get_store, stripped_subject


def thread_index(request, mlist_fqdn, threadid):
    ''' Displays all the email for a given thread identifier '''
    search_form = SearchForm(auto_id=False)
    t = loader.get_template('thread.html')
    store = get_store(request)
    thread = store.get_thread(mlist_fqdn, threadid)
    if not thread:
        raise Http404
    prev_thread, next_thread = store.get_thread_neighbors(mlist_fqdn, threadid)

    if "sort" in request.GET and request.GET["sort"] == "date":
        sort_mode = "date"
        emails = thread.emails
    else:
        sort_mode = "thread"
        emails = thread.emails_by_reply

    participants = {}
    for email in emails:
        # Extract all the votes for this message
        try:
            votes = Rating.objects.filter(messageid=email.message_id)
        except Rating.DoesNotExist:
            votes = {}

        likes = 0
        dislikes = 0

        for vote in votes:
            if vote.vote == 1:
                likes = likes + 1
            elif vote.vote == -1:
                dislikes = dislikes + 1
            else:
                pass

        email.votes = votes
        email.likes = likes
        email.dislikes = dislikes
        email.likestatus = "neutral"
        if email.likes - email.dislikes >= 10:
            email.likestatus = "likealot"
        elif email.likes - email.dislikes > 0:
            email.likestatus = "like"
        #elif email.likes - email.dislikes < 0:
        #    email.likestatus = "dislike"


        # Statistics on how many participants and messages this month
        participants[email.sender_name] = email.sender_email

        if sort_mode == "thread":
            email.level = email.thread_depth - 1 # replies start ragged left
            if email.level > 5:
                email.level = 5

    archives_length = get_months(store, mlist_fqdn)
    from_url = reverse("thread", kwargs={"mlist_fqdn":mlist_fqdn,
                                         "threadid":threadid})
    tag_form = AddTagForm(initial={'from_url' : from_url})

    try:
        tags = Tag.objects.filter(threadid=threadid, list_address=mlist_fqdn)
    except Tag.DoesNotExist:
        tags = {}

    # Extract relative dates
    today = datetime.date.today()
    days_old = today - thread.starting_email.date.date()
    days_inactive = today - thread.last_email.date.date()

    mlist = store.get_list(mlist_fqdn)
    subject = stripped_subject(mlist, thread.starting_email.subject)

    c = RequestContext(request, {
        'mlist' : mlist,
        'threadid' : threadid,
        'subject': subject,
        'tags' : tags,
        'list_address': mlist_fqdn,
        'search_form': search_form,
        'addtag_form': tag_form,
        'month': 'Thread',
        'participants': participants,
        'first_mail': thread.starting_email,
        'replies': list(emails)[1:],
        'neighbors': (prev_thread, next_thread),
        'archives_length': archives_length,
        'days_inactive': days_inactive.days,
        'days_old': days_old.days,
        'use_mockups': settings.USE_MOCKUPS,
        'sort_mode': sort_mode,
    })
    return HttpResponse(t.render(c))


def add_tag(request, mlist_fqdn, hashid):
    """ Add a tag to a given thread. """
    if not request.user.is_authenticated():
        return HttpResponse('You must be logged in to add a tag',
                            content_type="text/plain", status=403)

    if request.method != 'POST':
        return HttpResponse("Something went wrong here",
                            content_type="text/plain", status=500)

    form = AddTagForm(request.POST)
    if not form.is_valid():
        return HttpResponse("Error adding tag: invalid data",
                            content_type="text/plain", status=500)
    tag = form.data['tag']
    try:
        tag_obj = Tag.objects.get(threadid=hashid,
                                  list_address=mlist_fqdn, tag=tag)
    except Tag.DoesNotExist:
        tag_obj = Tag(list_address=mlist_fqdn, threadid=hashid, tag=tag)
        tag_obj.save()

    # Now refresh the tag list
    tags = Tag.objects.filter(threadid=hashid, list_address=mlist_fqdn)
    t = loader.get_template('threads/tags.html')
    html = t.render(RequestContext(request, {
            "tags": tags,
            "list_address": mlist_fqdn}))

    response = {"tags": [ t.tag for t in tags ], "html": html}
    return HttpResponse(simplejson.dumps(response),
                        mimetype='application/javascript')

