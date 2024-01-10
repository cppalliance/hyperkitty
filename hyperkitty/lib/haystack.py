# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 by the Free Software Foundation, Inc.
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

"""This module contains Django-haystack backend for SQLlite3."""

from haystack.backends import (
    BaseEngine, BaseSearchBackend, BaseSearchQuery, log_query)


class SqliteSearchBackend(BaseSearchBackend):

    def update(self, index, iterable, commit=True):
        return super().update(index, iterable, commit)

    def remove(self, obj_or_string):
        return super().remove(obj_or_string)

    def clear(self, models=None, commit=True):
        return super().clear(models, commit)

    @log_query
    def search(self, query_string, **kwargs):
        return super().search(query_string, **kwargs)

    def prep_value(self, value):
        return super().prep_value(value)

    def more_like_this(
            self,
            model_instance,
            additional_query_string=None,
            result_class=None
    ):
        return super().more_like_this(
            model_instance, additional_query_string, result_class)


class SqliteSearchQuery(BaseSearchQuery):

    def build_query(self):
        return super().build_query()


class SqliteEngine(BaseEngine):

    backend = SqliteSearchBackend
    query = SqliteSearchQuery
