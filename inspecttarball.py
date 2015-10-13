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

import os
import sys
import optparse
from modules.GoSymbolsExtractor import GoSymbolsExtractor
from modules.Config import Config

if __name__ == "__main__":

	parser = optparse.OptionParser("%prog [-p] [-d] [-t] [directory]")

	parser.add_option_group( optparse.OptionGroup(parser, "directory", "Directory to inspect. If empty, current directory is used.") )

	parser.add_option(
	    "", "-p", "--provides", dest="provides", action = "store_true", default = False,
	    help = "Display all directories with *.go files"
	)

	parser.add_option(
	    "", "", "--prefix", dest="prefix", default = "",
	    help = "Prefix all provided import paths, used with -p option"
	)

	parser.add_option(
	    "", "-s", "--spec", dest="spec", action="store_true", default = False,
	    help = "If set with -p options, print list of provided paths in spec file format."
	)

	parser.add_option(
            "", "-d", "--dirs", dest="dirs", action = "store_true", default = False,
            help = "Display all direct directories"
        )

	parser.add_option(
	    "", "-t", "--test", dest="test", action = "store_true", default = False,
	    help = "Display all directories containing *.go test files"
	)

	parser.add_option(
            "", "", "--scan-all-dirs", dest="scanalldirs", action = "store_true", default = False,
            help = "Scan all dirs, including Godeps directory"
        )

	parser.add_option(
            "", "", "--skip-dirs", dest="skipdirs", default = "",
            help = "Scan all dirs except specified via SKIPDIRS. Directories are comma separated list."
        )

	parser.add_option(
            "", "", "--skip-errors", dest="skiperrors", action = "store_true", default = False,
            help = "Skip all errors during Go symbol parsing"
        )

	parser.add_option(
            "", "-m", "--main-packages", dest="mainpackages", action = "store_true", default = False,
            help = "Show main packages"
        )

	options, args = parser.parse_args()

	path = "."
	if len(args):
		path = args[0]

	if not options.scanalldirs:
		noGodeps = Config().getSkippedDirectories()
	else:
		noGodeps = []

	if options.skipdirs:
		for dir in options.skipdirs.split(','):
			dir = dir.strip()
			if dir == "":
				continue
			noGodeps.append(dir)

	gse_obj = GoSymbolsExtractor(path, noGodeps=noGodeps, skip_errors=options.skiperrors)
	if not gse_obj.extract():
		sys.stderr.write("%s\n" % gse_obj.getError())
		exit(1)

	if options.provides:
		ip = gse_obj.getSymbolsPosition()

		ips = []
		for pkg in ip:
			ips.append(ip[pkg])

		skipped_provides_with_prefix = Config().getSkippedProvidesWithPrefix()

		for ip in sorted(ips):
			skip = False
			for prefix in skipped_provides_with_prefix:
				if ip.startswith(prefix):
					skip = True
					break

			if skip:
				continue

			# skip all provided packages with /internal/ keyword
			if "internal" in ip.split("/"):
				continue

			if options.spec != False:
				if ip != ".":
					print "Provides: golang(%%{import_path}/%s) = %%{version}-%%{release}" % (ip)
				else:
					print "Provides: golang(%{import_path}) = %{version}-%{release}"
			elif options.prefix != "":
				if ip != ".":
					print "%s/%s" % (options.prefix, ip)
				else:
					print options.prefix
			else:
				print ip

	elif options.test:
		sdirs = sorted(gse_obj.getTestDirectories())
		for dir in sdirs:
			if options.spec != False:
				if dir != ".":
					print "go test %%{import_path}/%s" % dir
				else:
					print "go test %{import_path}"
			else:
				print dir
	elif options.dirs:
		dirs = gse_obj.getSymbolsPosition().values() + gse_obj.getTestDirectories()
		sdirs = []
		for dir in dirs:
			sdirs.append( dir.split("/")[0] )

		sdirs = sorted(list(set(sdirs)))
		for dir in sdirs:
			print dir
	elif options.mainpackages:
		for pkg in gse_obj.getMainPackages():
			print pkg
	else:
		print "Usage: prog [-p] [-d] [-t] [directory]"
