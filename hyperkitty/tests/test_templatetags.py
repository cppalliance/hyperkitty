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
from textwrap import dedent
from unittest.mock import patch

from django.test import override_settings

from hyperkitty.lib.renderer import markdown_renderer
from hyperkitty.templatetags.hk_generic import (
    export_allowed, gravatar, settings_value_equals, snip_quoted)
from hyperkitty.templatetags.hk_haystack import nolongterms
from hyperkitty.tests.utils import TestCase


class SnipQuotedTestCase(TestCase):

    quotemsg = "[SNIP]"

    def test_quote_1(self):
        contents = """
On Fri, 09.11.12 11:27, Someone wrote:
&gt; This is the first quoted line
&gt; This is the second quoted line
This is the response.
"""
        expected = (
            """
            On Fri, 09.11.12 11:27, Someone wrote:
            <div class="quoted-switch"><a style="font-weight:normal" href="#">%s</a></div><div class="quoted-text quoted-text-0">  This is the first quoted line
             This is the second quoted line </div>This is the response.
            """  # noqa: E501
        ) % self.quotemsg
        result = snip_quoted(contents, self.quotemsg)

        self.assertEqual(result, "\n" + dedent(expected).strip() + "\n")

    def test_quote_2(self):
        contents = """
On Fri, 09.11.12 11:27, Someone wrote:
&gt; This is the first quoted line
&gt; On Fri 07.25.12, Aperson wrote:
&gt; &gt; This is the second quoted line.
&gt; This is the second quoted line
This is the response.
"""
        expected = (
            """
On Fri, 09.11.12 11:27, Someone wrote:
<div class="quoted-switch"><a style="font-weight:normal" href="#">{}</a></div>"""   # noqa: E501
            """<div class="quoted-text quoted-text-0">  This is the first quoted line
 On Fri 07.25.12, Aperson wrote:
<div class="quoted-text quoted-text-1">  This is the second quoted line. </div>"""   # noqa: E501
            """ This is the second quoted line </div>This is the response.
""").format(self.quotemsg)
        result = snip_quoted(contents, self.quotemsg)
        self.assertEqual(result, expected)


class HaystackTestCase(TestCase):

    def test_nolongterms_short(self):
        short_terms = "dummy sentence with only short terms"
        self.assertEqual(nolongterms(short_terms), short_terms)

    def test_nolongterms_too_long(self):
        long_term = "x" * 240
        text = "dummy %s sentence" % long_term
        self.assertEqual(nolongterms(text), "dummy sentence")

    def test_nolongterms_xmlescape(self):
        # the long term itself is < 240, but it's the XML-escaped value that
        # counts
        long_term = "x" * 237
        text = "dummy <%s> sentence" % long_term
        self.assertEqual(nolongterms(text), "dummy sentence")

    def test_nolongterms_xmlescape_amperstand(self):
        # the long term itself is < 240, but it's the XML-escaped value that
        # counts
        long_term = "&" * 60
        text = "dummy %s sentence" % long_term
        self.assertEqual(nolongterms(text), "dummy sentence")

    def test_nolongterms_doublequotes(self):
        # the long term itself is < 240, but the measured string is
        # double-quote-escaped first
        long_term = "x" * 237
        text = 'dummy "%s" sentence' % long_term
        self.assertEqual(nolongterms(text), "dummy sentence")

    def test_nolongterms_singlequotes(self):
        # the long term itself is < 240, but the measured string is
        # quote-escaped first
        long_term = "x" * 237
        text = "dummy '%s' sentence" % long_term
        self.assertEqual(nolongterms(text), "dummy sentence")

    def test_nolongterms_encoding(self):
        # the long term itself is < 240, but it's the utf8-encoded value that
        # counts
        long_term = "é" * 121
        text = "dummy %s sentence" % long_term
        self.assertEqual(nolongterms(text), "dummy sentence")


class TestGravatar(TestCase):

    def test_gravatar(self):
        """Test that we call gravatar library."""
        with patch('hyperkitty''.templatetags.'
                   'hk_generic.gravatar_orig') as mock_grav:
            gravatar('aperson@example.com')
            self.assertTrue(mock_grav.called)
            mock_grav.assert_called_with('aperson@example.com')
        html = gravatar('bperson@example.com')
        self.assertEqual(
            html,
            '<img class="gravatar" src="https://secure.gravatar.com/avatar/a100672ae026b5b7a7fb2929ff533e1e.jpg?s=80&amp;d=mm&amp;r=g" width="80" height="80" alt="" />')  # noqa: E501

    @override_settings(HYPERKITTY_ENABLE_GRAVATAR=False)
    def test_disabled_gravatar(self):
        with patch('hyperkitty''.templatetags.'
                   'hk_generic.gravatar_orig') as mock_grav:
            resp = gravatar('aperson@example.com')
            self.assertFalse(mock_grav.called)
            self.assertEqual(resp, '')


