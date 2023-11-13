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

import logging
from urllib.error import HTTPError

from django.core.cache import cache

from django_mailman3.lib.mailman import get_mailman_client
from mailmanclient import MailmanConnectionError


logger = logging.getLogger(__name__)


class ModeratedListException(Exception):
    pass


class AddressBannedFromList(Exception):
    pass


def subscribe(list_id, user, email=None, display_name=None):
    """Subscribe a user to a given MailingList.

    :param list_id: List to subscribe the user to.
    :param user: Django user to subscribe.
    :param email: Email address of the Django user. If not provided
        the default email of the Django user is used.
    :param display_name: The Display name of the user being subscribed,
        if not provided, a join of First and Last name of the Django
        user is used.

    :returns: Boolean indicating if the user was successfully subscribed
        to the list or not.
    """
    if email is None:
        email = user.email
    if display_name is None:
        display_name = "%s %s" % (user.first_name, user.last_name)
    client = get_mailman_client()
    rest_list = client.get_list(list_id)
    subscription_policy = rest_list.settings.get(
        "subscription_policy", "moderate")
    # Add a flag to return that would tell the user they have been subscribed
    # to the current list.
    subscribed_now = False
    try:
        member = rest_list.get_member(email)
    except ValueError:
        # We don't want to bypass moderation, don't subscribe. Instead
        # raise an error so that it can be caught to show the user
        if subscription_policy in ("moderate", "confirm_then_moderate"):
            raise ModeratedListException(
                "This list is moderated, please subscribe"
                " to it before posting.")

        # not subscribed yet, subscribe the user without email delivery
        try:
            member = rest_list.subscribe(
                email, display_name, pre_verified=True, pre_confirmed=True)
        except HTTPError as e:
            if e.code == 409:
                logger.info("Subscription for %s to %s is already pending",
                            email, list_id)
                return subscribed_now
            elif e.code == 400 and e.reason == 'Membership is banned':
                # Using the message string to actually do something here is
                # not the best idea, but we don't have any better way to
                # handle errors right now.
                # Ideally, API will assign different error codes to different
                # types of errors and we can use an internal no. to signal
                # various different errors.
                logger.info("%s is banned from %s", email, list_id)
                raise AddressBannedFromList(
                    "Address {} is banned from {}".format(email, list_id))
            else:
                raise
        # The result can be a Member object or a dict if the subscription can't
        # be done directly, or if it's pending, or something else.
        # Broken API :-(
        if isinstance(member, dict):
            logger.info("Subscription for %s to %s is pending",
                        email, list_id)
            return subscribed_now
        member.preferences["delivery_status"] = "by_user"
        member.preferences.save()
        subscribed_now = True
        cache.delete("User:%s:subscriptions" % user.id, version=2)
        logger.info("Subscribing %s to %s on first post",
                    email, list_id)

    return subscribed_now


def get_new_lists_from_mailman():
    """Poll Mailman's API and get all the new MailingLists.

    This is needed so that Hyperkitty can synchronize the internal
    state with Mailman Core. Ideally, HK is getting right signals from
    Postorius or email archiving is causing the new lists to be imported
    from the API on demand.

    This is typically invoked from one of the scheduled cron jobs.
    """
    from hyperkitty.models import MailingList
    mmclient = get_mailman_client()
    page_num = 0
    while page_num < 10000:  # Just for security
        page_num += 1
        try:
            mlist_page = mmclient.get_list_page(count=10, page=page_num)
        except MailmanConnectionError:
            break
        except HTTPError:
            break  # can't update at this time
        for mm_list in mlist_page:
            if MailingList.objects.filter(name=mm_list.fqdn_listname).exists():
                continue
            if mm_list.settings["archive_policy"] == "never":
                continue  # Should we display those lists anyway?
            logger.info("Imported the new list %s from Mailman",
                        mm_list.fqdn_listname)
            mlist = MailingList.objects.create(name=mm_list.fqdn_listname)
            mlist.update_from_mailman()
        if not mlist_page.has_next:
            break


def import_list_from_mailman(list_id):
    """Given a single MailingList, import details from Core.

    :param list_id: List id for MailingList to import.
    """
    from hyperkitty.models import MailingList
    mmclient = get_mailman_client()
    try:
        mm_list = mmclient.get_list(list_id)
    except (MailmanConnectionError, HTTPError):
        return
    mlist, created = MailingList.objects.get_or_create(
        name=mm_list.fqdn_listname)
    if created:
        logger.info("Imported the new list %s from Mailman",
                    mm_list.fqdn_listname)
    mlist.update_from_mailman()


def sync_with_mailman(overwrite=False):
    """Sync all the details from Mailman.

    This is invoked from Cron job/hyperkitty_import or hyperkitty_sync command.

    :param overwrite: Overwrite the existing Senders.
    """
    from hyperkitty.models import MailingList, Sender
    for mlist in MailingList.objects.all():
        mlist.update_from_mailman()
    # Now sync Sender.mailman_id with Mailman's User.user_id
    # There can be thousands of senders, break into smaller chunks to avoid
    # hogging up the memory
    buffer_size = 1000
    query = Sender.objects.all()
    if not overwrite:
        query = query.filter(mailman_id__isnull=True)
    prev_count = query.count()
    lower_bound = 0
    upper_bound = buffer_size
    while True:
        try:
            for sender in query.all()[lower_bound:upper_bound]:
                sender.set_mailman_id()
        except MailmanConnectionError:
            break  # Can't refresh at this time
        count = query.count()
        if count == 0:
            break  # all done
        if count == prev_count:
            # no improvement...
            if count < upper_bound:
                break  # ...and all users checked
            else:
                # there may be some more left
                lower_bound = upper_bound
                upper_bound += buffer_size
        prev_count = count
        logger.info("%d emails left to refresh, checked %d",
                    count, lower_bound)
