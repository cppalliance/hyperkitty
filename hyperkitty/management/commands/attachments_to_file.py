# -*- coding: utf-8 -*-
#
# Copyright (C) 2014-2023 by the Free Software Foundation, Inc.
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
Move attachments from database to file system after setting
HYPERKITTY_ATTACHMENT_FOLDER.
"""

import os

from django.core.management.base import BaseCommand, CommandError

from hyperkitty.management.utils import setup_logging
from hyperkitty.models.email import Attachment


class Command(BaseCommand):
    help = """Move attachments from database to file system after setting
HYPERKITTY_ATTACHMENT_FOLDER."""

    def add_arguments(self, parser):
        for action in parser._actions:
            for option in ('-v', '--verbosity'):
                if vars(action)['option_strings'][0] == option:
                    parser._handle_conflict_resolve(
                        None, [(option, action)])
        parser.add_argument(
            '-v', '--verbosity', default=0,
            type=int, choices=[0, 1],
            help="""Verbosity = 1 will print a dot for each 100 attachments
moved."""
        )
        parser.add_argument(
            '-c', '--chunk-size', default=100, type=int,
            help="""Specify the number of attachments to retrieve at one time
from the database. Default is 100. Larger values use more memory."""
        )

    def handle(self, *args, **options):
        options["verbosity"] = int(options.get("verbosity", "0"))
        options["chunk-size"] = int(options.get("chunk-size", 100))
        setup_logging(self, options["verbosity"])
        if args:
            raise CommandError("no arguments allowed")
        count = 0
        for attachment in Attachment.objects.iterator(
                chunk_size=options["chunk-size"]):
            path = attachment._get_folder()
            if path is None:
                raise CommandError('HYPERKITTY_ATTACHMENT_FOLDER is not set')
            if attachment.content is None:
                continue
            count += 1
            if options['verbosity'] > 0:
                if count % 100 == 0:
                    print('.', end='', flush=True)
                if count % 7000 == 0:
                    print()
            if not os.path.exists(path):
                os.makedirs(path)
            file = os.path.join(path, str(attachment.counter))
            with open(file, 'wb') as fp:
                fp.write(bytes(attachment.content))
            attachment.content = None
            attachment.save()
        if options['verbosity'] > 0:
            print()
        print(f'{count} attachments moved.')
