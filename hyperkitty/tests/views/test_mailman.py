# -*- coding: utf-8 -*-
#
# Copyright (C) 2016-2023 by the Free Software Foundation, Inc.
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
from email.message import EmailMessage
from io import BytesIO
from unittest.mock import patch

from django.conf import settings
from django.contrib.sites.models import Site

from django_mailman3.models import MailDomain

from hyperkitty.models.email import Email
from hyperkitty.tests.utils import TestCase
from hyperkitty.utils import reverse
from hyperkitty.views.mailman import _get_url


class PrivateListTestCase(TestCase):

    def test_get_url_no_msgid(self):
        self.assertEqual(
            _get_url("test@example.com"),
            "https://example.com" +
            reverse('hk_list_overview', args=["test@example.com"]))

    def test_get_url_default_domain(self):
        self.assertEqual(
            _get_url("test@example.com", "<message-id>"),
            "https://example.com" + reverse('hk_message_index', kwargs={
                "mlist_fqdn": "test@example.com",
                "message_id_hash": "3F32NJAOW2XVHJWKZ73T2EPICEIAB3LI"
            }))

    def test_get_url_with_domain(self):
        site = Site.objects.create(name="Example", domain="lists.example.org")
        MailDomain.objects.create(site=site, mail_domain="example.com")
        self.assertEqual(
            _get_url("test@example.com", "<message-id>"),
            "https://lists.example.org" + reverse('hk_message_index', kwargs={
                "mlist_fqdn": "test@example.com",
                "message_id_hash": "3F32NJAOW2XVHJWKZ73T2EPICEIAB3LI"
            }))


class ArchiveTestCase(TestCase):

    def setUp(self):
        msg = EmailMessage()
        msg["From"] = "dummy@example.com"
        msg["Subject"] = "Fake Subject"
        msg["Message-ID"] = "<dummy>"
        msg["Date"] = "Fri, 02 Nov 2012 16:07:54"
        msg.set_payload("Fake Message")
        self.message = BytesIO(msg.as_string().encode("utf-8"))
        # Pass archiver key using Authorization HTTP header
        self.auth = {
            'HTTP_AUTHORIZATION': f'Token {settings.MAILMAN_ARCHIVER_KEY}'}
        self.url = reverse('hk_mailman_archive')

    def test_basic(self):
        response = self.client.post(
            self.url,
            data={
                "mlist": "list@example.com",
                "name": "email.txt",
                "message": self.message,
            },
            **self.auth,
        )
        self.assertEqual(response.status_code, 200, response.content.decode())
        result = json.loads(response.content.decode(response.charset))
        self.assertEqual(result, {
            "url": "https://example.com/list/list@example.com/message/"
                   "QKODQBCADMDSP5YPOPKECXQWEQAMXZL3/"
        })
        self.assertEqual(Email.objects.filter(message_id="dummy").count(), 1)

    def test_data_error(self):
        with patch("hyperkitty.views.mailman.add_to_list") as atl:
            atl.side_effect = ValueError("test error")
            response = self.client.post(
                self.url,
                data={
                    "mlist": "list@example.com",
                    "name": "email.txt",
                    "message": self.message,
                },
                **self.auth
            )
        self.assertEqual(response.status_code, 400, response.content.decode())
        result = json.loads(response.content.decode(response.charset))
        self.assertEqual(result, {
            "error": "test error",
        })

    def test_missing_auth(self):
        response = self.client.post(
            self.url,
            data={
                'mlist': 'list@example.com',
                'name': 'email.txt',
                'message': self.message,
            },
        )
        self.assertContains(
            response,
            'The archiver key must be',
            status_code=401,
            )

    def test_wrong_auth(self):
        response = self.client.post(
            self.url,
            data={
                'mlist': 'list@example.com',
                'name': 'email.txt',
                'message': self.message,
            },
            HTTP_AUTHORIZATION='Token IncorrectArchiverKey'
        )
        self.assertContains(
            response,
            'the MAILMAN_ARCHIVER_KEY is provided by you and it is correct',
            status_code=401,
            )

    def test_old_auth(self):
        """Sending key as a GET param tells you to upgrade
        mailman-hyperkitty"""
        response = self.client.post(
            self.url + '?key=foo',
            data={
                'mlist': 'list@example.com',
                'name': 'email.txt',
                'message': self.message,
            },
        )
        self.assertContains(
            response,
            'You need to upgrade the mailman-hyperkitty package',
            status_code=401,
            )
