# -*- coding: utf-8 -*-
#
# Copyright (C) 2011-2023 by the Free Software Foundation, Inc.
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
#
# Author: Aurelien Bompard <abompard@fedoraproject.org>

"""
Import the content of a mbox file into the database.
"""

import mailbox
import os
import re
from contextlib import suppress
from datetime import datetime
from email import message_from_bytes, policy
from email.utils import make_msgid, unquote
from math import floor
from traceback import print_exc

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import Error as DatabaseError
from django.db import transaction
from django.utils.formats import date_format
from django.utils.timezone import utc

from dateutil import tz
from dateutil.parser import parse as parse_date

from hyperkitty.lib.analysis import compute_thread_order_and_depth
from hyperkitty.lib.incoming import DuplicateMessage, add_to_list
from hyperkitty.lib.mailman import sync_with_mailman
from hyperkitty.lib.utils import get_message_id
from hyperkitty.management.utils import setup_logging
from hyperkitty.models import Email, MailingList, Thread


# Allow all wierd line endings.
TEXTWRAP_RE = re.compile(r"(\n|\r|\r\n|\n\r)\s*")


class ProgressMarker(object):

    def __init__(self, verbose, stdout):
        self.verbose = verbose
        self.total = None
        self.count = 0
        self.count_imported = 0
        self.spinner_seq = ('|', '/', '-', '\\')
        self.stdout = stdout

    def tick(self, msgid=None):
        if self.total:
            msg = "%d%%" % floor(100.0 * self.count / self.total)
        else:
            msg = self.spinner_seq[self.count % len(self.spinner_seq)]
        if self.verbose:
            if self.total:
                self.stdout.write(
                    "%s (%d/%d, %s)" % (msgid, self.count, self.total, msg))
            else:
                self.stdout.write("%s (%d)" % (msgid, self.count))
        else:
            self.stdout.write("\r%s" % msg, ending='')
            self.stdout.flush()
        self.count += 1

    def finish(self):
        if self.verbose:
            self.stdout.write('  %s emails read' % self.count)
            self.stdout.write('  %s email added to the database'
                              % self.count_imported)
        else:
            self.stdout.write("\r", ending='')
            self.stdout.flush()


