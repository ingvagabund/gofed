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

from subprocess import PIPE
from subprocess import Popen

import os
import optparse

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

script_dir = os.path.dirname(os.path.realpath(__file__))

# golang(github.com/vishvananda/netlink)
# golang(%{import_path})
def getImportPath(raw_p, macro_p):
	if raw_p[:7] != "golang(":
		return ""

	if macro_p[:7] != "golang(":
		return ""

	raw_p = raw_p[7:]
	macro_p = macro_p[7:]

	r_l = len(raw_p) - 1
	m_l = len(macro_p) - 1

	while r_l > 0 and m_l > 0:
		if raw_p[r_l] == macro_p[m_l]:
			r_l = r_l - 1
			m_l = m_l - 1
		else:
			break

	return raw_p[:r_l+1]

def err(msg):
	print RED + msg + ENDC

def warning(msg):
	print BLUE + msg + ENDC

def debug(msg):
	print WHITE + msg + ENDC

def info(msg):
	print GREEN + msg + ENDC


def step(msg):
	print "%s%s %s%s" % (YELLOW, step.s_counter, msg, ENDC)
	step.s_counter = step.s_counter + 1
step.s_counter = 1

a = "golang(github.com/vishvananda/netlink)"
b = "golang(%{import_path})"

#print getImportPath(a, b)


# devel build: missing/superfluous provides, list of executables
# other buils: list of executables
# 
#
#
class Build:
	name = ""
	missing_provides = []
	super_provides = []
	executables = []

	def __init__(self, name):
		self.name = name

	def addMissingProvides(self, provides):
		self.missing_provides = provides

	def addSuperProvides(self, provides):
		self.super_provides = provides

	def addExecutables(self, execs):
		self.executables = execs

	def __str__(self):
		repre = "Name: %s" % self.name
		repre = repre + "\nMissing provides: %s" % ",".join(self.missing_provides)
		repre = repre + "\nSuperfluous provides: %s" % ",".join(self.super_provides)
		repre = repre + "\nExecutables: %s" % ",".join(self.executables)
		return repre

	def toXml(self, tab = 1):
		xml = tab*'\t' + "<build>\n"
		xml += (tab+1)*'\t' + "<name>%s</name>\n" % self.name
		xml += (tab+1)*'\t' + "<missing_provides>%s</missing_provides>\n" % ",".join(self.missing_provides)
		xml += (tab+1)*'\t' + "<superfluous_provides>%s</superfluous_provides>\n" % ",".join(self.super_provides)
		xml += (tab+1)*'\t' + "<executables>%s</executables>\n" % ",".join(self.executables)
		xml += tab*'\t' + "</build>\n"
		return xml

class Branch:
	branch = ""
	devel = None
	others = []

	def __init__(self, branch):
		self.branch = branch
		self.others = []

	def addDevel(self, devel):
		self.devel = devel

	def addBuild(self, build):
		self.others.append(build)

	def __str__(self):
		repre = "Branch: %s" % self.branch
		if self.devel:
			repre = repre + "\n====devel====\n"
			repre = repre + str(self.devel)

		for build in self.others:
			repre = repre + "\n=============\n"
			repre = repre + str(build)

		return repre

	def toXml(self, tab = 1):
		xml = tab*'\t' + "<branch>\n"
		xml += (tab+1)*'\t' + "<name>%s</name>\n" % self.branch
		xml += (tab+1)*'\t' + "<builds>\n"
		if self.devel:
			xml += self.devel.toXml(tab+2)

		for build in self.others:
			xml += build.toXml(tab+2)

		xml += (tab+1)*'\t' + "</builds>\n"
		xml += tab*'\t' + "</branch>\n"
		return xml

class Package:

	name = ""
	branches = []

	def __init__(self, name):
		self.name = name

	def addBranch(self, branch):
		self.branches.append(branch)

	def __str__(self):
		repre = "Package: %s" % self.name

                for branch in self.branches:
                        repre = repre + "\n\n"
                        repre = repre + str(branch)

                return repre

	def toXml(self, tab = 1):
		xml = tab*'\t' + "<package>\n"
		xml += (tab+1)*'\t' + "<name>%s</name>\n" % self.name
		xml += (tab+1)*'\t' + "<branches>\n"

		for branch in self.branches:
			xml += branch.toXml(tab+2)

		xml += (tab+1)*'\t' + "</branches>\n"
		xml += tab*'\t' + "</package>\n"
		return xml


def runCommand(cmd):
	#cmd = cmd.split(' ')
	process = Popen(cmd, stderr=PIPE, stdout=PIPE, shell=True)
	rt = process.returncode
	stdout, stderr = process.communicate()
	return stdout, stderr, rt

def getBuildProvides(build):
	stdout, stderr, _ = runCommand("rpm -qp --provides %s | grep '^golang(' | cut -d' ' -f1 | sed 's/golang(//' | sed 's/)//' | sort -u" % build)
	return sorted(stdout.split('\n')[:-1])

def getTarballProvides(import_path, directory):
	stdout, stderr, _ = runCommand("%s/inspecttarball.py -p %s" % (script_dir, directory))
	return sorted(map(lambda p: import_path if p == '.' else import_path + "/" + p, stdout.split('\n')[:-1]))

# from http://stackoverflow.com/questions/377017/test-if-executable-exists-in-python
def is_exe(fpath):
	return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

