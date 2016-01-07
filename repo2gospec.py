import optparse
from modules.Utils import ENDC, RED, GREEN
from modules.Utils import runCommand, FormatedPrint
from modules.Packages import packageInPkgdb

from modules.ImportPath import ImportPath
from modules.PackageInfo import PackageInfo
from modules.SpecGenerator import SpecGenerator
from modules.ImportPathsDecomposer import ImportPathsDecomposer
from modules.Config import Config

import os
import sys
import errno



def setOptions():
	parser = optparse.OptionParser("%prog [-e] [-d] file [file [file ...]]")

	sln = not (os.path.basename(sys.argv[0]) == "repo2gospec.py")
	github = os.path.basename(sys.argv[0]) == "github2gospec"
	googlecode = os.path.basename(sys.argv[0]) == "googlecode2gospec"
	bitbucket = os.path.basename(sys.argv[0]) == "bitbucket2gospec"

	SH = optparse.SUPPRESS_HELP

	parser.add_option(
	    "", "", "--github", dest="github", action="store_true", default = False,
	    help = SH if sln else "github.com repository"
	)

	parser.add_option(
	    "", "", "--googlecode", dest="googlecode", action="store_true", default = False,
	    help = SH if sln else "code.google.com repository"
	)

	parser.add_option(
	    "", "", "--bitbucket", dest="bitbucket", action="store_true", default = False,
	    help = SH if sln else "bitbucket.org repository"
	)

	parser.add_option(
	    "", "", "--detect", dest="detect", default = "",
	    help = SH if sln else "Detect repository from import path"
	)

	parser.add_option(
	    "", "", "--skip-errors", dest="skiperrors", action="store_true", default = False,
	    help = SH if sln else "Skip errors during Go symbol parsing"
	)

	if github:
		help_text = "Repository name, github.com/project/REPO"
	elif googlecode:
		help_text = "Repository name, code.google.com/p/REPO"
	elif bitbucket:
		help_text = "Repository name, bitbucket.org/project/REPO"
	else:
		help_text = "Repository name, e.g. github.com/project/REPO"
	

	parser.add_option(
	    "", "-r", "--repo", dest="repo", default = "",
	    help = help_text
	)

	if github:
		help_text = "Repository name, github.com/PROJECT/repository"
	elif bitbucket:
		help_text = "Repository name, bitbucket.org/PROJECT/repository"
	else:
		help_text = "Repository name, e.g. github.com/PROJECT/repository"

	parser.add_option(
	    "", "-p", "--project", dest="project", default = "",
	    help = SH if googlecode else help_text
	)

	if googlecode:
		parser.add_option(
		    "", "-c", "--rev", dest="revision", default = "",
		    help = "Revision"
		)
	else:
		parser.add_option(
		    "", "-c", "--commit", dest="commit", default = "",
		    help = "Commit. If not specified the latest is taken."
		)

	parser.add_option(
	    "", "-f", "--format", dest="format", action="store_true", default = False,
	    help = "Make messages more shiny"
	)

	parser.add_option(
	    "", "", "--force", dest="force", action="store_true", default = False,
	    help = "Generate spec file even if it is already in Fedora"
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
            "", "", "--with-build", dest="withbuild", action = "store_true", default = False,
            help = "Generate spec file with %build section"
        )

	parser.add_option(
            "", "", "--with-extra", dest="withextra", action = "store_true", default = False,
            help = "Generate spec file with additional pieces (e.g. definition of %gobuild and %gotest for explicit distributions)"
        )

	return parser.parse_args()

def checkOptions(options):
	fail = False

	if options.detect != "":
		return False

	if not options.github and not options.googlecode and not options.bitbucket:
		print "No provider specified"
		fail = True

	if options.github or options.googlecode or options.bitbucket:
		if options.repo == "":
			print "Repository missing"
			fail = True

	if options.github or options.bitbucket:
		if options.project == "":
			print "Project missing"
			fail = True

	if options.googlecode:
		if options.revision == "":
			print "Revision missing"
			fail = True


	return fail

def printBasicInfo(url, commit, name, formated=True):
	fmt_obj = FormatedPrint(formated)
	fmt_obj.printInfo("Repo URL: %s" % url)
	fmt_obj.printInfo("Commit: %s" % commit)
	fmt_obj.printInfo("Name: %s" % name)

