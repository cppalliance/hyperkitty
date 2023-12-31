# -*- coding: utf-8 -*-
#
# Copyright (C) 2014-2023 by the Free Software Foundation, Inc.
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

from django.conf import settings
from django.db import models


class Tagging(models.Model):

    thread = models.ForeignKey("Thread", on_delete=models.CASCADE)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    tag = models.ForeignKey("Tag", on_delete=models.CASCADE)

    def __str__(self):
        return 'Tag %s on %s by %s' % (
            str(self.tag), str(self.thread), str(self.user))


class Tag(models.Model):

    name = models.CharField(max_length=255, db_index=True, unique=True)
    threads = models.ManyToManyField(
        "Thread", through="Tagging", related_name="tags")
    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, through="Tagging", related_name="tags")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return 'Tag %s' % self.name
