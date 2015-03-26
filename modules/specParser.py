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

###################################################################
# TODO:
# [  ] - detect more import paths/sources in spec file?
# [  ] - detect from %files every build, analyze its content (downloading it from koji by detecting its name
#        from spec file => no koji latest-builds, which packages/builds are no arch, which are arch specific (el6 beast)
# [  ] - all provides of source code import must in a form golang(import_path/...)
# [  ] - what files/provides are optional, which should not be in provides (test files, example, ...)
# [  ] - golang imports of examples are optional
###################################################################

from subprocess import PIPE
from subprocess import Popen
import sys
import os
import re
import optparse
import tempfile

import Utils
import Repos

from Utils import getScriptDir, runCommand

RPM_SCRIPTLETS = ('pre', 'post', 'preun', 'postun', 'pretrans', 'posttrans',
                  'trigger', 'triggerin', 'triggerprein', 'triggerun',
                  'triggerun', 'triggerpostun', 'verifyscript')

SECTIONS = ('build', 'changelog', 'check', 'clean', 'description', 'files',
               'install', 'package', 'prep') + RPM_SCRIPTLETS

script_dir = getScriptDir() + "/.."

GOLANG_IMPORT_PATHS="data/golang.import_paths"

class SpecInfo:

	def __init__(self, spec):
		self.spec = spec
		lines = self.getRawSpecLines(spec)
		plines = self.getSpecLines(spec)
		# read macros
		self.macros = self.readMacros(lines)
		# read some tags
		self.tags = self.parseTags(plines)

	def getMacro(self, name):
		if name not in self.macros:
			return ""
		else:
			value, ok = self.evalMacro(name, self.macros)
			if ok:
				return value
			else:
				return ""

	def getTag(self, name):
		if name not in self.tags:
			return ""
		else:
			return self.tags[name]

	def readMacros(self, spec_lines = []):
		macros = {}
		for line in spec_lines:
			line = line.strip()
			if line == '' or  line.startswith((' ', '\t', '#', '\n')):
				continue

			if line.startswith('%global'):
				line = re.sub(r'[ \t]+', ' ', line)
				# %global <name> <body>
				parts = line.split(' ')
				macros[parts[1]] = parts[2]
				continue
		return macros

	def reevalMacro(self, old_value, macros):
		value = ''
		# what macros are inside? %{...} or %...
		# no macro in macro use
		key = ''
		mfound = False
		mbracket = False
		for c in old_value:
			if c == '%':
				key = ''
				mfound = True
				continue
			if mfound:
				if c == '{':
					if not mbracket:
						mbracket = True
						continue
					else:
						return '', False
				if re.match('[a-zA-Z_]', c):
					key += c
				else:
					if key not in macros:
						return '', False
					value += macros[key]
					if not mbracket:
						mfound = False
						value += c
						continue
					if c != '}':
						return '', False
					mbracket = False
					mfound = False
			else:
				value += c
		return value, True

	def evalMacro(self, name, macros):

		if name not in macros:
			return "", False	
		value = ""

		evalue, rc = self.reevalMacro(macros[name], macros)
		if rc == False:
			return '', False

		while evalue != value:
			value = evalue
			evalue, rc = self.reevalMacro(value, macros)
			if rc == False:
				return '', False

		return value, True

	def parseTags(self, spec_lines = []):
		tags = {}
		for line in spec_lines:
			line = re.sub(r'[ \t]+', ' ', line.strip())
			if line.upper().startswith('URL'):
				tags['url'] = line.split(' ')[1]
				continue
			if line.upper().startswith('NAME'):
				tags['name'] = line.split(' ')[1]
				continue
			if line.upper().startswith('SOURCE'):
				src = line[6:].strip()
				# now number or : follows
				if src[0] == ':':
					tags['source0'] = src[1:].strip()
				else:
					items = src.split(':')
					tags['source%s' % items[0].strip()] = ':'.join(items[1:]).strip()
		return tags

	def getRawSpecLines(self, spec):
		with open(spec, 'r') as file:
			return file.read().split('\n')

	def getSpecLines(self, spec):
		stdout, stderr, rt = Utils.runCommand('rpmspec -P %s' % spec)
		if rt != 0:
			return []
		return stdout.split('\n')

	def getProvidesFromPackageSections(self, spec, pkg_name):
		stdout, stderr, rc = Utils.runCommand('rpmspec -P %s' % spec)
		if rc != 0:
			return []

		provides = {}
		in_package = False
		p_name = ''
		skip = False

		for line in stdout.split('\n'):
			if line == '':
				continue

			line = line.strip()
			for sec in SECTIONS:
				if line.lower().startswith("%%%s" % sec):
					if sec == 'package':
						in_package = True
						line = re.sub(r'[ \t]+', ' ', line)
						items = line.split(' ')
						items_len = len(items)
						i = 1
						while i < items_len:
							item = items[i]
							i += 1
							if item.startswith('-n'):
								p_name = items[i]
								break
							if item[0] == '-':
								continue
							p_name = '%s-%s' % (pkg_name, item)
							break

						provides[p_name] = []
						skip = True
					else:
						in_package = False
					break
			if skip:
				skip = False
				continue

			if in_package:
				if line.startswith('Provides'):
					line = re.sub(r'[ \t]+', ' ', line)
					provides[p_name].append(line.split(' ')[1])

		return provides