# http://stackoverflow.com/questions/273192/in-python-check-if-a-directory-exists-and-create-it-if-necessary
def make_sure_path_exists(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

def isPkgInPkgDB(name, force):
	if packageInPkgdb(name):
		print "%sPackage %s already exists%s" % (RED, name, ENDC)
		if not force:
			exit(1)

def createBasicDirectories(name):
	make_sure_path_exists("%s/fedora/%s" % (name, name))
	os.chdir("%s/fedora/%s" % (name, name))

def downloadTarball(archive_url):
	so, se, rc = runCommand("wget -nv %s --no-check-certificate" % archive_url)
	if rc != 0:		
		print "%sUnable to download tarball:\n%s%s" % (RED, se, ENDC)
		exit(1)

if __name__ == "__main__":

	options, args = setOptions()

	if checkOptions(options):
		exit(1)

	fmt_obj = FormatedPrint(options.format)

	if not options.format:
		ENDC = ""
		RED = ""
		GREEN = ""

	if options.detect == "":
		# collect spec file information
		project = options.project
		repo = options.repo
		if not options.googlecode and project == "":
			fmt_obj.printError("Project missing")
			exit(1)

		if repo == "":
			fmt_obj.printError("Repository missing")
			exit(1)

		if options.github:
			import_path = "github.com/%s/%s" % (project, repo)
			commit = options.commit
		elif options.googlecode:
			import_path = "code.google.com/p/%s" % repo
			commit = options.revision
		elif options.bitbucket:
			import_path = "bitbucket.org/%s/%s" % (project, repo)
			commit = options.commit
		else:
			fmt_obj.printError("Provider not supported")
			exit(1)

	else:
		import_path = options.detect
		commit = options.commit

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

	# 1. decode some package info (name, archive url, ...)
	# 2. set path to downloaded tarball
	# 3. retrieve project info from tarball
	# 4. generate spec file
	
	pkg_obj = PackageInfo(import_path, commit, noGodeps, options.skiperrors)
	if not pkg_obj.decodeRepository():
		fmt_obj.printError(pkg_obj.getError())
		exit(1)

	name = pkg_obj.getName()
	if name == "":
		fmt_obj.printError("Unable to generate package name for %s" % import_path)
		exit(1)

	specfile = "%s.spec" % name
	total = 4

	# print basic information
	repository_info = pkg_obj.getRepositoryInfo()
	if repository_info == None:
		fmt_obj.printError("RepositoryInfo not set")
		exit(1)

	url = repository_info.getImportPathInfo().getPrefix()
	commit = repository_info.getCommit()
	archive_url = repository_info.getArchiveInfo().archive_url
	archive = repository_info.getArchiveInfo().archive
	printBasicInfo(url, commit, name, options.format)
	print ""

	# is the package already in Fedora
	fmt_obj.printProgress("(1/%s) Checking if the package already exists in PkgDB" % total)
	isPkgInPkgDB(name, options.force)

	# creating basic folder structure
	createBasicDirectories(name)

	# download tarball
	fmt_obj.printProgress("(2/%s) Downloading tarball" % total)
	downloadTarball(archive_url)
	so, se, rc = runCommand("tar -xf %s" % archive)
	if rc != 0:
		fmt_obj.printError("Unable to extract %s" % archive)
		exit(1)

	# generate spec file
	fmt_obj.printProgress("(3/%s) Generating spec file" % total)

	if not pkg_obj.decodeProject(os.getcwd()):
		fmt_obj.printError(pkg_obj.getError())
		exit(1)

	spec = SpecGenerator(import_path, commit, skiperrors = options.skiperrors, with_build = options.withbuild, with_extra = options.withextra)
	spec.setPackageInfo(pkg_obj)

	try:
		file = open("%s" % specfile, "w")
		spec.setOutputFile(file)
		if not spec.generate():
			fmt_obj.printError("Unable to generate spec file: %s" % spec.getError())
			exit(1)
	except IOError:
		fmt_obj.printError("Error: can\'t open %s file" % specfile)
		exit(1)

	file.close()

	so, se, rc = runCommand("rpmdev-bumpspec %s -c \"First package for Fedora\"" % specfile)
	if rc != 0:
		fmt_obj.printError("Unable to bump spec file: %s" % se)
		exit(1)

	fmt_obj.printProgress("(4/%s) Discovering golang dependencies" % total)

	prj_info = pkg_obj.getProjectInfo()
	if prj_info == None:
		fmt_obj.printError("Unable to bump spec file: %s" % se)
		exit(1)

	ip_used = prj_info.getImportedPackages()
	package_imports_occurence = prj_info.getPackageImportsOccurences()

	ipd = ImportPathsDecomposer(ip_used)
	if not ipd.decompose():
		fmt_obj.printError(ipd.getError())
		exit(1)

	warn = ipd.getWarning()
	if warn != "":
		fmt_obj.printWarning(warn)

	classes = ipd.getClasses()
	sorted_classes = sorted(classes.keys())

	for element in sorted_classes:
		if element == "Native":
			continue

		if element == "Unknown":
			fmt_obj.printWarning("Some import paths were not detected. Please run gofed ggi -c on extracted tarball manually")
			continue

		one_class = []
		for gimport in classes[element]:
			# does it occur only in main package?
			# remove it from classes[element]
			if len(package_imports_occurence[gimport]) == 1 and package_imports_occurence[gimport][0].endswith(":main"):
				continue

			one_class.append(gimport)

		if one_class == []:
			continue

		classes[element] = sorted(one_class)

		if element.startswith(url):
			continue

		ip_obj = ImportPath(element)
		if not ip_obj.parse():
			fmt_obj.printWarning("Unable to translate %s to package name" % element)
			continue

		pkg_name = ip_obj.getPackageName()
		pkg_in_pkgdb = False

		if pkg_name != "":
			pkg_in_pkgdb = packageInPkgdb(pkg_name)
			if pkg_in_pkgdb:
				print (GREEN + "Class: %s (%s) PkgDB=%s" + ENDC) % (element, pkg_name, pkg_in_pkgdb)
			else:
				print (RED + "Class: %s (%s) PkgDB=%s" + ENDC ) % (element, pkg_name, pkg_in_pkgdb)


	print ""
	fmt_obj.printInfo("Spec file %s at %s" % (specfile, os.getcwd()))
