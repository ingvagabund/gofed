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
from xml.dom import minidom
from xml.dom.minidom import Node
import optparse
import ConfigParser

script_dir = os.path.dirname(os.path.realpath(__file__))

ERR_NO_ERROR = 0
ERR_NO_BRANCHES = 1
ERR_NOT_BRANCH = 2
ERR_NOT_NAME_OR_BUILDS = 3
ERR_NOT_BUILD = 4
ERR_NOT_BUILD_TAGS = 5

RED = '\033[91m'
GREEN = '\033[92m'
BLUE = '\033[94m'
CYAN = '\033[96m'
WHITE = '\033[97m'
YELLOW = '\033[93m'
MAGENTA = '\033[95m'
GREY = '\033[90m'
BLACK = '\033[90m'
DEFAULT = '\033[99m'
ENDC = '\033[0m'

def printErr(err):
	print "Error: %d" % err

class Implicit:
	config = None
	sections = {}

	def __init__(self):
		self.config = ConfigParser.ConfigParser()
		self.config.read("%s/data/golang.implicit" % script_dir)

	def getOptions(self, name, distro):
		key = "%s:%s" % (name, distro)
		if key in self.sections:
			return self.config.options(self.sections[key])

		if name in self.config.sections():
			self.sections[key] = name
			return self.config.options(name)
		elif key in self.config.sections():
			self.sections[key] = key
			return self.config.options("%s:%s" % (name, distro))
		else:
			return None

	def getProperty(self, name, distro, key):
		options = self.getOptions(name, distro)
		if options == None:
			return ""
		elif key in options:
			return self.config.get(self.sections["%s:%s" % (name, distro)], key)
		else:
			return ""

def getLeafTagData(tag):
	for item in tag.childNodes:
		if item.nodeType == Node.TEXT_NODE:
			return item.data
	return ""

def inspectBuild(build, implicit):
	b_name = ""
	b_missing = []
	b_super = []
	b_exec = []
	clean = True
	exec_only = False
	for item in build.childNodes:
		if item.nodeType != Node.ELEMENT_NODE:
			continue

		if item.tagName == "name":
			b_name = getLeafTagData(item)
		elif item.tagName == "missing_provides":
			b_missing = getLeafTagData(item)
			if b_missing != "":
				b_missing = b_missing.split(',')
			else:
				b_missing = []
		elif item.tagName == "superfluous_provides":
			b_super = getLeafTagData(item)
			if b_super != "":
				b_super = b_super.split(',')
			else:
				b_super = []
		elif item.tagName == "executables":
			b_exec = getLeafTagData(item)
			if b_exec != "":
				b_exec = b_exec.split(',')
			else:
				b_exec = []

		else:
			return {}, ERR_NOT_BUILD_TAGS

	# distro is surrounded by a dot, it is the third element from the right
	p_distro = b_name.split('.')[-3]
	# N-V-R
	p_name = '-'.join(b_name.split('-')[:-2])

	# filter missing
	impl = implicit.getProperty(p_name, p_distro, 'missing')
	if impl != "":
		impl = map(lambda x: x.strip(), impl.split(','))
		b_missing = filter(lambda x: x not in impl, b_missing)

	# filter super
	impl = implicit.getProperty(p_name, p_distro, 'super')
	if impl != "":
		impl = map(lambda x: x.strip(), impl.split(','))
		b_super = filter(lambda x: x not in impl, b_super)

	if b_exec:
		exec_only = True

	if b_missing or b_super or b_exec:
		clean = False
		exec_only = False

	return {
		"name": b_name,
		"missing": b_missing,
		"super": b_super,
		"exec": b_exec,
		"clean": clean,
		"exec_only": exec_only,
	}, ERR_NO_ERROR

def inspectBuilds(buildsElm, implicit):
	builds = []
	for build in buildsElm.childNodes:
		if build.nodeType != Node.ELEMENT_NODE:
			continue

		if build.tagName != "build":
			return [], ERR_NOT_BUILD
	
		b_info, err = inspectBuild(build, implicit)
		if err != ERR_NO_ERROR:
			printErr(err)
		else:
			builds.append(b_info)

	return builds

