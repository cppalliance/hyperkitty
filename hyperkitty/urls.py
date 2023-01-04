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
# Author: Aamir Khan <syst3m.w0rm@gmail.com>
# Author: Aurelien Bompard <abompard@fedoraproject.org>
#

from django.conf.urls import include
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import path, re_path
from django.views.generic.base import TemplateView

from hyperkitty.api import email as api_email
from hyperkitty.api import mailinglist as api_mailinglist
from hyperkitty.api import tag as api_tag
from hyperkitty.api import thread as api_thread
from hyperkitty.feed import MailingListFeed
from hyperkitty.lib.view_helpers import check_mlist_private
from hyperkitty.views import (
    accounts, categories, compat, index, mailman, message, mlist, search,
    tags, thread, users)


# flake8: noqa


# List archives and overview
list_patterns = [
    re_path(r'^(?P<year>\d{4})/(?P<month>\d\d?)/(?P<day>\d\d?)/$',
        mlist.archives, name='hk_archives_with_day'),
    re_path(r'^(?P<year>\d{4})/(?P<month>\d\d?)/$',
        mlist.archives, name='hk_archives_with_month'),
    path('latest', mlist.archives, name='hk_archives_latest'),
    path('', mlist.overview, name='hk_list_overview'),
    path('recent-activity', mlist.recent_activity, name='hk_list_recent_activity'),
    path('recent-threads', mlist.overview_recent_threads, name='hk_list_overview_recent_threads'),
    path('pop-threads', mlist.overview_pop_threads, name='hk_list_overview_pop_threads'),
    path('top-threads', mlist.overview_top_threads, name='hk_list_overview_top_threads'),
    path('favorites', mlist.overview_favorites, name='hk_list_overview_favorites'),
    path('posted-to', mlist.overview_posted_to, name='hk_list_overview_posted_to'),
    path('top-posters', mlist.overview_top_posters, name='hk_list_overview_top_posters'),
    re_path(r'^export/(?P<filename>[^/]+)\.mbox.gz$',
        mlist.export_mbox, name='hk_list_export_mbox'),
    path('delete/', mlist.delete, name='hk_list_delete'),
    path('feed/', check_mlist_private(MailingListFeed()), name='hk_list_feed'),
]


# Messages
message_patterns = [
    path('', message.index, name='hk_message_index'),
    path('attachment/<int:counter>/<path:filename>', message.attachment, name='hk_message_attachment'),
    path('vote', message.vote, name='hk_message_vote'),
    path('reply', message.reply, name='hk_message_reply'),
    path('delete', message.delete, name='hk_message_delete'),
]


# Threads
thread_patterns = [
    path('', thread.thread_index, name='hk_thread'),
    path('replies', thread.replies, name='hk_thread_replies'),
    path('tags', thread.tags, name='hk_tags'),
    path('suggest-tags', thread.suggest_tags, name='hk_suggest_tags'),
    path('favorite', thread.favorite, name='hk_favorite'),
    path('category', thread.set_category, name='hk_thread_set_category'),
    path('reattach', thread.reattach, name='hk_thread_reattach'),
    path('reattach-suggest', thread.reattach_suggest, name='hk_thread_reattach_suggest'),
    path('delete', message.delete, name='hk_thread_delete'),
]


# REST API
api_list_patterns = [
    path('', api_mailinglist.MailingListDetail.as_view(), name="hk_api_mailinglist_detail"),
    path('threads/', api_thread.ThreadList.as_view(), name="hk_api_thread_list"),
    path('thread/<str:thread_id>/', api_thread.ThreadDetail.as_view(), name="hk_api_thread_detail"),
    path('emails/', api_email.EmailList.as_view(), name="hk_api_email_list"),
    re_path(r'^email/(?P<message_id_hash>.*)/$',
        api_email.EmailDetail.as_view(), name="hk_api_email_detail"),
    path('thread/<str:thread_id>/emails/', api_email.EmailList.as_view(), name="hk_api_thread_email_list"),
]
api_patterns = [
    path('', TemplateView.as_view(template_name="hyperkitty/api.html")),
    path('lists/', api_mailinglist.MailingListList.as_view(), name="hk_api_mailinglist_list"),
    re_path(r'^list/(?P<mlist_fqdn>[^/@]+@[^/@]+)/', include(api_list_patterns)),
    path('sender/<str:mailman_id>/emails/', api_email.EmailListBySender.as_view(), name="hk_api_sender_email_list"),
    path('tags/', api_tag.TagList.as_view(), name="hk_api_tag_list"),
]


