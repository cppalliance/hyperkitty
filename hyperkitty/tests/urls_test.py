# -*- coding: utf-8 -*-
#
# Copyright (C) 2012-2022 by the Free Software Foundation, Inc.
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

"""
This file is the main URL config for a Django website including HyperKitty.
"""

from django.conf.urls import include
from django.urls import path


urlpatterns = [
    path('', include('hyperkitty.urls')),
    path('', include('django_mailman3.urls')),
    path('accounts/', include('allauth.urls')),
]
