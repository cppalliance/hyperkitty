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

import datetime
import json
import zlib

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction
from django.http import (
    Http404, HttpResponse, HttpResponseBadRequest, StreamingHttpResponse)
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import formats, timezone
from django.utils.dateformat import format as date_format
from django.utils.translation import gettext as _
from django.views.decorators.cache import cache_page

from django_mailman3.lib.mailman import get_mailman_user_id
from django_mailman3.lib.paginator import paginate

from hyperkitty.lib.view_helpers import (
    check_mlist_private, daterange, get_display_dates, get_months)
from hyperkitty.models import Favorite, LastView
from hyperkitty.signals import silenced_email_pre_delete


@check_mlist_private
def archives(request, mlist_fqdn, year=None, month=None, day=None):
    """List of threads in MailingList.

    If year & month is None, we return *all* the threads and render a view with
    all the threads of a MailingList.
    """
    mlist = request.mlist

    if year is None and month is None:
        # If the year and month is None, we set the begin date to the date of
        # the first email and end date to be today.
        end_date = datetime.date.today()
        # Since we don't need any special filtering, just return *all* the
        # threads ordered by date_active.
        threads = (mlist
                   .threads
                   .order_by("-date_active")
                   .select_related('starting_email')
                   .select_related('starting_email__sender'))

        # Get the earliest email in the mailing list to get the begin_date for
        # the mailing list.
        try:
            begin_date = (mlist
                          .emails
                          .order_by('date')
                          .values_list('date', flat=True)[0])
        except IndexError:
            # If there aren't any emails for the list, we just put the current
            # date as the begin and end date both.
            begin_date = end_date

        # Set the month and year to be today's.
        year = end_date.year
        month = end_date.month
        # The list title for all the threads.
        list_title = ""
        no_results_text = _("for this MailingList")
    else:
        try:
            begin_date, end_date = get_display_dates(year, month, day)
        except ValueError:
            # Wrong date format, for example 9999/0/0
            raise Http404("Wrong date format")

        threads = mlist.get_threads_between(begin_date, end_date)

        if day is None:
            list_title = date_format(begin_date, "F Y")
            no_results_text = _("for this month")
        else:
            list_title = formats.date_format(begin_date)  # works with i18n
            no_results_text = _("for this day")

    # Export button
    export = {
        "url": "%s?start=%s&end=%s" % (
            reverse("hk_list_export_mbox", kwargs={
                    "mlist_fqdn": mlist.name,
                    "filename": "%s-%s" % (
                        mlist.name, end_date.strftime("%Y-%m"))}),
            begin_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d")),
        "message": _("Download"),
        "title": _("This month in gzipped mbox format"),
    }
    extra_context = {
        'month': begin_date,
        'month_num': begin_date.month,
        "list_title": list_title.capitalize(),
        "no_results_text": no_results_text,
        "export": export,
    }
    if day is None:
        extra_context["participants_count"] = \
            mlist.get_participants_count_for_month(int(year), int(month))
    return _thread_list(request, mlist, threads, extra_context=extra_context)


def _thread_list(request, mlist, threads,
                 template_name='hyperkitty/thread_list.html',
                 extra_context=None):
    threads = paginate(threads,
                       request.GET.get('page'),
                       request.GET.get('count'))

    # We need to set favorites only if the user is logged in.
    if request.user.is_authenticated:
        # First, make a list of all the threads.
        thread_ids = [thread.id for thread in threads]
        # Then, get all the rows in the favs table which correspond to the
        # current user but the thread ids is from the above list. This will
        # get us which of the above threads are favorited, on which we should
        # set the favorite to be true.
        favs = (Favorite
                .objects
                .filter(thread_id__in=thread_ids, user=request.user)
                .values_list('thread_id', flat=True))

        # Do the same dance for un-read thing of the user.

        # This is a re-implementation of Thread.is_unread_by method that gets
        # multiple values in a single query and does the actual computation in
        # memory for unread count.
        last_views = (LastView
                      .objects
                      .filter(thread_id__in=thread_ids, user=request.user)
                      .values_list('id', 'thread_id', 'view_date'))

        # If there are more than one entry for single thread, delete the older
        # one and keep only the new one.
        lvs = {}
        for view_id, thread_id, view_date in last_views:
            # If we've seen this thread_id, i.e. this user has duplicate
            # LastView entries for this thread, so just delete the older one.
            if thread_id in lvs:
                if lvs[thread_id][1] > view_date:
                    del_id = view_id
                    lvs[thread_id] = (view_id, view_date)
                else:
                    # The one in lvs is the older one, so we'll delete that.
                    del_id = lvs[thread_id][0]
                LastView.objects.get(pk=del_id).delete()
            else:
                lvs[thread_id] = (view_id, view_date)

        for thread in threads:
            # Set if the user favorited this thread.
            thread.favorite = thread.id in favs
            # Sef if the user read this thread based on LastViews.
            if thread.id not in lvs:
                thread.is_unread = True
            else:
                thread.is_unread = (
                    thread.date_active.replace(tzinfo=timezone.utc) > lvs.get(thread.id)[1])  # noqa: E501

    context = {
        'mlist': mlist,
        'threads': threads,
        'months_list': get_months(mlist),
    }
    if extra_context is not None:
        context.update(extra_context)
    return render(request, template_name, context)


@check_mlist_private
def overview(request, mlist_fqdn=None):
    if not mlist_fqdn:
        return redirect('/')
    mlist = request.mlist

    # top authors are the ones that have the most kudos.  How do we determine
    # that?  Most likes for their post?
    authors = []

    # Threads by category
    threads_by_category = {}

    # Export button
    recent_dates = [
        d.strftime("%Y-%m-%d") for d in mlist.get_recent_dates()]
    recent_url = "%s?start=%s&end=%s" % (
        reverse("hk_list_export_mbox", kwargs={
                "mlist_fqdn": mlist.name,
                "filename": "%s-%s-%s" % (
                    mlist.name, recent_dates[0], recent_dates[1])}),
        recent_dates[0], recent_dates[1])
    today = datetime.date.today()
    month_dates = get_display_dates(today.year, today.month, None)
    month_url = "%s?start=%s&end=%s" % (
        reverse("hk_list_export_mbox", kwargs={
                "mlist_fqdn": mlist.name,
                "filename": "%s-%s" % (mlist.name, today.strftime("%Y-%m"))}),
        month_dates[0].strftime("%Y-%m-%d"),
        month_dates[1].strftime("%Y-%m-%d"))
    export = {"recent": recent_url, "month": month_url}

    context = {
        'view_name': 'overview',
        'mlist': mlist,
        'top_author': authors,
        'threads_by_category': threads_by_category,
        'months_list': get_months(mlist),
        'export': export,
        'posting_enabled': getattr(
            settings, 'HYPERKITTY_ALLOW_WEB_POSTING', True),
    }
    return render(request, "hyperkitty/overview.html", context)


@check_mlist_private
# @cache_page(3600 * 12)  # cache for 12 hours
def overview_recent_threads(request, mlist_fqdn):
    """Return the most recently updated threads."""
    mlist = request.mlist
    return render(request, "hyperkitty/fragments/overview_threads.html", {
        'mlist': mlist,
        'threads': mlist.recent_threads[:20],
        'empty': _('No discussions this month (yet).'),
        })


@check_mlist_private
# @cache_page(3600 * 12)  # cache for 12 hours
def overview_pop_threads(request, mlist_fqdn):
    """Return the threads with the most votes."""
    mlist = request.mlist
    return render(request, "hyperkitty/fragments/overview_threads.html", {
        'mlist': mlist,
        'threads': mlist.popular_threads,
        "empty": _('No vote has been cast this month (yet).'),
        })


@check_mlist_private
# @cache_page(3600 * 12)  # cache for 12 hours
def overview_top_threads(request, mlist_fqdn):
    """Return the threads with the most answers."""
    mlist = request.mlist
    return render(request, "hyperkitty/fragments/overview_threads.html", {
        'mlist': mlist,
        'threads': mlist.top_threads,
        "empty": _('No discussions this month (yet).'),
        })


@check_mlist_private
# @cache_page(3600 * 12)  # cache for 12 hours
def overview_favorites(request, mlist_fqdn):
    """Return the threads that the logged-in user has set as favorite."""
    mlist = request.mlist
    if request.user.is_authenticated:
        favorites = [f.thread for f in Favorite.objects.filter(
            thread__mailinglist=mlist, user=request.user)]
    else:
        favorites = []
    return render(request, "hyperkitty/fragments/overview_threads.html", {
        'mlist': mlist,
        'threads': favorites,
        "empty": _('You have not flagged any discussions (yet).'),
        })


@check_mlist_private
# @cache_page(3600 * 12)  # cache for 12 hours
def overview_posted_to(request, mlist_fqdn):
    """Return the threads that the logged-in user has posted to."""
    mlist = request.mlist
    if request.user.is_authenticated:
        mm_user_id = get_mailman_user_id(request.user)
        threads_posted_to = []
        if mm_user_id is not None:
            for thread in mlist.recent_threads:
                senders = set(
                    [e.sender.mailman_id for e in thread.emails.all()])
                if mm_user_id in senders:
                    threads_posted_to.append(thread)
    else:
        threads_posted_to = []
    return render(request, "hyperkitty/fragments/overview_threads.html", {
        'mlist': mlist,
        'threads': threads_posted_to,
        "empty": _('You have not posted to this list (yet).'),
        })


@check_mlist_private
# @cache_page(3600 * 12)  # cache for 12 hours
def overview_top_posters(request, mlist_fqdn):
    """Return the authors that sent the most emails."""
    mlist = request.mlist
    return render(request, "hyperkitty/fragments/overview_top_posters.html", {
        'mlist': mlist,
        })


@check_mlist_private
@cache_page(3600 * 12)  # cache for 12 hours
def recent_activity(request, mlist_fqdn):
    """Return the number of emails posted in the last 30 days"""
    mlist = request.mlist
    begin_date, end_date = mlist.get_recent_dates()
    days = daterange(begin_date, end_date)

    # Use get_messages and not get_threads to count the emails, because
    # recently active threads include messages from before the start date
    emails_in_month = mlist.emails.filter(
        date__gte=begin_date,
        date__lt=end_date)
    # graph
    emails_per_date = {}
    # populate with all days before adding data.
    for day in days:
        emails_per_date[day.strftime("%Y-%m-%d")] = 0
    # now count the emails
    for email in emails_in_month:
        date_str = email.date.strftime("%Y-%m-%d")
        if date_str not in emails_per_date:
            continue  # outside the range
        emails_per_date[date_str] += 1
    # return the proper format for the javascript chart function
    evolution = [{"date": d, "count": emails_per_date[d]}
                 for d in sorted(emails_per_date)]
    return HttpResponse(json.dumps({"evolution": evolution}),
                        content_type='application/javascript')


@check_mlist_private
def export_mbox(request, mlist_fqdn, filename):
    # If the settings HYPERKITTY_MBOX_EXPORT is set to False, then
    # disable download of archives.
    if not getattr(settings, "HYPERKITTY_MBOX_EXPORT", True):
        return HttpResponseBadRequest("Archive download disabled.")

    mlist = request.mlist
    query = mlist.emails
    try:
        if "start" in request.GET:
            start_date = datetime.datetime.strptime(
                request.GET["start"], "%Y-%m-%d")
            start_date = timezone.make_aware(start_date, timezone.utc)
            query = query.filter(date__gte=start_date)
        if "end" in request.GET:
            end_date = datetime.datetime.strptime(
                request.GET["end"], "%Y-%m-%d")
            end_date = timezone.make_aware(end_date, timezone.utc)
            query = query.filter(date__lt=end_date)
    except ValueError:
        return HttpResponseBadRequest("Invalid dates")
    if "thread" in request.GET:
        query = query.filter(thread__thread_id=request.GET["thread"])
    if "message" in request.GET:
        query = query.filter(message_id_hash=request.GET["message"])

    def stream_mbox(query):
        # Use the gzip format: http://www.zlib.net/manual.html#Advanced
        compressor = zlib.compressobj(6, zlib.DEFLATED, zlib.MAX_WBITS | 16)
        for email in query.order_by("archived_date").all():
            yield compressor.compress(email.as_bytes())
            yield compressor.compress(b"\n\n")
        yield compressor.flush()
    response = StreamingHttpResponse(
        stream_mbox(query), content_type="application/gzip")
    response['Content-Disposition'] = (
        'attachment; filename="%s.mbox.gz"' % filename)
    return response


@login_required
@check_mlist_private
@transaction.atomic
def delete(request, mlist_fqdn):
    mlist = request.mlist
    if not request.user.is_staff and not request.user.is_superuser:
        return HttpResponse(
            _('You must be a staff member to delete a MailingList'),
            content_type="text/plain", status=403)
    if request.method == 'POST':
        # XXX(maxking): This is a hack to make sure that we don't continuously
        # keep re-setting the parent of emails when trying to delete all the
        # emails and threads.
        # We silence the pre_delete hook for email which does this re-balancing
        # and then continue to do the delete action.
        with silenced_email_pre_delete():
            try:
                mlist.threads.all().delete()
                mlist.delete()
                messages.success(
                    request,
                    _('Successfully deleted {}'.format(mlist.name)))
                return redirect('/')
            except (IntegrityError, ObjectDoesNotExist) as e:
                messages.error(request, str(e))

            return redirect(
                reverse('hk_list_overview', kwargs={"mlist_fqdn": mlist.name}))
    else:
        return render(request, "hyperkitty/list_delete.html", {"mlist": mlist})
