# for the given package, check, if the commit is already packaged in Fedora
import modules.Utils
import re
import os
import modules.specParser
import optparse
import modules.Repos
from modules.Repos import Repos, IPMap

if __name__ == "__main__":
	parser = optparse.OptionParser("%prog {package|-i import_path} ucommit")

        parser.add_option_group( optparse.OptionGroup(parser, "package", "package name") )

        parser.add_option_group( optparse.OptionGroup(parser, "ucommit", "upstream commit") )

	parser.add_option(
	    "", "-i", "--import_path", dest="ip", action = "store_true", default = False,
	    help = "import path of a golang package"
	)


	options, args = parser.parse_args()

	if len(args) != 2:
		print "Usage: %prog {package|-i import_path} ucommit"
		exit(0)

	pkg = args[0]
	commit = args[1]

	if options.ip:
		im = IPMap().loadIMap()
		ip = args[0]
		if 'golang(%s)' % ip in im:
			pkg, _ = im['golang(%s)' % ip]
		else:
			print "import path %s not found" % ip
			exit(1)

	repos_obj = Repos()
	repos = repos_obj.parseReposInfo()
	if pkg not in repos:
		print "package %s not found in golang.repos" % pkg
		exit(1)

	path, upstream = repos[pkg]
	ups_commits = modules.Repos.getRepoCommits(path, upstream)
	pkg_commit  = modules.specParser.getPackageCommits(pkg)

	# now fedora and commit, up to date?
	if commit not in ups_commits:
		print "%s: upstream commit %s not found" % (pkg, commit)
		exit(1)

	if pkg_commit not in ups_commits:
		print "%s: package commit %s not found" % (pkg, pkg_commit)
		exit(1)

	commit_ts = int(ups_commits[commit])
	pkg_commit_ts = int(ups_commits[pkg_commit])

	if commit == pkg_commit:
		print "package %s up2date" % pkg
	elif commit_ts > pkg_commit_ts:
		print "package %s outdated" % pkg
	else:
		print "package %s has newer commit" % pkg
	