class DbImporter(object):
    """
    Import email messages into the HyperKitty database using its API.
    """

    def __init__(self, list_address, options, stdout, stderr):
        self.list_address = list_address
        self.verbose = options["verbosity"] >= 2
        self.since = options.get("since")
        self.impacted_thread_ids = set()
        self.stdout = stdout
        self.stderr = stderr

    def _is_too_old(self, message, report_name):
        if not self.since:
            return False
        date = message.get("date")
        if not date:
            return False
        try:
            date = parse_date(date)
        except ValueError as e:
            if self.verbose:
                self.stderr.write(
                    "Can't parse date string in message {}{}: {}. "
                    "The date string is: '{}'".format(
                        unquote(message.get("message-id", 'n/a')),
                        report_name, e, date.decode("ascii", "replace")))
            return False
        if date.tzinfo is None:
            date = date.replace(tzinfo=utc)
        try:
            return date <= self.since
        except ValueError:
            return False

    def _get_date(self, message, header, report_name):
        try:
            date = message.get(header)
            if date and not date.datetime:
                if self.verbose:
                    self.stderr.write(
                        "Bad datetime in {} header in message {}{}.".format(
                            header, unquote(message.get("message-id", 'n/a')),
                            report_name))
                return None
        except (AttributeError, TypeError, ValueError) as e:
            if self.verbose:
                self.stderr.write(
                    "Can't get {} header in message {}{}: {}.".format(
                        header, unquote(message.get("message-id", 'n/a')),
                        report_name, e))
            return None
        return date

    def _fix_mid(self, mid):
        # Message-IDs of the form
        # Message-ID: <58C6B8A302CF0E71@example.com> (added by
        #  postmaster@example.com)
        # have been seen.  First remove whitespace. Then if the Message-ID
        # starts with '<' remove everything after the first '>'. Then ensure
        # it has '<' and '>' at beginning and end.
        mid = re.sub(r'\s', '', mid)
        if mid.startswith('<'):
            mid = re.sub('>.*', '>', mid)
        else:
            mid = '<' + mid
        if not mid.endswith('>'):
            mid += '>'
        # We've also seen bogus Message-IDs with non-ascii so remove any.
        mid = mid.encode('ascii', 'ignore').decode('ascii')
        return mid

    def from_mbox(self, mbfile, report_name):
        """
        Insert all the emails contained in an mbox file into the database.

        :arg mbfile: a mailbox file
        """
        mbox = mailbox.mbox(mbfile)
        progress_marker = ProgressMarker(self.verbose, self.stdout)
        if not self.since:
            progress_marker.total = len(mbox)
        for msg in mbox:
            # FIXME: this converts mailbox.mboxMessage to
            # email.message.EmailMessage
            # We need to fix up Message-IDs here because recent Python email
            # throws an IndexError exception on getting a Message-ID of <>.
            if msg['message-id'] is None:
                msg['Message-ID'] = make_msgid('generated')
            mid = str(msg['message-id'])
            if mid.strip() in ('', '<>'):
                msg.replace_header('Message-ID', make_msgid('generated'))
            elif mid != self._fix_mid(mid):
                msg.replace_header('Message-ID', self._fix_mid(mid))
            try:
                msg_raw = msg.as_bytes(unixfrom=False)
            except UnicodeError as e:
                self.stderr.write('Failed to convert {}{} to bytes\n'
                                  '    {}'.format(
                                   unquote(msg.get("Message-Id", 'n/a')),
                                   report_name, e))
                continue
            unixfrom = msg.get_from()
            try:
                message = message_from_bytes(msg_raw, policy=policy.default)
            except (UnicodeError, IndexError) as e:
                self.stderr.write('Failed to convert {}{} to '
                                  'email.message.Message\n    {}'.format(
                                   unquote(msg.get("Message-Id", 'n/a')),
                                   report_name, e))
                continue
            # Fix missing and wierd Date: headers.
            date = (self._get_date(message, "date", report_name) or
                    self._get_date(message, "resent-date", report_name))
            if unixfrom and not date:
                date = " ".join(unixfrom.split()[1:])

            if date:
                # Make sure this date can be parsed before setting it as as the
                # header. If not, a TypeError is raised and we just keep the
                # old Header.
                with suppress(TypeError):
                    del message['Date']
                    message['Date'] = date

            if self._is_too_old(message, report_name):
                continue
            progress_marker.tick(unquote(message.get("message-id", 'n/a')))
            # Un-wrap the subject line if necessary
            if message["subject"]:
                # If we can't replace the header because it contains some
                # unicode Next Line or similar. Just keep the original.
                with suppress(ValueError):
                    message.replace_header(
                        "subject", TEXTWRAP_RE.sub(" ", message["subject"]))
            if unixfrom:
                message.set_unixfrom(unixfrom)
            # Now insert the message
            try:
                with transaction.atomic():
                    add_to_list(self.list_address, message, from_import=True)
            except DuplicateMessage as e:
                if self.verbose:
                    self.stderr.write(
                        "Duplicate email with message-id '%s'%s"
                        % (e.args[0], report_name))
                continue
            except (LookupError, UnicodeError, ValueError) as e:
                self.stderr.write("Failed adding message %s%s: %s"
                                  % (message.get("Message-ID"),
                                     report_name, e))
                if len(e.args) == 2:
                    try:
                        self.stderr.write(
                            "%s from %s about %s"
                            % (e.args[0], e.args[1].get("From"),
                               e.args[1].get("Subject")))
                    except UnicodeDecodeError:
                        pass
                # Don't reraise the exception
                continue
            except DatabaseError:
                try:
                    print_exc(file=self.stderr)
                except UnicodeError:
                    pass
                self.stderr.write(
                    "Message %s%s failed to import, skipping"
                    % (unquote(message["Message-Id"]), report_name))
                continue
            except Exception as e:
                # In case of *any* exception, log and continue to import the
                # rest of the archive.
                self.stderr.write(
                    "Message {}{} failed to import, skipping\n    {}".format(
                        unquote(message["Message-ID"]), report_name, e))
                continue
            email = Email.objects.get(
                mailinglist__name=self.list_address,
                message_id=get_message_id(message))
            # # Commit every time to be able to rollback on error
            # if not transaction.get_autocommit():
            #     transaction.commit()
            # Store the list of impacted threads to be able to compute the
            # thread_order and thread_depth values
            self.impacted_thread_ids.add(email.thread_id)
            progress_marker.count_imported += 1
        # self.store.search_index.flush() # Now commit to the search index
        progress_marker.finish()
        mbox.close()