def fetchProvides(pkg, branch):
	"""Fetch a spec file from pkgdb and get provides from all its [sub]packages

	Keyword arguments:
	pkg -- package name
	branch -- branch name
	"""
	f = tempfile.NamedTemporaryFile(delete=True)
	runCommand("curl http://pkgs.fedoraproject.org/cgit/%s.git/plain/%s.spec > %s" % (pkg, pkg, f.name))
	provides = SpecInfo(f.name).getProvidesFromPackageSections(f.name, pkg)
	f.close()
	return provides


def getBuildsFromFilesSections(spec, pkg_name):
	stdout, stderr, rc = Utils.runCommand('rpmspec -P %s | grep "^%%files"' % spec)
	if rc != 0:
		return []

	builds = []
	for line in stdout.split('\n'):
		if line != '':
			line = re.sub(r'[ \t]+', ' ', line)
			n_option = False
			n_value = ''
			name = ''
			items = line.split(' ')
			items_len = len(items)
			i = 1
			while i < items_len:
				item = items[i]
				i += 1
				# -n new_name
				if item == '-n':
					n_option = True
					n_value = items[i]
					#i += 1
					#continue
					break
				# -f file read list of files from file. We can skip this option.
				if item == '-f':
					i += 1
					continue
				# skip remaining options of any
				if item[0] == '-':
					continue
				# the non-option item is package's name
				name = item

			if n_option:
				builds.append(n_value)
			else:
				builds.append("%s-%s" % (pkg_name, name))

	return builds

def loadImportPaths():
	lines = []
	with open('%s/%s' % (script_dir, GOLANG_IMPORT_PATHS), 'r') as file:
		lines = file.read().split('\n')

	import_paths = {}
	for line in lines:
		parts = line.split(':')
		if len(parts) != 2:
			continue

		import_paths[parts[0]] = []
		field = parts[1].split(',')
		for item in field:
			import_paths[parts[0]].append(item.strip())

	return import_paths

def loadSubpackageSourceMapping():
	lines = []
	with open('%s/%s' % (script_dir, GOLANG_IMPORT_PATHS), 'r') as file:
		lines = file.read().split('\n')

	sources = {}
	for line in lines:
		parts = line.split(':')
		if len(parts) != 2:
			continue

		sources[parts[0]] = []
		field = parts[1].split(',')
		for item in field:
			sources[parts[0]].append(item.strip())

	return sources

