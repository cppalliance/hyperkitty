# -*- coding: utf-8 -*-
#
# Copyright (C) 2018-2023 by the Free Software Foundation, Inc.
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

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.http import urlencode

from hyperkitty import models


admin.site.register(models.profile.Profile)
admin.site.register(models.tag.Tag)
admin.site.register(models.vote.Vote)
admin.site.register(models.thread.LastView)
admin.site.register(models.favorite.Favorite)


@admin.register(models.email.Email)
class EmailAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'date', 'subject', 'mailinglist')
    list_filter = ('sender', 'mailinglist__list_id', 'thread_id')
    search_fields = ('subject', 'sender__address')


@admin.register(models.thread.Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ('id', 'mailinglist', 'subject', 'date_active', 'emails')
    search_fields = ('subject', 'mailinglist__name', 'mailinglist__list_id')
    list_filter = ('mailinglist__list_id', )

    def emails(self, obj):
        count = obj.emails.count()
        url = (
            reverse("admin:hyperkitty_email_changelist")
            + "?"
            + urlencode({"thread__id": f"{obj.id}"})
        )
        return format_html('<a href="{}">{} Emails</a>', url, count)


@admin.register(models.mailinglist.MailingList)
class MailingListAdmin(admin.ModelAdmin):
    list_display = ('name', 'list_id', 'threads', 'emails')
    search_fields = ('name', 'list_id')

    def threads(self, obj):
        count = obj.threads.count()
        url = (
            reverse("admin:hyperkitty_thread_changelist")
            + "?"
            + urlencode({"mailinglist__id": f"{obj.id}"})
        )
        return format_html('<a href="{}">{} Threads</a>', url, count)

    def emails(self, obj):
        count = obj.emails.count()
        url = (
            reverse("admin:hyperkitty_email_changelist")
            + "?"
            + urlencode({"mailinglist__id": f"{obj.id}"})
        )
        return format_html('<a href="{}">{} Emails</a>', url, count)


@admin.register(models.category.ThreadCategory)
class ThreadCategoryAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        obj.name = obj.name.lower()
        return super(ThreadCategoryAdmin, self).save_model(
                     request, obj, form, change)
