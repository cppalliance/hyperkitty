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

from hyperkitty.lib.renderer import markdown_renderer, text_renderer
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
            ('<p><a target="_blank" href="https://some.url/llasdfjaksdgfjsdfgkjasdfbgksdfjgbsdfkgjbsdflkgjbsdflgksjdhfbgksdfgb">https://some.url/llasdfjaksdgfjsdfgkjasdfbgksdfjgbsdfkgjbsdflkgjbsdflgksjdhf...</a></p>'))   # noqa: E501

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

    def test_outlook_style_reply_blockquote(self):
        contents = """\
This is the replied text.

Sent from my Galaxy

-------- Original message --------
From: A person <person(a)example.com>
Date: 6/26/23 16:23 (GMT-05:00)
To: mytestlist@example.com
Subject: Testing if the quoted reply works with Outlook style.

This is the original text *with* some __markup__.
"""
        result = markdown_renderer(contents)
        print(result)
        self.assertEqual(
            result.strip(),
            """<p>This is the replied text.</p>
<p>Sent from my Galaxy</p>
<div class="quoted-switch"><a href="#">...</a></div><blockquote class="blockquote quoted-text"><p>-------- Original message --------
From: A person <person(a)example.com>
Date: 6/26/23 16:23 (GMT-05:00)
To: mytestlist@example.com
Subject: Testing if the quoted reply works with Outlook style.
This is the original text <em>*with*</em> some <strong>__markup__</strong>.</p>
</blockquote>""")  # noqa: E501

    def test_backslash(self):
        contents = r'^.*@gmail\.com$'
        result = markdown_renderer(contents)
        self.assertEqual(
            result.strip(),
            r'<p>^.*@gmail\.com$</p>')

    def test_backslash_code(self):
        contents = r'`^.*@gmail\.com$`'
        result = markdown_renderer(contents)
        self.assertEqual(
            result.strip(),
            r'<p><code>^.*@gmail\.com$</code></p>')

    def test_backslash_code_block(self):
        contents = r"""```
^.*@gmail\.com$
```"""
        result = markdown_renderer(contents)
        self.assertEqual(
            result.strip(),
            r"""<pre><code>^.*@gmail\.com$
</code></pre>""")


class TestDecoratePlain(TestCase):

    def test_backslash(self):
        contents = r'^.*@gmail\.com$'
        result = text_renderer(contents)
        self.assertEqual(
            result.strip(),
            r'<p>^.*@gmail\.com$</p>')

    def test_backslash_code(self):
        contents = r'`^.*@gmail\.com$`'
        result = text_renderer(contents)
        self.assertEqual(
            result.strip(),
            r'<p>`^.*@gmail\.com$`</p>')

    def test_plaintext_patch(self):
        self.maxDiff = None
        contents = TEST_EMAIL_PATCH_QUOTED
        result = text_renderer(contents)
        self.assertEqual(result.strip(), EXPECTED_TEST_EMAIL_PATCH_QUOTED)

    def test_plaintext_patch_gl_494(self):
        self.maxDiff = None
        contents = TEST_EMAIL_ISSUE_GL_494
        result = text_renderer(contents)
        self.assertEqual(
            result.strip(), TEST_EMAIL_TEXT_RENDER_RESULT.strip())


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


# Sample emails for testing rendering.
TEST_EMAIL_PATCH_QUOTED = r"""
Regarding 3be269542f4d18eaee0ad8fbeffa55708557879f,

> [... 62 lines elided]
> diff --git a/storage/spider/spd_param.cc b/storage/spider/spd_param.cc
> index 2da262cd2bc..308857d153a 100644
> --- a/storage/spider/spd_param.cc
> +++ b/storage/spider/spd_param.cc
> @@ -116,16 +116,20 @@ extern volatile ulonglong spider_mon_table_cache_vers=
ion_req;
>        MYSQL_SYSVAR_NAME(param_name).def_val;                            \
>    }
> +extern handlerton *spider_hton_ptr;
>  static int spider_trx_status_var(THD *thd, SHOW_VAR *var, char *buff,
>                                   ulonglong SPIDER_TRX::*counter)
>  {
> -  int error_num =3D 0;
> -  SPIDER_TRX *trx;
>    DBUG_ENTER("spider_direct_update");
>    var->type =3D SHOW_LONGLONG;
> -  if ((trx =3D spider_get_trx(thd, TRUE, &error_num)))
> -    var->value =3D (char *) &(trx->*counter);
> -  DBUG_RETURN(error_num);
> +  var->value=3D buff;
> +  if (thd !=3D current_thd)
> +    mysql_mutex_lock(&thd->LOCK_thd_data);


If it always returns 0, how about we change the signature of this
function to return void?

>  }

Best"""  # noqa: E501


EXPECTED_TEST_EMAIL_PATCH_QUOTED = r"""<p>Regarding 3be269542f4d18eaee0ad8fbeffa55708557879f,</p>
<div class="quoted-switch"><a href="#">...</a></div><blockquote class="blockquote quoted-text"><p>[... 62 lines elided]
diff --git a/storage/spider/spd_param.cc b/storage/spider/spd_param.cc
index 2da262cd2bc..308857d153a 100644
--- a/storage/spider/spd_param.cc
+++ b/storage/spider/spd_param.cc
@@ -116,16 +116,20 @@ extern volatile ulonglong spider_mon_table_cache_vers=
ion_req;
       MYSQL_SYSVAR_NAME(param_name).def_val;                            \
   }
+extern handlerton *spider_hton_ptr;
 static int spider_trx_status_var(THD *thd, SHOW_VAR *var, char *buff,
                                  ulonglong SPIDER_TRX::*counter)
 {
-  int error_num =3D 0;
-  SPIDER_TRX *trx;
   DBUG_ENTER("spider_direct_update");
   var->type =3D SHOW_LONGLONG;
-  if ((trx =3D spider_get_trx(thd, TRUE, &error_num)))
-    var->value =3D (char *) &(trx->*counter);
-  DBUG_RETURN(error_num);
+  var->value=3D buff;
+  if (thd !=3D current_thd)
+    mysql_mutex_lock(&thd->LOCK_thd_data);</p>
</blockquote><p>If it always returns 0, how about we change the signature of this
function to return void?</p>
<div class="quoted-switch"><a href="#">...</a></div><blockquote class="blockquote quoted-text"><p>}</p>
</blockquote><p>Best</p>"""  # noqa: E501

TEST_EMAIL_ISSUE_GL_494 = """>> >>> >In the example"""

TEST_EMAIL_TEXT_RENDER_RESULT = """<div class="quoted-switch"><a href="#">...</a></div><blockquote class="blockquote quoted-text"><div class="quoted-switch"><a href="#">...</a></div><blockquote class="blockquote quoted-text"><div class="quoted-switch"><a href="#">...</a></div><blockquote class="blockquote quoted-text"><div class="quoted-switch"><a href="#">...</a></div><blockquote class="blockquote quoted-text"><div class="quoted-switch"><a href="#">...</a></div><blockquote class="blockquote quoted-text"><div class="quoted-switch"><a href="#">...</a></div><blockquote class="blockquote quoted-text"><p>In the example</p>
</blockquote></blockquote></blockquote></blockquote></blockquote></blockquote>"""  # noqa: E501