def getTarballDirs(prefix, fullpath_files, test = False):
	go_dirs = []
	for fname in fullpath_files:
		# does the dirName contains *.go files
		# find any *.go file
		if test == False:
			if not fname.endswith(".go"):
				continue
		else:
			if not fname.endswith("_test.go"):
				continue

		dir = '/'.join(fname.split('/')[1:-1])
		if dir not in go_dirs:
			go_dirs.append(dir)

	return go_dirs

def getTarballImports(tarball):
	# only to compare provides from tarball
	# executables are handled separatelly from individual builds
	stdout, stderr, rc = Utils.runCommand('tar -tf %s | sort' % tarball)
	if rc != 0:
		return []

	# provides are test = False
	dirs = getTarballDirs('', stdout.split('\n'))
	return dirs

def fetchPkgInfo(pkg, branch):
	"""Fetch a spec file from pkgdb and get its commit

	Keyword arguments:
	pkg -- package name
	branch -- branch name
	"""
	f = tempfile.NamedTemporaryFile(delete=True)
	Utils.runCommand("curl http://pkgs.fedoraproject.org/cgit/%s.git/plain/%s.spec > %s" % (pkg, pkg, f.name))
	spec_info = SpecInfo(f.name)
	info = {}
	commit = spec_info.getMacro('commit')
	if commit == "":
		commit = spec_info.getMacro('rev')

	info["commit"] = commit
	info["url"] = spec_info.getTag("url")

	f.close()
	return info

def getPackageCommits(pkg):
	info = fetchPkgInfo(pkg, 'master')
	return info["commit"] 

def getPkgURL(pkg, branch = "master"):
	info = fetchPkgInfo(pkg, 'master')
	return info["url"] 



class SpecTest:

	def __init__(self, spec):
		self.spec = spec
		self.spec_info = SpecInfo(spec)
		url = self.spec_info.getTag("url")
		self.name = self.spec_info.getTag("name")
		self.import_path = self.spec_info.getMacro("import_path")

		self.repo, self.url = Repos.detectKnownRepos(url)
		self.import_paths = {}

		if self.import_path != "":
			self.import_paths['%s-devel' % (self.name)] = self.import_path

