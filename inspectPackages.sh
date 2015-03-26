#!/bin/sh

# ####################################################################
# gofed - set of tools to automize packaging of golang devel codes
# Copyright (C) 2014  Jan Chaloupka, jchaloup@redhat.com
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
# ####################################################################

script_dir=$(realpath $(dirname $0))

# get packages names
packages=$(cat $script_dir/data/golang.packages)

# run scan
rm -f scan.log
for pkg_name in $packages; do
	echo "Scanning ${pkg_name}..."
	echo "Scanning ${pkg_name}..." >> scan.log
	python $script_dir/inspectpackage.py $pkg_name -o ${pkg_name}.xml >> scan.log
	if [ $? -eq 0 ]; then
		python $script_dir/xml2info.py ${pkg_name}.xml
	fi
	echo "" >> scan.log
done
