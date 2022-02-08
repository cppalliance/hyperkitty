# -*- coding: utf-8 -*-

import io
import tempfile
from contextlib import redirect_stdout, suppress
from email.message import EmailMessage

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError

from hyperkitty.lib.incoming import add_to_list
from hyperkitty.models import Attachment, Email
from hyperkitty.tests.utils import TestCase


class CommandTestCase(TestCase):

    def setUp(self):
        msg_in = EmailMessage()
        msg_in["From"] = "dummy@example.com"
        msg_in["Message-ID"] = "<msg>"
        msg_in.set_content("Hello World.")
        msg_in.add_attachment("Dummy message", subtype='plain')
        msg_in.add_attachment("<html><body>Dummy message</body></html>",
                              subtype='html')
        add_to_list("list@example.com", msg_in)
        self.tempdir = tempfile.TemporaryDirectory()

    def tearDown(self):
        settings.HYPERKITTY_ATTACHMENT_FOLDER = None
        self.tempdir.cleanup()

    def test_no_attachment_folder(self):
        # Test that no HYPERKITTY_ATTACHMENT_FOLDER raises CommandError
        with self.assertRaisesRegex(CommandError,
                                    'HYPERKITTY_ATTACHMENT_FOLDER is not set'):
            call_command('attachments_to_file')

    def test_attachments_are_moved(self):
        # Test that attachments are moved to file system and retrievable.
        settings.HYPERKITTY_ATTACHMENT_FOLDER = self.tempdir.name
        call_command('attachments_to_file')
        # There is no content in the attachments table
        count = 0
        for attachment in Attachment.objects.all():
            count += 1
            self.assertIsNone(attachment.content)
        self.assertEqual(count, 2)
        # Get the message as_message and ensure it has the attachments.
        email = Email.objects.get(message_id="msg")
        msg = email.as_message()
        self.assertEqual(msg["From"], "dummy@example.com")
        self.assertEqual(msg["Message-ID"], "<msg>")
        self.assertTrue(msg.is_multipart())
        payload = msg.get_payload()
        self.assertEqual(len(payload), 3)
        self.assertEqual(
            payload[0].get_content(), "Hello World.\n\n\n\n\n")
        self.assertEqual(
            payload[1].get_content(), "Dummy message\n")
        self.assertEqual(payload[2].get_content_type(), "text/html")
        self.assertEqual(
            payload[2].get_content(),
            "<html><body>Dummy message</body></html>\n")

    def test_verbosity_option(self):
        # This merely tests that the option can be specified without issue,
        # and that an extra newline is printed before the summary.
        settings.HYPERKITTY_ATTACHMENT_FOLDER = self.tempdir.name
        with io.StringIO() as fp, redirect_stdout(fp):
            call_command('attachments_to_file', '--verbosity=1')
            self.assertEqual(fp.getvalue(), """\

2 attachments moved.
""")

    def test_chunk_size_option(self):
        # This merely tests that the option can be specified without issue,
        settings.HYPERKITTY_ATTACHMENT_FOLDER = self.tempdir.name
        with io.StringIO() as fp, redirect_stdout(fp):
            call_command('attachments_to_file', '--chunk-size=1000')
            self.assertEqual(fp.getvalue(), """\
2 attachments moved.
""")

    def test_help_output(self):
        with io.StringIO() as fp, redirect_stdout(fp):
            with suppress(SystemExit):
                call_command('attachments_to_file', '--help')
            self.assertRegex(fp.getvalue(), """\
(?s)usage:  attachments_to_file \[-h\] \[-c CHUNK_SIZE\] \[--version\]
                            \[--settings SETTINGS\] \[--pythonpath PYTHONPATH\]
                            \[--traceback\] \[--no-color\] \[--force-color\]
                            .*\[-v \{0,1\}\]

Move attachments from database to file system after setting
HYPERKITTY_ATTACHMENT_FOLDER\.

optional arguments:
  -h, --help            show this help message and exit
  -c CHUNK_SIZE, --chunk-size CHUNK_SIZE
                        Specify the number of attachments to retrieve at one
                        time from the database\. Default is 100\. Larger values
                        use more memory\.
  --version             show program's version number and exit
  --settings SETTINGS   The Python path to a settings module, e\.g\.
                        "myproject\.settings\.main". If this isn't provided, the
                        DJANGO_SETTINGS_MODULE environment variable will be
                        used\.
  --pythonpath PYTHONPATH
                        A directory to add to the Python path, e\.g\.
                        "/home/djangoprojects/myproject"\.
  --traceback           Raise on CommandError exceptions
  --no-color            Don't colorize the command output\.
  --force-color         Force colorization of the command output\..*
  -v \{0,1\}, --verbosity \{0,1\}
                        Verbosity = 1 will print a dot for each 100
                        attachments moved\.
""")                                               # noqa E501,W605
