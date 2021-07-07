from gofedlib.logger.logger import Logger

from gofedlib.utils import ENDC, RED, GREEN, runCommand, getScriptDir
from gofed.modules.Utils import FormatedPrint

from gofed.modules.SpecGenerator import SpecGenerator

import os
import sys
import errno
import logging
import json

from gofedinfra.system.core.factory.actfactory import ActFactory
from gofedlib.go.data2specmodeldata import Data2SpecModelData
from gofedlib.go.contentmetadataextractor import ContentMetadataExtractor
from gofedlib.go.importpath.parserbuilder import ImportPathParserBuilder
from gofedlib.go.importpath.decomposerbuilder import ImportPathsDecomposerBuilder
from gofedlib.types import UnsupportedImportPathError
from gofedlib.distribution.clients.pkgdb.client import PkgDBClient
from gofedlib.distribution.packagenamegeneratorbuilder import PackageNameGeneratorBuilder
from gofedlib.providers.providerbuilder import ProviderBuilder
from gofedlib.repository.repositoryclientbuilder import RepositoryClientBuilder
from gofedinfra.system.artefacts.artefacts import (
	ARTEFACT_GOLANG_PROJECT_PACKAGES,
	ARTEFACT_GOLANG_PROJECT_CONTENT_METADATA
)

from cmdsignature.parser import CmdSignatureParser
from gofedlib.utils import getScriptDir

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
	if PkgDBClient().packageExists(name):
		print "%sPackage %s already exists%s" % (RED, name, ENDC)
		if not force:
			exit(1)

def createTargetDirectories(name, target = ""):
	if target == "":
		target = "%s/%s" % (os.getcwd(), name)
	else:
		target = os.path.abspath("%s/%s" % (target, name) )

	make_sure_path_exists(target)
	os.chdir(target)

def checkDependencies(fmt_obj, classes, url):
	name_generator = PackageNameGeneratorBuilder().buildWithLocalMapping()
	for element in sorted(classes.keys()):
		if element == "Unknown":
			fmt_obj.printWarning("Some import paths were not detected. Please run gofed ggi -c on extracted tarball manually")
			continue

		classes[element] = sorted(classes[element])

		try:
			pkg_name = name_generator.generate(element).name()
		except UnsupportedImportPathError as e:
			fmt_obj.printWarning("Unable to translate %s to package name: %s" % (element, e))
			continue

		pkg_in_pkgdb = PkgDBClient().packageExists(pkg_name)
		if pkg_in_pkgdb:
			print (GREEN + "\tClass: %s (%s) PkgDB=%s" + ENDC) % (element, pkg_name, pkg_in_pkgdb)
		else:
			print (RED + "\tClass: %s (%s) PkgDB=%s" + ENDC ) % (element, pkg_name, pkg_in_pkgdb)

