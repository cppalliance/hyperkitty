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

import hmac
import json
import logging
from email import message_from_binary_file
from email.message import EmailMessage
from email.policy import default
from functools import wraps
from urllib.parse import unquote, urljoin

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, SuspiciousOperation
from django.http import HttpResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from django_mailman3.models import MailDomain

from hyperkitty.lib.incoming import DuplicateMessage, add_to_list
from hyperkitty.lib.utils import get_message_id_hash


logger = logging.getLogger(__name__)


def key_and_ip_auth(func):
    @wraps(func)
    def _decorator(request, *args, **kwargs):
        for attr in ('MAILMAN_ARCHIVER_KEY', 'MAILMAN_ARCHIVER_FROM'):
            if not hasattr(settings, attr):
                msg = "Missing setting: %s" % attr
                logger.error(msg)
                raise ImproperlyConfigured(msg)
        # '*' matches any host
        if '*' in settings.MAILMAN_ARCHIVER_FROM:
            logger.debug(
                "Found '*' into MAILMAN_ARCHIVER_FROM. IP check disabled "
                "for archiving API endpoint. Accepting client IP "
                "{}.".format(request.META["REMOTE_ADDR"]))
        elif (request.META.get("REMOTE_ADDR") not in
                settings.MAILMAN_ARCHIVER_FROM):
            logger.error(
                "Access to the archiving API endpoint was forbidden from "
                "IP {}, your MAILMAN_ARCHIVER_FROM setting may be "
                "misconfigured".format(request.META["REMOTE_ADDR"]))
            return HttpResponse(
                """<html><title>Forbidden</title><body>
                <h1>Access is forbidden</h1><p>Please check the IP addresses
                 assigned to MAILMAN_ARCHIVER_FROM in the settings file.
                </p></body></html>""",
                content_type="text/html", status=403)

        authorization = request.headers.get('Authorization')
        if authorization is None:
            if request.GET.get('key') is not None:
                # Old authentication method used, need to upgrade
                # mailman-hyperkitty
                logger.error(
                    'The MAILMAN_ARCHIVER_KEY is now required to be '
                    'sent over the Authorization HTTP header, you need to '
                    'upgrade the mailman-hyperkitty package to 1.2.0 or newer.'
                )
                return HttpResponse(
                    """<html><title>Auth required</title><body>
                    <h1>Authorization Required</h1><p>The archiver key is now
                     required to be sent over the Authorization HTTP header.
                     You need to upgrade the mailman-hyperkitty package to
                     1.2.0 or newer.
                    </p></body></html>""",
                    content_type="text/html", status=401)
            else:
                # No auth provided over header nor GET param
                logger.error(
                    'The MAILMAN_ARCHIVER_KEY was not sent as the '
                    'Authorization HTTP header.'
                )
                return HttpResponse(
                    """<html><title>Auth required</title><body>
                    <h1>Authorization Required</h1><p>The archiver key must be
                     sent over the Authorization HTTP header.
                    </p></body></html>""",
                    content_type="text/html", status=401)

        auth = authorization.split()
        # Use timing-attack safe comparison of secret key
        if (len(auth) != 2 or auth[0] != 'Token' or
                not hmac.compare_digest(
                    auth[1], settings.MAILMAN_ARCHIVER_KEY)):
            return HttpResponse(
                """<html><title>Auth required</title><body>
                <h1>Authorization Required</h1><p>Please check whether
                 the MAILMAN_ARCHIVER_KEY is provided by you and it is correct.
                </p></body></html>""",
                content_type="text/html", status=401)
        return func(request, *args, **kwargs)
    return _decorator


def _get_url(mlist_fqdn, msg_id=None):
    # We can't use HttpRequest.build_absolute_uri() because the mailman API may
    # be accessed via localhost.
    # https://docs.djangoproject.com/en/dev/ref/request-response/#django.http.HttpRequest.build_absolute_uri
    # https://docs.djangoproject.com/en/dev/ref/contrib/sites/#getting-the-current-domain-for-full-urls
    # result = urljoin(public_url, urlunquote(
    #                  reverse('hk_list_overview', args=[mlist_fqdn])))
    # We use the MailDomain association from django_mailman3 to find out the
    # proper domain.
    if msg_id is None:
        url = reverse('hk_list_overview', args=[mlist_fqdn])
    else:
        msg_hash = get_message_id_hash(msg_id.strip().strip("<>"))
        url = reverse('hk_message_index', kwargs={
            "mlist_fqdn": mlist_fqdn, "message_id_hash": msg_hash})
    relative_url = unquote(url)
    mail_domain = mlist_fqdn.split("@")[1]
    try:
        domain = MailDomain.objects.get(
            mail_domain=mail_domain).site.domain
    except MailDomain.DoesNotExist:
        domain = mail_domain
    return urljoin("https://%s" % domain, relative_url)


@key_and_ip_auth
def urls(request):
    result = _get_url(request.GET["mlist"], request.GET.get("msgid"))
    return HttpResponse(json.dumps({"url": result}),
                        content_type='application/javascript')


@require_POST
@key_and_ip_auth
@csrf_exempt
def archive(request):
    mlist_fqdn = request.POST["mlist"]
    if "message" not in request.FILES:
        raise SuspiciousOperation
    msg = message_from_binary_file(
        request.FILES['message'], _class=EmailMessage, policy=default)
    try:
        add_to_list(mlist_fqdn, msg)
    except DuplicateMessage as e:
        logger.info("Duplicate email with message-id '%s'", e.args[0])
    except ValueError as e:
        logger.warning("Could not archive the email with message-id '%s': %s",
                       msg.get("Message-Id", None), e)
        return HttpResponse(json.dumps({"error": str(e)}), status=400,
                            content_type='application/javascript')
    url = _get_url(mlist_fqdn, msg['Message-Id'])
    logger.info("Archived message %s to %s", msg['Message-Id'], url)
    return HttpResponse(json.dumps({"url": url}),
                        content_type='application/javascript')
