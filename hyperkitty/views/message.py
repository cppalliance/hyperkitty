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
import logging
import urllib

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import SuspiciousOperation
from django.db import DatabaseError
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template import loader
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views import defaults as default_views
from django.views.decorators.http import require_POST

from hyperkitty.forms import MessageDeleteForm, PostForm, ReplyForm
from hyperkitty.lib.mailman import (
    AddressBannedFromList, ModeratedListException)
from hyperkitty.lib.posting import PostingFailed, post_to_list, reply_subject
from hyperkitty.lib.view_helpers import (
    check_mlist_private, get_months, get_posting_form)
from hyperkitty.models.email import Attachment, Email
from hyperkitty.models.thread import Thread


logger = logging.getLogger(__name__)


@check_mlist_private
def index(request, mlist_fqdn, message_id_hash):
    '''
    Displays a single message identified by its message_id_hash (derived from
    message_id)
    '''
    mlist = request.mlist
    message = get_object_or_404(
        Email, mailinglist=mlist, message_id_hash=message_id_hash)
    if request.user.is_authenticated:
        message.myvote = message.votes.filter(user=request.user).first()
    else:
        message.myvote = None

    # Export button
    export = {
        "url": "%s?message=%s" % (
            reverse("hk_list_export_mbox", kwargs={
                "mlist_fqdn": mlist.name,
                "filename": "%s-%s" % (mlist.name, message.message_id_hash)
                }),
            message.message_id_hash),
        "message": _("Download"),
        "title": _("This message in gzipped mbox format"),
    }

    context = {
        'mlist': mlist,
        'message': message,
        'message_id_hash': message_id_hash,
        'months_list': get_months(mlist),
        'month': message.date,
        'reply_form': get_posting_form(ReplyForm, request, mlist),
        'export': export,
        'posting_enabled': getattr(
            settings, 'HYPERKITTY_ALLOW_WEB_POSTING', True),
        'user_is_owner': mlist.is_owner(request.user),
    }
    return render(request, "hyperkitty/message.html", context)


@check_mlist_private
def attachment(request, mlist_fqdn, message_id_hash, counter, filename):
    """
    Sends the numbered attachment for download. The filename is not used for
    lookup, but validated nonetheless for security reasons.
    """
    mlist = request.mlist
    message = get_object_or_404(
        Email, mailinglist=mlist, message_id_hash=message_id_hash)
    att = get_object_or_404(
        Attachment, email=message, counter=int(counter))
    if att.name != filename:
        raise Http404
    # http://djangosnippets.org/snippets/1710/
    response = HttpResponse(att.get_content())
    response['Content-Type'] = att.content_type
    response['Content-Length'] = att.size
    if att.encoding is not None:
        response['Content-Encoding'] = att.encoding
    # Follow RFC2231, browser support is sufficient nowadays (2012-09)
    response['Content-Disposition'] = 'attachment; filename*=UTF-8\'\'%s' \
        % urllib.parse.quote(att.name.encode('utf-8'))
    return response


@require_POST
@check_mlist_private
def vote(request, mlist_fqdn, message_id_hash):
    """ Vote for or against a given message identified by messageid. """
    if not request.user.is_authenticated:
        return HttpResponse('You must be logged in to vote',
                            content_type="text/plain", status=403)
    mlist = request.mlist
    message = get_object_or_404(
        Email, mailinglist=mlist, message_id_hash=message_id_hash)

    value = int(request.POST['vote'])
    message.vote(value, request.user)

    # Extract all the votes for this message to refresh it
    message.myvote = message.votes.filter(user=request.user).first()
    t = loader.get_template('hyperkitty/fragments/like_form.html')
    html = t.render({
        "mlist": mlist,
        "object": message,
        "message_id_hash": message_id_hash,
    }, request)

    votes = message.get_votes()
    result = {"like": votes["likes"], "dislike": votes["dislikes"],
              "html": html}
    return HttpResponse(json.dumps(result),
                        content_type='application/javascript')


@require_POST
@login_required
@check_mlist_private
def reply(request, mlist_fqdn, message_id_hash):
    """Sends a reply to the list."""
    if not getattr(settings, 'HYPERKITTY_ALLOW_WEB_POSTING', True):
        return HttpResponse('Posting via Hyperkitty is disabled',
                            content_type="text/plain", status=403)
    mlist = request.mlist
    form = get_posting_form(ReplyForm, request, mlist, request.POST)
    if not form.is_valid():
        return HttpResponse(form.errors.as_text(),
                            content_type="text/plain", status=400)
    if form.cleaned_data["newthread"]:
        subject = form.cleaned_data["subject"]
        headers = {}
    else:
        message = get_object_or_404(
            Email, mailinglist=mlist, message_id_hash=message_id_hash)
        subject = reply_subject(message.subject)
        headers = {"In-Reply-To": "<%s>" % message.message_id,
                   "References": "<%s>" % message.message_id, }
    if form.cleaned_data["sender"]:
        headers["From"] = form.cleaned_data["sender"]
    try:
        subscribed_now = post_to_list(
            request, mlist, subject, form.cleaned_data["message"], headers)
    except PostingFailed as e:
        return HttpResponse(str(e), content_type="text/plain", status=500)
    except ModeratedListException as e:
        return HttpResponse(str(e), content_type="text/plain", status=403)
    except AddressBannedFromList as e:
        return default_views.permission_denied(request, e)

    # TODO: if newthread, don't insert the temp mail in the thread, redirect to
    # the new thread. Should we insert the mail in the DB and flag it as
    # "temporary", to be confirmed by a later reception from mailman? This
    # looks complex, because the temp mail should only be visible by its
    # sender.

    if form.cleaned_data["newthread"]:
        html = None
    else:
        email_reply = {
            "sender_name": "%s %s" % (request.user.first_name,
                                      request.user.last_name),
            "sender_address": (form.cleaned_data["sender"]
                               or request.user.email),
            "content": form.cleaned_data["message"],
            # no need to increment, level = thread_depth - 1
            "level": message.thread_depth,
            "mailinglist": mlist,
        }
        t = loader.get_template('hyperkitty/ajax/temp_message.html')
        html = t.render({'email': email_reply}, request)
    # TODO: make the message below translatable.
    result = {"result": _("Your reply has been sent and is being processed."),
              "message_html": html}
    if subscribed_now:
        result['result'] += (
            _("\n  You have been subscribed to {} list.").format(mlist_fqdn))
    return HttpResponse(json.dumps(result),
                        content_type="application/javascript")