if __name__ == "__main__":

	cur_dir = getScriptDir(__file__)
	gen_flags = "%s/repo2gospec-global.yml" % (cur_dir)

	program_name = os.path.basename(sys.argv[0])
	provider = ""

	if program_name == "repo2gospec.py":
		subcmd_flags = "%s/repo2gospec.yml" % (cur_dir)
	elif program_name == "github2gospec":
		subcmd_flags = "%s/github2gospec.yml" % (cur_dir)
		provider = "github"
	elif program_name == "googlecode2gospec":
		subcmd_flags = "%s/googlecode2gospec.yml" % (cur_dir)
		provider = "googlecode"
	elif program_name == "bitbucket2gospec":
		subcmd_flags = "%s/bitbucket2gospec.yml" % (cur_dir)
		provider = "bitbucket"

	parser = CmdSignatureParser([gen_flags, subcmd_flags]).generate().parse()
	if not parser.check():
		exit(1)

	options = parser.options()

	Logger.set(options.verbose)

	fmt_obj = FormatedPrint(options.format)

	if not options.format:
		ENDC = ""
		RED = ""
		GREEN = ""

	if provider == "":
		if options.github:
			provider = "github"
		elif options.bitbucket:
			provider = "bitbucket"
		elif options.googlecode:
			provider = "googlecode"

	# collect spec file information
	if provider == "github":
		import_path = "github.com/%s/%s" % (options.project, options.repo)
		commit = options.commit
	elif provider == "googlecode":
		import_path = "code.google.com/p/%s" % options.repo
		commit = options.revision
	elif provider == "bitbucket":
		import_path = "bitbucket.org/%s/%s" % (options.project, options.repo)
		commit = options.commit
	else:
		import_path = options.detect
		commit = options.commit

	path = ""
	if options.directory != "":
		if options.directory[0] == "/":
			path = options.directory
		else:
			path = os.path.abspath(options.directory)

		# path exists?
		if not os.path.exists(path):
			logging.error("Path '%s' does not exist" % path)
			exit(1)

	name_generator = PackageNameGeneratorBuilder().buildWithLocalMapping()
	upstream_provider = ProviderBuilder().buildUpstreamWithLocalMapping()
	ipparser = ImportPathParserBuilder().buildWithLocalMapping()

	import_path_prefix = ipparser.parse(import_path).prefix()
	repository_prefix = upstream_provider.parse(import_path_prefix).prefix()
	repository_signature = upstream_provider.signature()
	name = name_generator.generate(import_path_prefix).name()

	# 1. decode some package info (name, archive url, ...)
	# 2. set path to downloaded tarball
	# 3. retrieve project info from tarball
	# 4. generate spec file
	specfile = "%s.spec" % name
	total = 4

	# commit
	if options.directory == "" and commit == "":
		try:
			repo = RepositoryClientBuilder().buildWithRemoteClient(repository_signature,lazy=True)
                except KeyError as err:
			logging.error(err)
			exit(1)
		commit = repo.latestCommit()["hexsha"]

	# print basic information
	printBasicInfo(repository_prefix, commit, name, options.format)
	print ""

	# is the package already in Fedora
	fmt_obj.printProgress("(1/%s) Checking if the package already exists in PkgDB" % total)
	isPkgInPkgDB(name, options.force)

	# creating target directory structure
	createTargetDirectories(name, options.target)

	# download tarball
	fmt_obj.printProgress("(2/%s) Collecting data" % total)

	# convert import path to project provider path
	metadata = {
		"provider_prefix": repository_prefix,
		"import_path": import_path_prefix,
		"commit": commit,
		"package_name": name
		#{"key": "summary", "value": "..."},
		#{"key": "description", "value": "..."},
		#{"key": "website", "value": "https://godoc.org/github.com/bradfitz/http2"}
	}

	if options.directory != "":
		data = {
			"type": "user_directory",
			"resource": os.path.abspath(path),
			"ipprefix": metadata["import_path"]
		}
	else:
		data = {
			"type": "upstream_source_code",
			"repository": repository_signature,
			"commit": metadata["commit"],
			"ipprefix": metadata["import_path"]
		}

	try:
		data = ActFactory().bake("spec-model-data-provider").call(data)
	except Exception as e:
		logging.error(e)
		exit(1)

	combiner = Data2SpecModelData()
	combiner.combine(
		metadata,
		data[ARTEFACT_GOLANG_PROJECT_PACKAGES],
		data[ARTEFACT_GOLANG_PROJECT_CONTENT_METADATA]
	)
	data = combiner.getData()

	# generate spec file
	fmt_obj.printProgress("(3/%s) Generating spec file" % total)

	spec = SpecGenerator(
		with_build = options.withbuild,
		with_extra = options.withextra
	)

	try:
		with open("%s" % specfile, "w") as f:
			spec.generate(data, f)

	except IOError:
		fmt_obj.printError("Error: can\'t write to '%s' file" % specfile)
		exit(1)

	so, se, rc = runCommand("rpmdev-bumpspec %s -c \"First package for Fedora\"" % specfile)
	if rc != 0:
		fmt_obj.printError("Unable to bump spec file: %s" % se)
		exit(1)

	fmt_obj.printProgress("(4/%s) Discovering golang dependencies" % total)

	if data["data"]["packages"] != []:
		package_deps = reduce(lambda x,y: x + y, map(lambda l: l["dependencies"], data["data"]["packages"]))
	else:
		package_deps = []

	if data["data"]["tests"] != []:
		test_deps = reduce(lambda x,y: x + y, map(lambda l: l["dependencies"], data["data"]["tests"]))
	else:
		test_deps = []

	package_deps = sorted(list(set(package_deps)))
	diff_deps = sorted(list(set(test_deps) - set(package_deps)))
	decomposer = ImportPathsDecomposerBuilder().buildLocalDecomposer()

	# filter out self imports
	package_deps = filter(lambda l: not l.startswith(metadata["import_path"]), package_deps)
	diff_deps = filter(lambda l: not l.startswith(metadata["import_path"]), diff_deps)

	add_line = True
	if package_deps != []:
		fmt_obj.printProgress("Discovering package dependencies")
		decomposer.decompose(package_deps)
		classes = decomposer.classes()
		checkDependencies(fmt_obj, classes, metadata["import_path"])
		print ""
		add_line = False

	if diff_deps != []:
		fmt_obj.printProgress("Discovering test dependencies")
		decomposer.decompose(diff_deps)
		classes = decomposer.classes()
		checkDependencies(fmt_obj, classes, metadata["import_path"])
		print ""
		add_line = False

	if add_line:
		print ""

	fmt_obj.printInfo("Spec file %s at %s" % (specfile, os.getcwd()))
