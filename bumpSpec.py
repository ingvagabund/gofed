import optparse
from modules.Utils import runCommand, RED, ENDC
from modules.SpecParser import SpecParser

from modules.RepositoryInfo import RepositoryInfo

def getSpec():
	so, se, rc = runCommand("ls *.spec")
	if rc != 0:
		return ""
	else:
		return so.strip().split(" ")[0]

def getMacros(spec, repoprefix):

	err = ""
	macros = {}
	obj = SpecParser(spec)
	if not obj.parse():
		err = obj.getError()
		return err, {}, -1

	if repoprefix == "":
		macros["project"] = obj.getMacro("project")
		macros["repo"] = obj.getMacro("repo")
		macros["provider"] = obj.getMacro("provider")
		macros["commit"] = obj.getMacro("commit")
		macros["ip"] = obj.getMacro("provider_prefix")
		if macros["ip"] == "":
			macros["ip"] = obj.getMacro("import_path")

	else:
		macros["project"] = obj.getMacro("%s_project" % repoprefix)
		macros["repo"] = obj.getMacro("%s_repo" % repoprefix)
		macros["provider"] = obj.getMacro("%s_provider" % repoprefix)
		macros["commit"] = obj.getMacro("%s_commit" % repoprefix)
		macros["ip"] = obj.getMacro("%s_provider_prefix" % repoprefix)
		if macros["ip"] == "":
			macros["ip"] = obj.getMacro("%s_import_path" % repoprefix)

	last_bug_id = obj.getBugIdFromLastChangelog()

	if macros["project"] == "":
		err = "Unable to detect project macro"
		return err, {}, -1

	if macros["repo"] == "":
		err = "Unable to detect repo macro"
		return err, {}, -1

	if macros["provider"] == "":
		err = "unable to detect provider macro"
		return err, {}, -1

	if macros["commit"] == "":
		err = "unable to detect commit macro"
		return err, {}, -1

	if macros["ip"] == "":
		err = "Unable to detect provider URL"
		return err, {}, -1

	return "", macros, last_bug_id

def downloadTarball(archive_url):
	so, se, rc = runCommand("wget -nv %s --no-check-certificate" % archive_url)
	if rc != 0:		
		print "%sUnable to download tarball:\n%s%s" % (RED, se, ENDC)
		exit(1)

def updateSpec(spec, commit, repoprefix):
	if repoprefix == "":
		commit_macro = "commit"
	else:
		commit_macro = "%s_commit" % repoprefix
	cmd = "sed -i -e \"s/%%global %s\([[:space:]]\+\)[[:xdigit:]]\{40\}/%%global %s\\1%s/\" %s" % (commit_macro, commit_macro, commit, spec)

	so, se, rc = runCommand(cmd)
	if rc != 0:
		return False
	else:
		return True

def bumpSpec(spec, commit, last_bug_id):
	if last_bug_id != -1:
		cmd = "rpmdev-bumpspec --comment=\"$(echo \"Bump to upstream %s\n  related: #%s\")\" %s" % (commit, last_bug_id, spec)
	else:
		cmd = "rpmdev-bumpspec --comment=\"Bump to upstream %s\" %s" % (commit, spec)

	so, se, rc = runCommand(cmd)
	if rc != 0:
		return False
	else:
		return True

if __name__ == "__main__":

	parser = optparse.OptionParser("%prog [-c COMMIT] ")

	parser.add_option(
	    "", "-c", "--commit", dest="commit", default = "",
	    help = "Bump spec file to commit."
	)

	parser.add_option(
	    "", "-s", "--skip-master", dest="skipmaster", action="store_true", default = False,
	    help = "Skip master branch test."
	)

	parser.add_option(
	    "", "", "--skip-checks", dest="skipchecks", action="store_true", default = False,
	    help = "Skip checks for tags and releases."
	)

	parser.add_option(
	    "", "", "--repo-prefix", dest="repoprefix", default = "",
	    help = "Update tarball for repo macro prefixed with repo-prefix."
	)

	parser.add_option(
	    "", "", "--no-bump", dest="nobump", action="store_true", default = False,
	    help = "Don't bump spec file"
	)

	options, args = parser.parse_args()

	# must be on master branch
	if not options.skipmaster:
		so, se, rc = runCommand("git branch | grep '*' | sed 's/*//'")
		if rc != 0:
			print "Not in a git repository"
			exit(1)

		branch = so.split('\n')[0].strip()
		if branch != "master":
			print "Not on branch master"
			exit(1)

	# get spec file
	print "Searching for spec file"
	spec = getSpec()
	if spec == "":
		print "Unable to find spec file"
		exit(1)

	# get macros
	print "Reading macros from %s" % spec
	err, macros, last_bug_id = getMacros(spec, options.repoprefix)
	if err != "":
		print err
		exit(2)

	provider = macros["provider"]
	project = macros["project"]
	repo = macros["repo"]
	current_commit = macros["commit"]

	# only github so far
	if provider != "github" and provider != "bitbucket":
		print "Only githum.com and bitbucket.org are supported"
		exit(2)

	commit = options.commit
	if commit == "":
		# get latest commit
		print "Getting the latest commit from %s" % macros["ip"]

	ri_obj = RepositoryInfo(macros["ip"], commit)
	if not ri_obj.retrieve():
		print ri_obj.getError()
		exit(1)

	commit = ri_obj.getCommit()
	# don't bump if the commit is equal to the latest
	if commit == current_commit:
		print "The latest commit equals the current commit"
		exit(1)

	if not options.skipchecks:
		if provider == "github":
			tags = ri_obj.getGithubTags(project, repo)
			releases = ri_obj.getGithubReleases(project, repo)

			print "Tags: " + ", ".join(tags[:5])
			print "Releases: " + ", ".join(releases[:5])

	# download tarball
	print "Downloading tarball"
	ar_info = ri_obj.getArchiveInfo()
	shortcommit = ar_info.shortcommit
	archive = ar_info.archive
	archive_url = ar_info.archive_url

	downloadTarball(archive_url)

	# update spec file
	print "Updating spec file"
	if not updateSpec(spec, commit, options.repoprefix):
		print "Unable to update spec file"
		exit(5)

	# bump spec file
	if not options.nobump:
		print "Bumping spec file"
		if not bumpSpec(spec, commit, last_bug_id):
			print "Unable to bump spec file"
			exit(6)