class Command(BaseCommand):
    help = (
        "Imports the specified archive mbox(es). "
        "Before running this, the mbox(es) should be checked for "
        "messages that could throw uncaught exceptions with the "
        "contrib/check_hk_archive script and for unescaped 'From ' lines "
        "with Mailman 2.1's cleanarch script.")

    def add_arguments(self, parser):
        parser.add_argument('mbox', nargs='+')
        parser.add_argument(
            '--delete',
            action='store_true',
            dest='delete',
            default=False,
            help='Delete poll instead of closing it')
        parser.add_argument(
            '-l', '--list-address',
            help="the full list address the mailbox will be imported to")
        parser.add_argument(
            '--no-sync-mailman',
            action='store_true', default=False,
            help="do not sync properties with Mailman (faster, useful "
                 "for batch imports)")
        parser.add_argument(
            '--since',
            help="only import emails later than this date.  Defaults to the "
                 "date of the newest message in the existing archive if any.")
        parser.add_argument(
            '--ignore-mtime',
            action='store_true', default=False,
            help="do not check mbox mtimes (slower)")

    def _check_options(self, options):
        if not options.get("list_address"):
            raise CommandError(
                "The list address must be given on the command-line.")
        if "@" not in options["list_address"]:
            raise CommandError(
                "The list address must be fully-qualified, including "
                "the '@' symbol and the domain name.")
        if not options.get("mbox"):
            raise CommandError("No mbox file selected.")
        for mbfile in options["mbox"]:
            if not os.path.exists(mbfile):
                raise CommandError("No such file: %s" % mbfile)
        options["verbosity"] = int(options.get("verbosity", "1"))
        if options["since"]:
            try:
                options["since"] = parse_date(options["since"])
                if options["since"].tzinfo is None:
                    options["since"] = options["since"].replace(
                        tzinfo=tz.tzlocal())
            except ValueError as e:
                raise CommandError("invalid value for '--since': %s" % e)

    def handle(self, *args, **options):
        self._check_options(options)
        setup_logging(self, options["verbosity"])
        # main
        list_address = options["list_address"].lower()
        # Keep autocommit on SQLite:
        # https://docs.djangoproject.com/en/1.8/topics/db/transactions/#savepoints-in-sqlite
        # if (settings.DATABASES["default"]["ENGINE"]
        #     != "django.db.backends.sqlite3":
        #     transaction.set_autocommit(False)
        # Sync list settings with Mailman before importing messages:
        if not options["no_sync_mailman"]:
            mlist = MailingList.objects.get_or_create(name=list_address)[0]
            mlist.update_from_mailman()
            mlist.save()
        settings.HYPERKITTY_BATCH_MODE = True
        # Only import emails newer than the latest email in the DB
        latest_email_date = Email.objects.filter(
                mailinglist__name=list_address
            ).values("date").order_by("-date").first()
        if latest_email_date and not options["since"]:
            options["since"] = latest_email_date["date"]
            self.stdout.write(
                'Warning: not importing messages older than {}. '
                'Use "--since=<date>" to import older messages.'.format(
                    date_format(latest_email_date["date"])))
        if options["since"] and options["verbosity"] >= 2:
            self.stdout.write(
                "Only emails after %s will be imported" % options["since"])
        importer = DbImporter(list_address, options, self.stdout, self.stderr)
        # disable mailman client for now
        for mbfile in options["mbox"]:
            if len(options["mbox"]) > 1:
                report_name = ' from mbox {}'.format(mbfile)
            else:
                report_name = ''
            if options["verbosity"] >= 1:
                self.stdout.write("Importing from mbox file %s to %s"
                                  % (mbfile, list_address))
            if not options["ignore_mtime"] and options["since"] is not None:
                mtime = datetime.fromtimestamp(
                    os.path.getmtime(mbfile), tz.tzlocal())
                if mtime <= options["since"]:
                    if options["verbosity"] >= 2:
                        self.stdout.write('Mailbox file for %s is too old'
                                          % list_address)
                    continue
            importer.from_mbox(mbfile, report_name)
            if options["verbosity"] >= 2:
                total_in_list = Email.objects.filter(
                    mailinglist__name=list_address).count()
                self.stdout.write('  %s emails are stored into the database'
                                  % total_in_list)
        if options["verbosity"] >= 1:
            self.stdout.write("Computing thread structure")
        # Work on batches of thread ids to avoid creating a huge SQL request
        # (it's an IN statement)
        thread_ids = list(importer.impacted_thread_ids)
        while thread_ids:
            thread_ids_batch = thread_ids[:100]
            thread_ids = thread_ids[100:]
            for thread in Thread.objects.filter(id__in=thread_ids_batch):
                compute_thread_order_and_depth(thread)
        if not options["no_sync_mailman"]:
            if options["verbosity"] >= 1:
                self.stdout.write("Synchronizing properties with Mailman")
            sync_with_mailman()
            # if not transaction.get_autocommit():
            #     transaction.commit()
        if options["verbosity"] >= 1:
            self.stdout.write("Warming up cache")
        call_command("hyperkitty_warm_up_cache", list_address)
        if options["verbosity"] >= 1:
            self.stdout.write(
                "The full-text search index is not updated for this list. "
                "It will not be updated by the 'minutely' incremental "
                "update job. To update the index for this list, run the "
                "Django admin command with arguments "
                "'update_index_one_list {}'."
                .format(list_address)
                )
