#! /bin/bash
# Copyright (C) 2022 by the Free Software Foundation, Inc.
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

# This script assumes that you have the 'fork' set as the 'origin'.

# This script will
# 0. Stash all the local changes.
# 1. Delete the update-po branch if it exists locally
# 2. create a new branch update-po
# 3. run the scripts/update-po.sh script.
# 4. Commit the changes made by the script
# 5. Push the branch to gitlab and create a merge request.
# 6. Go back to the previous branch.

set -x

# Stash anything in the current page.
git stash

# Force delete the update-po branch if it exists locally.
git branch -D update-po

# Fetch all remote changes.
git fetch upstream

# Create a new branch.
git checkout -b update-po upstream/master

# Run the update po command.
parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )
$parent_path/update-po.sh

# Add the files and comment.
git add hyperkitty/locale/*
git commit -m 'Update po files'
git push -o merge_request.create -o merge_request.remove_source_branch origin update-po

# Go back to the original directory and git branch.
git checkout -

