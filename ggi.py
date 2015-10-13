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
from modules.Packages import packageInPkgdb
from modules.Utils import FormatedPrint
from modules.ImportPath import ImportPath
from modules.ImportPathsDecomposer import ImportPathsDecomposer
from modules.GoSymbolsExtractor import GoSymbolsExtractor
from modules.Config import Config

def show_main(occurrences):
	not_just_main = False
	main_pkgs = []
	for occurrence in occurrences:
		parts = occurrence.split(":")
		if len(parts) != 2:
			continue

		if parts[1] != "main":
			not_just_main = True
		else:
			main_pkgs.append(occurrence)

	if not main_pkgs:
		return ""

	if not_just_main:
		return "+(%s)" % ", ".join(main_pkgs)
	else:
		return "(%s)" % ", ".join(main_pkgs)

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

	parser.add_option(
            "", "", "--spec", dest="spec", action = "store_true", default = False,
            help = "Display import path for spec file"
        )

	parser.add_option(
            "", "-r", "--requires", dest="requires", action = "store_true", default = False,
            help = "Use Requires instead of BuildRequires. Used only with --spec option."
        )

	parser.add_option(
            "", "", "--skip-errors", dest="skiperrors", action = "store_true", default = False,
            help = "Skip all errors during Go symbol parsing"
        )

	parser.add_option(
            "", "", "--importpath", dest="importpath", default = "",
            help = "Don't display class belonging to IMPORTPATH prefix"
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
            "", "", "--all-occurrences", dest="alloccurrences", action = "store_true", default = False,
            help = "List imported paths in all packages including main. Default is skip main packages."
        )

	parser.add_option(
            "", "", "--show-occurrence", dest="showoccurrence", action = "store_true", default = False,
            help = "Show occurence of import paths."
        )

	parser.add_option(
            "", "", "--show-main", dest="showmain", action = "store_true", default = False,
            help = "Show occurence of import paths in main packages only (+means not just main)."
        )

	options, args = parser.parse_args()

	path = "."
	if len(args):
		path = args[0]

	fmt_obj = FormatedPrint()

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

	gse_obj = GoSymbolsExtractor(path, imports_only=True, skip_errors=options.skiperrors, noGodeps=noGodeps)
	if not gse_obj.extract():
		fmt_obj.printError(gse_obj.getError())
		exit(1)

	package_imports_occurence = gse_obj.getPackageImportsOccurences()

	ip_used = gse_obj.getImportedPackages()
	ipd = ImportPathsDecomposer(ip_used)
	if not ipd.decompose():
		fmt_obj.printError(ipd.getError())
		exit(1)

	warn = ipd.getWarning()
	if warn != "":
		fmt_obj.printWarning("Warning: %s" % warn)

	classes = ipd.getClasses()
	sorted_classes = sorted(classes.keys())

	# get max length of all imports
	max_len = 0
	for element in sorted_classes:
		if element == "Native":
			continue

		# class name starts with prefix => filter out
		if options.importpath != "" and element.startswith(options.importpath):
			continue

		gimports = []
		for gimport in classes[element]:
			if options.importpath != "" and gimport.startswith(options.importpath):
				continue
			gimports.append(gimport)

		for gimport in gimports:
			if options.showmain:
				main_occ = show_main(package_imports_occurence[gimport])
				if main_occ == "":
					continue

			import_len = len(gimport)
			if import_len > max_len:
				max_len = import_len

	if options.spec and options.showoccurrence:
		print "# THIS IS NOT A VALID SPEC FORMAT"
		print "# COMMENTS HAS TO BE STARTED AT THE BEGGINING OF A LINE"


	for element in sorted_classes:
		if not options.all and element == "Native":
			continue

		if not options.alloccurrences:
			one_class = []
			for gimport in classes[element]:
				# does it occur only in main package?
				# remove it from classes[element]
				skip = True
				if gimport in package_imports_occurence:
					for occurrence in package_imports_occurence[gimport]:
						if not occurrence.endswith(":main"):
							skip = False
							break
				if skip:
					continue

				one_class.append(gimport)

			classes[element] = sorted(one_class)

		# class name starts with prefix => filter out
		if options.importpath != "" and element.startswith(options.importpath):
			continue

		# filter out all members of a class prefixed by prefix
		gimports = []
		for gimport in classes[element]:
			if options.importpath != "" and gimport.startswith(options.importpath):
				continue
			gimports.append(gimport)

		if gimports == []:
			continue

		if options.classes:
			# Native class is just printed
			if options.all and element == "Native":
				# does not make sense to check Native class in PkgDB
				if options.pkgdb:
					continue
				print "Class: %s" % element
				if not options.short:
					for gimport in gimports:
						if options.showoccurrence:
							if options.showmain:
								main_occ = show_main(package_imports_occurence[gimport])
								if main_occ != "":
									print "\t%s %s" % (gimport, main_occ)
							else:
								print "\t%s (%s)" % (gimport, ", ".join(package_imports_occurence[gimport]))
						else:
							print "\t%s" % gimport
				continue

			# Translate non-native class into package name (if -d option)
			if options.pkgdb:
				ip_obj = ImportPath(element)
				if not ip_obj.parse():
					fmt_obj.printWarning("Unable to translate %s to package name" % element)
					continue

				pkg_name = ip_obj.getPackageName()
				if pkg_name == "":
					fmt_obj.printWarning(ip_obj.getError())

				pkg_in_pkgdb = packageInPkgdb(pkg_name)
				if pkg_in_pkgdb:
					if options.verbose:
						print (GREEN + "Class: %s (%s) PkgDB=%s" + ENDC) % (element, pkg_name, pkg_in_pkgdb)
				else:
					print (RED + "Class: %s (%s) PkgDB=%s" + ENDC ) % (element, pkg_name, pkg_in_pkgdb)
				continue

			# Print class
			print "Class: %s" % element
			if not options.short:
				for gimport in sorted(gimports):
					if options.showoccurrence:
						if options.showmain:
							main_occ = show_main(package_imports_occurence[gimport])
							if main_occ != "":
								print "\t%s %s" % (gimport, main_occ)
						else:
							print "\t%s (%s)" % (gimport, ", ".join(package_imports_occurence[gimport]))
					else:
						print "\t%s" % gimport
			continue

		# Spec file BR
		if options.spec:
			for gimport in sorted(classes[element]):
				if options.requires:
					if options.showoccurrence:
						import_len = len(gimport)
						print "Requires: golang(%s) %s# %s" % (gimport, (max_len - import_len)*" ", ", ".join(package_imports_occurence[gimport]))
					else:
						print "Requires: golang(%s)" % gimport
				else:
					if options.showoccurrence:
						import_len = len(gimport)
						print "BuildRequires: golang(%s) %s# %s" % (gimport, (max_len - import_len)*" ", ", ".join(package_imports_occurence[gimport]))
					else:
						print "BuildRequires: golang(%s)" % gimport
			continue

		# Just a list of all import paths
		for gimport in sorted(classes[element]):
			if options.showoccurrence:
				import_len = len(gimport)
				if options.showmain:
					main_occ = show_main(package_imports_occurence[gimport])
					if main_occ != "":
						print "\t%s %s %s" % (gimport, (max_len - import_len)*" ", main_occ)
				else:
					print "\t%s %s(%s)" % (gimport, (max_len - import_len)*" ", ", ".join(package_imports_occurence[gimport]))
			else:
				print "\t%s" % gimport