class TestDecorate(TestCase):

    def setUp(self):
        pass

    def test_parse_quote(self):
        contents = """
On Fri, 09.11.12 11:27, Someone wrote:
> This is the first quoted line
> On Fri 07.25.12, Aperson wrote:
>> This is the second quoted line.
This is the response.
"""
        expected = (
            '<p>On Fri, 09.11.12 11:27, Someone wrote:</p>\n'
            '<div class="quoted-switch"><a href="#">...</a></div>'
            '<blockquote class="blockquote quoted-text"><p>This is the first quoted line\nOn Fri 07.25.12, Aperson wrote:</p>\n'  # noqa: E501
            '<div class="quoted-switch"><a href="#">...</a></div>'
            '<blockquote class="blockquote quoted-text"><p>This is the second quoted line.</p>\n'   # noqa: E501
            '</blockquote></blockquote>'
            '<p>This is the response.</p>\n')
        result = markdown_renderer(contents)
        self.assertEqual(result.strip(), expected.strip())

    def test_parse_heading_normal(self):
        contents = """
Heading 1
=========
"""
        result = markdown_renderer(contents)
        self.assertEqual(result.strip(), "<h1>Heading 1</h1>")

    def test_parse_autolink(self):
        contents = """
https://some.url/llasdfjaksdgfjsdfgkjasdfbgksdfjgbsdfkgjbsdflkgjbsdflgksjdhfbgksdfgb
"""
        result = markdown_renderer(contents)
        self.assertEqual(
            result.strip(),
            '<p><a target="_blank" href="https://some.url/llasdfjaksdgfjsdfgkjasdfbgksdfjgbsdfkgjbsdflkgjbsdflgksjdhfbgksdfgb">https://some.url/llasdfjaksdgfjsdfgkjasdfbgksdfjgbsdfkgjbsdflkgjbsdflgksjdhf...</a></p>')   # noqa: E501

    def test_autolink_small_url(self):
        # Test that autolink doesn't add ... to URLs that aren't truncated.
        contents = """
https://some.url/example
"""
        result = markdown_renderer(contents)
        self.assertEqual(
            result.strip(),
            '<p><a target="_blank" href="https://some.url/example">https://some.url/example</a></p>')  # noqa: E501

    def test_image_markdown(self):
        contents = """
![Image Alt Text](https://url.com/image.png "Alt Text")
"""
        result = markdown_renderer(contents)
        self.assertEqual(
            result.strip(),
            '<p>![Image Alt Text](https://url.com/image.png "Alt Text")</p>')

    def test_image_html(self):
        contents = """
![Image Alt Text](https://url.com/image.png "Image title")
"""
        with self.settings(HYPERKITTY_RENDER_INLINE_IMAGE=True):
            result = markdown_renderer(contents)
        self.assertEqual(
            result.strip(), '<p><img src="https://url.com/image.png" alt="Image Alt Text" title="Image title" /></p>')  # noqa: E501

    def test_header(self):
        contents = """\
# This is another sample text.
"""
        result = markdown_renderer(contents)
        self.assertEqual(
            result.strip(),
            '<p># This is another sample text.</p>')


class SettingsValuesTest(TestCase):

    def test_settings_value_equals(self):
        # Simple test to ensure the method works as expected.
        # When the values aren't set, it imples empty string.
        self.assertFalse(settings_value_equals('MY_SETTING', True))
        self.assertTrue(settings_value_equals('MY_SETTING', ''))
        with override_settings(HYPERKITTY_ENABLE_GRAVATAR=False):
            self.assertTrue(settings_value_equals(
                'HYPERKITTY_ENABLE_GRAVATAR', False))
        with override_settings(MY_SETTING='SOME_VALUE'):
            self.assertFalse(settings_value_equals('MY_SETTING', 'Anything'))
            self.assertTrue(settings_value_equals('MY_SETTING', 'SOME_VALUE'))

    def test_export_allowed(self):
        # Test when value is not set.
        self.assertTrue(export_allowed())
        # Test when set to True.
        with override_settings(HYPERKITTY_MBOX_EXPORT=True):
            self.assertTrue(export_allowed())
        # Test when set to False.
        with override_settings(HYPERKITTY_MBOX_EXPORT=False):
            self.assertFalse(export_allowed())