def inspectBranch(branch, implicit):
	b_name = ""
	b_builds = []

	if branch.tagName != "branch":
		return [], ERR_NOT_BRANCH

	for b_node in branch.childNodes:
		# <name> and <builds> tag
		if b_node.nodeType == Node.ELEMENT_NODE:
			if b_node.tagName == "name":
				for item in b_node.childNodes:
					if item.nodeType == Node.TEXT_NODE:
						b_name = item.data
			elif b_node.tagName == 'builds':
				b_builds = b_node
			else:
				return [], ERR_NOT_NAME_OR_BUILDS
	return {
		'name': b_name,
		'builds': inspectBuilds(b_builds, implicit)
	}, ERR_NO_ERROR

def showList(lst):
	for item in lst:
		print "\t" + item

def interpretScan(branches, short = True):
	for branch in branches:
		print 10*'=' + 'branch: ' + branch['name'] + 10*'='
		for build in branch['builds']:
			if short and build['clean']:
				continue

			print 'build: %s' % build['name']
			if build['exec']:
				print 'Executables:'
				showList(build['exec'])
			if build['super']:
				print 'Incorrect provides:'
				showList(build['super'])
			if build['missing']:
				print 'Missing provides:'
				showList(build['missing'])
		print ""

def sumarizeScan(branches, exclude_exec = True):
	counter = {}
	for branch in branches:
		counter[branch['name']] = 0
		cnt = 0
		for build in branch['builds']:
			if build['clean']:
				continue

			if not exclude_exec and build['exec']:
				cnt = cnt + len(build['exec'])
			if build['super']:
				cnt = cnt + len(build['super'])
			if build['missing']:
				cnt = cnt + len(build['missing'])
		counter[branch['name']] = counter[branch['name']] + cnt

	return counter

def analyzeResults(branchesElm):
	branches = []

	implicit = Implicit()

	for branchElm in branchesElm:
		if branchElm.nodeType == Node.ELEMENT_NODE:
			branch, err = inspectBranch(branchElm, implicit)
			if err != ERR_NO_ERROR:
				 printErr(err)
			else:
				branches.append(branch)
	return branches


if __name__ == "__main__":
	parser = optparse.OptionParser("%prog [-e] [-d] file [file [file ...]]")

        parser.add_option_group( optparse.OptionGroup(parser, "file", "Xml file with scanned results") )

	parser.add_option(
	    "", "-d", "--detail", dest="detail", action = "store_true", default = False,
	    help = "Display more information about affected branches"
	)

	parser.add_option(
	    "", "-e", "--executable", dest="executables", action = "store_true", default = False,
	    help = "Include executables in summary"
	)

	options, args = parser.parse_args()

	if len(args) < 1:
		print "Usage: %prog file.xml"
		exit(0)

	output = []
	for xmlfile in args:
		xmldoc = minidom.parse(xmlfile)

		brchs_elm = xmldoc.getElementsByTagName('branches')
		if len(brchs_elm) == 0:
			if len(args) == 1:
				exit(ERR_NO_BRANCHES)
			else:
				continue

		pkg_name = getLeafTagData(xmldoc.getElementsByTagName('name')[0])
		branches = analyzeResults(brchs_elm[0].childNodes)

		if options.detail:
			interpretScan(branches)
		else:
			summary = sumarizeScan(branches, not options.executables)
			info = []
			for br in summary:
				if summary[br] > 0:
					info.append(br + " (%s%d%s)" % (RED, summary[br], ENDC))
				else:
					info.append(br + " (%d)" % summary[br])

			output.append((pkg_name, ', '.join(info)))

	m_len = 0
	for pkg_name, info in output:
		m_len = max(m_len, len(pkg_name))

	for pkg_name, info in output:
		spacer = m_len - len(pkg_name)
		print "%s%s%s%s %s" % (BLUE, pkg_name, ENDC, spacer * " ", info)

	exit(0)
