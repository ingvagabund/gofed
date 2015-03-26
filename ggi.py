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

import sys
import re
import os
import urllib2
import optparse
from subprocess import Popen, PIPE
from modules.Utils import GREEN, RED, ENDC
from modules.ImportPaths import getFileTreeImports, getNativeImports
from modules.Repos import getMappings
from modules.ImportPaths import decomposeImports
from modules.Packages import packageInPkgdb
from modules.Repos import repo2pkgName

if __name__ == "__main__":
	parser = optparse.OptionParser("%prog [-a] [-c] [-d [-v]] [directory]")

	parser.add_option_group( optparse.OptionGroup(parser, "directory", "Directory to inspect. If empty, current directory is used.") )

	parser.add_option(
	    "", "-a", "--all", dest="all", action = "store_true", default = False,
	    help = "Display all imports including golang native"
	)

	parser.add_option(
            "", "-c", "--classes", dest="classes", action = "store_true", default = False,
            help = "Decompose imports into classes"
        )

	parser.add_option(
            "", "-d", "--pkgdb", dest="pkgdb", action = "store_true", default = False,
            help = "Check if a class is in the PkgDB (only with -c option)"
        )

	parser.add_option(
            "", "-v", "--verbose", dest="verbose", action = "store_true", default = False,
            help = "Show all packages if -d option is on"
        )

	parser.add_option(
            "", "-s", "--short", dest="short", action = "store_true", default = False,
            help = "Display just classes without its imports"
        )

	options, args = parser.parse_args()

	path = "."
	if len(args):
		path = args[0]

	classes = decomposeImports(getFileTreeImports(path))
	sorted_classes = sorted(classes.keys())

	for element in sorted_classes:
		if not options.all and element == "Native":
			continue

		pkg_name = repo2pkgName(element)
		pkg_in_pkgdb = False

		if options.classes:
			if options.pkgdb and pkg_name != "":
				pkg_in_pkgdb = packageInPkgdb(pkg_name)
				if pkg_in_pkgdb:
					if options.verbose:
						print (GREEN + "Class: %s (%s) PkgDB=%s" + ENDC) % (element, pkg_name, pkg_in_pkgdb)
				else:
					print (RED + "Class: %s (%s) PkgDB=%s" + ENDC ) % (element, pkg_name, pkg_in_pkgdb)
			else:
				print "Class: %s" % element
		if not options.classes or not options.short:
			for gimport in classes[element]:
				print "\t%s" % gimport
			if options.classes:
				print ""

