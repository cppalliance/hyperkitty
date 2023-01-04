# -*- coding: utf-8 -*-
#
# Copyright (C) 2021-2023 by the Free Software Foundation, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301,
# USA.

from email.message import EmailMessage
from unittest.mock import patch

from django.contrib.auth.models import User

from bs4 import BeautifulSoup

from hyperkitty.lib.incoming import add_to_list
from hyperkitty.models.mailinglist import ArchivePolicy, MailingList
from hyperkitty.tests.utils import TestCase
from hyperkitty.utils import reverse


class TestMailingListFeed(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            'testuser', 'test@example.com', 'testPass')
        self.user.is_superuser = True
        self.user.save()
        self.client.login(username='testuser', password='testPass')

    def test_feed(self):
        msg = EmailMessage()
        msg["From"] = "Dummy Sender <dummy@example.com>"
        msg["Subject"] = "First Subject"
        msg["Date"] = "Mon, 02 Feb 2015 13:00:00 +0300"
        msg["Message-ID"] = "<msg>"
        msg.set_payload("Dummy message")
        add_to_list("list@example.com", msg)
        url = reverse('hk_list_feed', args=('list@example.com', ))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content, "lxml")
        self.assertEqual(len(soup.find_all("title",
                                           string="First Subject")), 1)

    def test_control_chars(self):
        msg = EmailMessage()
        msg["From"] = "Dummy\x01 Sender <dummy@example.com>"
        msg["Subject"] = "First\x01 Subject"
        msg["Date"] = "Mon, 02 Feb 2015 13:00:00 +0300"
        msg["Message-ID"] = "<msg>"
        msg.set_payload("Dummy\x01 message")
        add_to_list("list@example.com", msg)
        url = reverse('hk_list_feed', args=('list@example.com', ))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content, "lxml")
        self.assertEqual(len(soup.find_all("title",
                                           string="First&#1; Subject")), 1)

    def test_private_feed_authentication(self):
        """Test the authentication checks for a private mailinglist's feed"""
        mlist = MailingList.objects.create(name='list@example.com')
        mlist.archive_policy = ArchivePolicy.private.value
        mlist.save()
        # Anonymous access to feeds should be disallowed.
        self.client.logout()
        self._check_response(403)
        # Access to a super user should be allowed.
        self.client.force_login(self.user)
        self._check_response(200)
        # Access to a regular signed-in user shouldn't be allowed for
        # private lists.
        regular_user = User.objects.create_user(
            'someuser', 'someuser@example.com', 'testpass')
        self.client.force_login(regular_user)
        self._check_response(403)
        # After subscribing, the user should be able to add access.
        with patch('hyperkitty.lib.view_helpers.get_subscriptions') as gs:
            gs.return_value = ['list.example.com']
            # Now, the user should ideally be subscribed and have acess to the
            # private list.
            self._check_response(200)

    def _check_response(self, expected_code):
        url = reverse('hk_list_feed', args=('list@example.com', ))
        response = self.client.get(url)
        self.assertEqual(response.status_code, expected_code)
