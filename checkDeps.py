import json
import sys
import modules.Repos
import modules.specParser
import modules.Utils
import optparse
from modules.Utils import GREEN, RED, ENDC, YELLOW
from modules.Repos import Repos, IPMap

def getGoDeps(path):
	deps = {}
	with open(path, 'r') as file:
		json_deps = json.loads(file.read())

	if "Deps" not in json_deps:
		return {}

	for dep in json_deps["Deps"]:
		if "ImportPath" not in dep or "Rev" not in dep:
			continue

		ip = str(dep["ImportPath"])
		rev = str(dep["Rev"])
		deps[ip] = rev

	return deps


if __name__ == "__main__":

	parser = optparse.OptionParser("%prog [-l] [-v] deps.json")

	parser.add_option_group( optparse.OptionGroup(parser, "deps.json", "JSON file with golang deps") )

	parser.add_option(
	    "", "-l", "--dontpull", dest="pull", action = "store_false", default = True,
	    help = "Dont pull repositories (use only local)"
	)

	parser.add_option(
	    "", "-v", "--verbose", dest="verbose", action = "store_true", default = False,
	    help = "Verbose mode"
	)

	options, args = parser.parse_args()

	if len(args) != 1:
		print "Synopsis: prog [-l] [-v] deps.json"
		exit(1)

	json_file = args[0]

	deps = getGoDeps(json_file)
	if deps == {}:
		print "%s is corrupted or has no dependencies" % json_file
		exit(1)

	repos_obj = Repos()

	im = IPMap().loadIMap()
	repos = repos_obj.parseReposInfo()
	keys = sorted(deps.keys())

	cache = []

	for dep in keys:
		ip = dep
		commit = deps[dep]
		pkg = ''
		if 'golang(%s)' % ip in im:
			pkg, _ = im['golang(%s)' % ip]
		else:
			print "import path %s not found" % ip
			continue

		if pkg not in repos:
			print "package %s not found in golang.repos" % pkg
			continue

		if pkg in cache:
			continue

		cache.append(pkg)
		path, upstream = repos[pkg]
		ups_commits = modules.Repos.getRepoCommits(path, upstream, pull=options.pull)
		pkg_commit  = modules.specParser.getPackageCommits(pkg)

		# now fedora and commit, up to date?
		if commit not in ups_commits:
			print "%s: upstream commit %s not found" % (pkg, commit)
			continue

		if pkg_commit not in ups_commits:
			print "%s: package commit %s not found" % (pkg, pkg_commit)
			continue

		commit_ts = int(ups_commits[commit])
		pkg_commit_ts = int(ups_commits[pkg_commit])

		if commit == pkg_commit:
			if options.verbose:
				print "%spackage %s up2date%s" % (GREEN, pkg, ENDC)
		elif commit_ts > pkg_commit_ts:
			print "%spackage %s outdated%s" % (RED, pkg, ENDC)
		else:
			if options.verbose:
				print "%spackage %s has newer commit%s" % (YELLOW, pkg, ENDC)

	