##################################
# TESTS
##################################
	def testImportPath(self, verbose = False):
		if self.import_path == "":
			print "E: missing %global import_path ..."
			return 1
		if verbose:
			print "import_path detected: %s" % self.import_path
		return 0

	def testPackageName(self, verbose = False):
		pkg_name = ''
		if self.repo == Repos.GITHUB:
			pkg_name = Repos.github2pkgdb(self.url)
		elif self.repo == Repos.GOOGLECODE:
			pkg_name = Repos.googlecode2pkgdb(self.url)
		elif self.repo == Repos.GOLANGORG:
			pkg_name = Repos.golangorg2pkgdb(self.url)
	#	elif self.repo == Repos.GOPKG:
	#		pkg_name = Repos.gopkg2pkgdb(url)

		if pkg_name == '':
			if verbose:
				print 'Uknown repo url'
			return 0

		if pkg_name != self.name:
			print "W: Incorrect package name, should be %s" % pkg_name
			return 1
		if verbose:
			print "Correct package name: %s" % pkg_name

		return 0

	def testCommit(self, verbose = False):
		commit_label = 'commit'
		commit = self.spec_info.getMacro(commit_label)
		if commit == "":
			commit_label = 'rev'
			commit = self.spec_info.getMacro(commit_label)

		if commit == "":
			print "E: missing %%global %s ..." % commit_label
			return 1
		if verbose:
			print "%s detected: %s" % (commit_label, commit)
		return 0

	def testProvides(self, builds, provides, verbose = False):
		errors = 0
		# here filter only devel subpackages
		for key in provides:
			if key not in builds:
				if verbose:
					print "Skipping %s, not in builds" % key
				continue

			if not key.endswith('devel'):
				if verbose:
					print "Skipping %s, name does not end with devel sufix" % key
				continue

			if verbose:
				print "Checking Provides of %s package:" % key
			ip = []
			if key in self.import_paths:
				ip = [self.import_paths[key]]
			elif key in self.local_ips:
				if verbose:
					print "Taking import path from golang.import_paths"
				ip = self.local_ips[key]
			elif verbose:
				print "Import path for this package unknown"
		
			for provide in provides[key]:
				if not provide.startswith('golang('):
					print "E: Provides does not start with golang(: %s" % provide
					errors += 1
					continue
				if provide[-1] != ')':
					print "E: Provides does not end with ): %s" % provide
					errors += 1
					continue
				if ip != []:
					found = False
					for path in ip:
						if provide[7:-1].startswith(path):
							found = True
							break

					if not found:
						print "E: Provides does not start with any of import paths %s: %s" % (', '.join(ip), provide)
						errors += 1
						continue
				if verbose:
					print "Provides %s in a correct form" % provide
		return errors

	def testBuilds(self, verbose = False):
		errors = 0
		warning = 0
		pkg_name = self.name
		builds = getBuildsFromFilesSections(self.spec, pkg_name)

		self.local_ips = loadImportPaths()
		# tarball lies with a spec file in a branch (from sources the first one?)
		source_mappings = loadSubpackageSourceMapping()
		# get sources from a spec
		source0 = self.spec_info.getTag("source0")
		if source0 == "":
			print "Source or Source0 tag missing in spec file"
			return 1, 0

		spec_source0 = source0.split('/')[-1]
		# get source file imports from tarball
		tar_imports = getTarballImports(spec_source0)

		provides = SpecInfo(self.spec).getProvidesFromPackageSections(self.spec, pkg_name)
		# test form of provides
		errors += self.testProvides(builds, provides)

		# compare provides
		for build in builds:
			if build not in provides:
				continue

			ip = ''
			if build in self.import_paths:
				ip = [self.import_paths[build]]
			elif build in self.local_ips:
				ip = self.local_ips[build]
			else:
				continue

			ip_provides = []
			for path in ip:
				for ti in tar_imports:
					if ti != '':
						ip_provides.append('golang(%s/%s)' % (path, ti))
					else:
						ip_provides.append('golang(%s)' % path)

			missing = list(set(ip_provides) - set(provides[build]))
			superfluous = list(set(provides[build]) - set(ip_provides))
			for value in missing:
				print 'W: %s: missing Provides: %s' % (build, value)
				warning += 1

			for value in superfluous:
				print 'W: %s: superfluous Provides: %s' % (build, value)
				warning += 1

		return errors, warning

##################################
# MAIN
##################################
if __name__ == '__main__':

	parser = optparse.OptionParser("%prog [-v] [-r ROOT] specfile")

#        parser.add_option_group( optparse.OptionGroup(parser, "file", "Xml file with scanned results") )

	parser.add_option(
	    "", "-v", "--verbose", dest="verbose", action = "store_true", default = False,
	    help = "Display more information"
	)

	parser.add_option(
	    "", "-r", "--root", dest="root", default = '.',
	    help = "Set root directory (directory containing spec file and tarball)"
	)

	options, args = parser.parse_args()

	if len(args) != 1:
		print "Synopis: prog [-v] [-r ROOT] specfile"
		exit(1)

	if options.root != '.':
		os.chdir(options.root)

	# test if spec file exists

	errors = 0
	warnings = 0
	verbose = options.verbose
	spec = args[0]
	specTestObj = SpecTest(spec)
	#########
	# TESTS #
	#########

	# 1. check package name
	warnings += specTestObj.testPackageName(verbose)
	# 2. check for %global import_path ...
	errors += specTestObj.testImportPath(verbose)
	# 3. check for %global commit ... #
	errors += specTestObj.testCommit(verbose)
	# 4. check Provides of every devel subpackage
	err, war = specTestObj.testBuilds(verbose)
	errors += err
	warnings += war

	###########
	# Summary #
	###########
	print "%s specfiles checked; %s errors, %s warnings." % (1, errors, warnings)