def getBuildExecutable(build):
	executables = []
	stdout, stderr, _ = runCommand("mkdir -p unpackaged")
	if stderr != "":
                err("Unable to create unpackaged folder: %s" % stderr)
                return 1

	stdout, stderr, _ = runCommand("cp %s unpackaged/." % build)

	os.chdir("unpackaged")

	stdout, stderr, _ = runCommand("rpm2cpio %s | cpio -idmv" % build)
	for dirName, subdirList, fileList in os.walk('.'):
		for file in fileList:
			fullPath = dirName + '/' + file
			if is_exe(fullPath):
				executables.append(fullPath)
	os.chdir("..")
	stdout, stderr, _ = runCommand("rm -rf unpackaged")

	return executables


def checkProvides(pkg_name, devel):
	info("\tChecking build Provides:")
	bp = getBuildProvides(devel)

	stdout, stderr, _ = runCommand("rpmspec -P *.spec | grep Provides | grep golang | grep ')' | grep '(' | sed 's/[ \t][ \t]*/ /g' | cut -d' ' -f2 | head -1")
	subs_ip = stdout.split('\n')[0]

	stdout, stderr, _ = runCommand("grep '%{import_path}' *.spec | grep Provides | sed 's/[ \t][ \t]*/ /g' | cut -d' ' -f2 | head -1")
	raw_ip = stdout.split('\n')[0]

	ip = getImportPath(subs_ip, raw_ip)

	stdout, stderr, _ = runCommand("tar -tf $(cat sources | sed 's/[ \t][ \t]*/ /g' | cut -d' ' -f2) | cut -d '/' -f1 | head -1")

	directory = stdout.split('\n')[0]

	info("\tChecking tarball Provides:")

	tp = getTarballProvides(ip, directory)

	bp_missing = list(set(tp) - set(bp))
	bp_superf  = list(set(bp) - set(tp))

	return bp_missing, bp_superf

def inspectBranch(pkg_name, branch, distro):
	branch_obj = Branch(branch)

	step("Branch: %s" % branch)
	stdout, stderr, _ = runCommand("fedpkg switch-branch %s" % branch)
	if stderr != "":
		err("Unable to switch to %s: %s" % (branch, stderr))
		return None, 1

	stdout, stderr, _ = runCommand("fedpkg prep")
	if stderr != "":
		err("Unable to prep: %s" % stderr)
		return None, 1

	info("\tGetting builds from koji")
	stdout, stderr, _ = runCommand("koji latest-build %s %s --quiet" % (distro, pkg_name))
        if stderr != "":
                err("Unable to get latest-build: %s" % stderr)
                return None, 1

	build = stdout.split(' ')[0]
	if build == "GenericError:":
		err("Unable to get latest-build: %s" % stdout)
                return None, 1

	stdout, stderr, _ = runCommand("koji download-build %s" % build)
	# no test for stderr as the command writes to stderr

	devel = ""
	stdout, stderr, _ = runCommand("ls %s-devel-*.rpm" % pkg_name)
        if stderr != "":
                warning("No %s-devel package" % pkg_name)
	else:
		devel = stdout.split('\n')[0]

	if devel != "":
		build_obj = Build(devel)
       
		info("\tInspecting %s" % devel)
		mp, sp = checkProvides(pkg_name, devel)
		build_obj.addMissingProvides(mp)
		build_obj.addSuperProvides(sp)

		info("\tChecking %s for executable" % devel)
		executables = getBuildExecutable(devel)
		build_obj.addExecutables(executables)

		branch_obj.addDevel(build_obj)

	#	print build_obj.toXml()

	cmd = "ls *.rpm | grep -v '.src.rpm$'"
	if devel != "":
		cmd += " | grep -v %s" % devel

	stdout, stderr, _ = runCommand(cmd)
	others = stdout.split('\n')[:-1]
	if others:
		info("\tChecking other builds")
		for build in others:
			build_obj = Build(build)
			info("\tChecking %s for executable" % build)
			executables = getBuildExecutable(build)
			build_obj.addExecutables(executables)
			branch_obj.addBuild(build_obj)

	stdout, stderr, _ = runCommand("git clean -fd")

	return branch_obj, 0


def inspectPackage(pkg_name):

	cwd = os.getcwd()

	pkg_obj = Package(pkg_name)

	tmp_dir, stderr, _ = runCommand("mktemp -d")
	if stderr != "":
		err("Unable to create temp directory: %s" % stderr)
		return None

	tmp_dir = tmp_dir.split('\n')[0]
	os.chdir("%s" % tmp_dir)

	#err("Changing directory to %s" % tmp_dir)

	step("Cloning %s" % pkg_name)
	stdout, stderr, _ = runCommand("fedpkg clone %s" % pkg_name)
	if stderr != "":
		err("Unable to clone %s's repo: %s" % (pkg_name, stderr))
		return None

	os.chdir("%s" % pkg_name)

	for (branch, distro) in [('master', 'rawhide'), ('f21', 'f21'), ('f20', 'f20'), ('el6', 'dist-6E-epel-build')]:
		obj, er = inspectBranch(pkg_name, branch, distro)
		if er == 0 and obj:
			pkg_obj.addBranch(obj)

	runCommand("rm -rf %s" % tmp_dir)

	os.chdir(cwd)

	return pkg_obj


if __name__ == "__main__":

	parser = optparse.OptionParser("%prog [-o|--output FILE] pkg_name")

        parser.add_option(
		"", "-o", "--output", dest="output",
		help = "Output to xml file"
        )

	options, args = parser.parse_args()
	if len(args) != 1:
		print "Synopsis: %prog [-o|--output FILE] pkg_name"
		exit(1)

	pkg_obj = inspectPackage(args[0])
	if pkg_obj == None:
		exit(1)

	if options.output:
		with open(options.output, 'w') as file:
			file.write('<?xml version="1.0" encoding="utf-8" ?>\n')
			file.write(pkg_obj.toXml(0))
	else:
		print pkg_obj

	exit(0)