@login_required
@check_mlist_private
def new_message(request, mlist_fqdn):
    """Sends a new thread-starting message to the list. """
    if not getattr(settings, 'HYPERKITTY_ALLOW_WEB_POSTING', True):
        return HttpResponse('Posting via Hyperkitty is disabled',
                            content_type="text/plain", status=403)
    mlist = request.mlist
    if request.method == 'POST':
        form = get_posting_form(PostForm, request, mlist, request.POST)
        if form.is_valid():
            today = datetime.date.today()
            headers = {}
            if form.cleaned_data["sender"]:
                headers["From"] = form.cleaned_data["sender"]
            try:
                post_to_list(request, mlist, form.cleaned_data['subject'],
                             form.cleaned_data["message"], headers)
            except PostingFailed as e:
                messages.error(request, str(e))
                logger.info(
                    "Failed to send message from %s to list %s due to %s",
                    form.cleaned_data["sender"], mlist, str(e))
            except ModeratedListException as e:
                return HttpResponse(
                    str(e), content_type="text/plain", status=403)
            except AddressBannedFromList as e:
                return default_views.permission_denied(request, e)
            else:
                messages.success(
                    request, "The message has been sent successfully.")
                redirect_url = reverse('hk_archives_with_month', kwargs={
                    "mlist_fqdn": mlist_fqdn,
                    'year': today.year, 'month': today.month})
                return redirect(redirect_url)
    else:
        form = get_posting_form(PostForm, request, mlist)
    context = {
        "mlist": mlist,
        "post_form": form,
        'months_list': get_months(mlist),
    }
    return render(request, "hyperkitty/message_new.html", context)


@login_required
@check_mlist_private
def delete(request, mlist_fqdn, threadid=None, message_id_hash=None):
    """Delete messages. """
    mlist = request.mlist
    if not (request.user.is_staff or
            request.user.is_superuser or
            mlist.is_owner(request.user)):
        return HttpResponse(
            'You must be a staff member or list owner to delete a message',
            content_type="text/plain", status=403)

    if threadid is not None:
        thread = get_object_or_404(
            Thread, mailinglist=mlist, thread_id=threadid)
        message = None
    elif message_id_hash is not None:
        message = get_object_or_404(
            Email, mailinglist=mlist, message_id_hash=message_id_hash)
        thread = None
    else:
        raise SuspiciousOperation

    form_queryset = Email.objects.filter(mailinglist=mlist)
    if thread is not None:
        form_queryset = form_queryset.filter(thread=thread)
    elif message is not None:
        form_queryset = form_queryset.filter(pk=message.pk)

    if request.method == 'POST':
        form = MessageDeleteForm(request.POST)
        form.fields["email"].queryset = form_queryset
        if form.is_valid():
            thread_ids = []
            for email in sorted(form.cleaned_data["email"], reverse=True):
                email.refresh_from_db()
                thread_id = email.thread.pk
                try:
                    email.delete()
                except DatabaseError as e:
                    form.add_error(
                        "email",
                        _("Could not delete message %(msg_id_hash)s: "
                          "%(error)s")
                        % {"msg_id_hash": email.message_id_hash, "error": e})
                    continue
                logger.info("Deleted email %s (%s)",
                            email.pk, email.message_id)
                thread_ids.append(thread_id)
            if thread_ids:
                messages.success(
                    request, _("Successfully deleted %(count)s messages.")
                    % {"count": len(thread_ids)})
            if not form.has_error("email"):
                if len(set(thread_ids)) == 1:
                    try:
                        thread = Thread.objects.get(pk=thread_ids[0])
                        return redirect(reverse('hk_thread', kwargs={
                            "mlist_fqdn": mlist_fqdn,
                            "threadid": thread.thread_id}))
                    except Thread.DoesNotExist:
                        # The thread has been deleted to in cascade, go back to
                        # the list.
                        pass
                return redirect(reverse('hk_list_overview', kwargs={
                    "mlist_fqdn": mlist_fqdn}))
    else:
        initial = form_queryset.values_list("pk", flat=True)
        form = MessageDeleteForm(initial={"email": initial})
        form.fields["email"].queryset = form_queryset
    context = {
        "mlist": mlist,
        "form": form,
    }
    if thread is not None:
        context.update({
            "thread": thread,
            "form_action": reverse("hk_thread_delete", kwargs={
                "mlist_fqdn": mlist_fqdn, "threadid": thread.thread_id}),
            "cancel_url": reverse("hk_thread", kwargs={
                "mlist_fqdn": mlist_fqdn, "threadid": thread.thread_id}),
            })
    elif message is not None:
        context.update({
            "message": message,
            "form_action": reverse("hk_message_delete", kwargs={
                "mlist_fqdn": mlist_fqdn,
                "message_id_hash": message.message_id_hash}),
            "cancel_url": reverse("hk_message_index", kwargs={
                "mlist_fqdn": mlist_fqdn,
                "message_id_hash": message.message_id_hash}),
            })
    return render(request, "hyperkitty/message_delete.html", context)
