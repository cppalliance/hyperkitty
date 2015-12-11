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
# Author: Aurelien Bompard <abompard@fedoraproject.org>
#

from __future__ import absolute_import, print_function, unicode_literals

import os
import logging
import shutil
import tempfile
from unittest import SkipTest

import haystack
import mailmanclient
from mock import Mock, patch
from django import VERSION as DJANGO_VERSION
from django.test import RequestFactory, TestCase as DjangoTestCase
from django.conf import settings
from django.contrib.messages.storage.cookie import CookieStorage
from django.core.management import call_command
#from django.core.cache import get_cache

from hyperkitty.lib.cache import cache


def setup_logging(tmpdir):
    formatter = logging.Formatter(fmt="%(message)s")
    levels = ["debug", "info", "warning", "error"]
    handlers = []
    for level_name in levels:
        log_path = os.path.join(tmpdir, "%s.log" % level_name)
        handler = logging.FileHandler(log_path)
        handler.setLevel(getattr(logging, level_name.upper()))
        handler.setFormatter(formatter)
        handlers.append(handler)
    for logger_name in ["django", "hyperkitty"]:
        logger = logging.getLogger(logger_name)
        logger.propagate = False
        logger.setLevel(logging.DEBUG)
        del logger.handlers[:]
        for handler in handlers:
            logger.addHandler(handler)


class TestCase(DjangoTestCase):
    # pylint: disable=attribute-defined-outside-init

    # Testcase classes can use this variable to add more overrides:
    override_settings = {}


    def _pre_setup(self):
        super(TestCase, self)._pre_setup()
        self.tmpdir = tempfile.mkdtemp(prefix="hyperkitty-testing-")
        # Logging
        setup_logging(self.tmpdir)
        # Override settings
        self._old_settings = {}
        self._override_setting("STATIC_ROOT",
            os.path.join(self.tmpdir, "static"))
        override_settings = self.override_settings.copy()
        for key, value in override_settings.items():
            self._override_setting(key, value)
        #if DJANGO_VERSION[:2] < (1, 7):
        #    cache.backend = get_cache("default") # in 1.7 it's a proxy
        #else:
        #    from django.core.cache import caches
        #    #print("~"*40, caches.all())
        self.mailman_client = Mock()
        self.mailman_client.get_user.side_effect = mailmanclient.MailmanConnectionError()
        self.mailman_client.get_list.side_effect = mailmanclient.MailmanConnectionError()
        self._mm_client_patcher = patch("hyperkitty.lib.mailman.MailmanClient",
                                        lambda *a: self.mailman_client)
        self._mm_client_patcher.start()

    def _override_setting(self, key, value):
        self._old_settings[key] = getattr(settings, key, None)
        setattr(settings, key, value)

    def _post_teardown(self):
        self._mm_client_patcher.stop()
        cache.clear()
        for key, value in self._old_settings.items():
            if value is None:
                delattr(settings, key)
            else:
                setattr(settings, key, value)
        shutil.rmtree(self.tmpdir)
        super(TestCase, self)._post_teardown()


class SearchEnabledTestCase(TestCase):
    # pylint: disable=attribute-defined-outside-init

    def _pre_setup(self):
        try:
            import whoosh # pylint: disable=unused-variable
        except ImportError:
            raise SkipTest("The Whoosh library is not available")
        super(SearchEnabledTestCase, self)._pre_setup()
        if DJANGO_VERSION < (1, 7):
            haystack.connections.reload("default")
        call_command('rebuild_index', interactive=False, verbosity=0)

    def _post_teardown(self):
        super(SearchEnabledTestCase, self)._post_teardown()




def get_test_file(*fileparts):
    return os.path.join(os.path.dirname(__file__), "testdata", *fileparts)
get_test_file.__test__ = False


def get_flash_messages(response):
    if "messages" not in response.cookies:
        return []
    dummy_request = RequestFactory().get("/")
    dummy_request.COOKIES["messages"] = response.cookies["messages"].value
    return list(CookieStorage(dummy_request))
get_flash_messages.__test__ = False