urlpatterns = [
    # Index
    path('', index.index, name='hk_root'),
    path('find-list', index.find_list, name='hk_find_list'),

    # User profile
    path('profile/', include([
        path('', accounts.user_profile, name='hk_user_profile'),
        path('favorites', accounts.favorites, name='hk_user_favorites'),
        path('last_views', accounts.last_views, name='hk_user_last_views'),
        path('votes', accounts.votes, name='hk_user_votes'),
        path('subscriptions', accounts.subscriptions,
            name='hk_user_subscriptions'),
    ])),

    # Users
    path('users/', users.users, name='hk_users_overview'),
    path('users/<str:user_id>/', accounts.public_profile, name='hk_public_user_profile'),
    path('users/<str:user_id>/posts', accounts.posts, name='hk_user_posts'),

    # List archives and overview
    re_path(r'^list/(?P<mlist_fqdn>[^/@]+@[^/@]+)/', include(list_patterns)),

    # Messages
    re_path(r'^list/(?P<mlist_fqdn>[^/@]+@[^/@]+)/message/'
        r'(?P<message_id_hash>\w+)/', include(message_patterns)),
    re_path(r'^list/(?P<mlist_fqdn>[^/@]+@[^/@]+)/message/new$',
        message.new_message, name='hk_message_new'),

    # Threads
    re_path(r'^list/(?P<mlist_fqdn>[^/@]+@[^/@]+)/thread/(?P<threadid>\w+)/',
        include(thread_patterns)),

    # Search
    path('search', search.search, name='hk_search'),

    # Categories and Tags
    path('categories/', categories.categories, name='hk_categories_overview'),
    path('tags/', tags.tags, name='hk_tags_overview'),

    # Mailman archiver API
    path('api/mailman/urls', mailman.urls, name='hk_mailman_urls'),
    path('api/mailman/archive', mailman.archive, name='hk_mailman_archive'),

    # REST API
    path('api/', include(api_patterns)),

    # Mailman 2.X compatibility
    re_path(r'^listinfo/?$', compat.summary),
    re_path(r'^listinfo/(?P<list_name>[^/]+)/?$', compat.summary),
    re_path(r'^pipermail/(?P<list_name>[^/]+)/?$', compat.summary),
    re_path(r'^pipermail/(?P<list_name>[^/]+)/(?P<year>\d\d\d\d)-(?P<month_name>\w+)/?$', compat.arch_month),
    re_path(r'^pipermail/(?P<list_name>[^/]+)/(?P<year>\d\d\d\d)-(?P<month_name>\w+)/(?P<summary_type>[a-z]+)\.html$', compat.arch_month),
    re_path(r'^pipermail/(?P<list_name>[^/]+)/(?P<year>\d\d\d\d)-(?P<month_name>\w+)\.txt.gz', compat.arch_month_mbox),
    #url(r'^pipermail/(?P<list_name>[^/]+)/(?P<year>\d\d\d\d)-(?P<month_name>\w+)/(?P<msg_num>\d+)\.html$', compat.message),
    re_path(r'^list/(?P<list_name>[^@]+)@[^/]+/(?P<year>\d\d\d\d)-(?P<month_name>\w+)/?$', compat.arch_month),
    #url(r'^list/(?P<list_name>[^@]+)@[^/]+/(?P<year>\d\d\d\d)-(?P<month_name>\w+)/(?P<msg_num>\d+)\.html$', compat.message),

    # URL compatibility with previous versions
    re_path(r'^list/(?P<list_id>[^@/]+)/', compat.redirect_list_id),
    path('lists/', compat.redirect_lists),

]
#) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += staticfiles_urlpatterns()
