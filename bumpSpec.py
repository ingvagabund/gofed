import optparse
import urllib
import json
from modules.Utils import runCommand
from modules.specParser import SpecInfo

def getGithubLatestCommit(project, repo):
	link = "https://api.github.com/repos/%s/%s/commits" % (project, repo)
	f = urllib.urlopen(link)
	c_file = f.read()
	# get the latest commit
	commits = json.loads(c_file)
	if len(commits) == 0:
		return ""
	else:
		return commits[0]["sha"]

def getSpec():
	so, se, rc = runCommand("ls *.spec")
	if rc != 0:
		return ""
	else:
		return so.strip().split(" ")[0]

def getMacros(spec):

	err = ""
	macros = {}
	obj = SpecInfo(spec)
	macros["project"] = obj.getMacro("project")
	macros["repo"] = obj.getMacro("repo")

	if macros["project"] == "":
		err = "Unable to detect project macro"
		return err, {}

	if macros["repo"] == "":
		err = "Unable to detect repo macro"
		return err, {}

	macros["ip"] = obj.getMacro("import_path")
	if macros["ip"] == "":
		macros["provider"] = obj.getMacro("provider")
		macros["provider_tld"] = obj.getMacro("provider_tld")

		if macros["provider"] == "":
			err = "unable to detect provider macro"
			return err, {}

		if macros["provider_tld"] == "":
			err = "Unable to detect provider_tld macro"
			return err, {}

		macros["ip"] = "%s.%s/%s/%s" % (macros["provider"], macros["provider_tld"], macros["project"], macros["repo"])

	return "", macros

def downloadTarball(import_path, commit, repo):
	shortcommit = commit[:7]
	so, se, rc = runCommand("wget https://%s/archive/%s/%s-%s.tar.gz" % (
		import_path, commit, repo, shortcommit))

	if rc != 0:
		return False
	else:
		return True

def updateSpec(spec, commit):
	so, se, rc = runCommand("sed -i -e \"s/%%global commit\([[:space:]]\+\)[[:xdigit:]]\{40\}/%%global commit\\1%s/\" %s" % (commit, spec))
	if rc != 0:
		return False
	else:
		return True

def bumpSpec(spec, commit):
	so, se, rc = runCommand("rpmdev-bumpspec --comment=\"Bump to upstream %s\" %s" % (commit, spec))
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

	options, args = parser.parse_args()

	# must be on master branch
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
	err, macros = getMacros(spec)
	if err != "":
		print err
		exit(2)

	commit = options.commit
	if commit == "":
		# get latest commit
		print "Getting the latest commit from %s" % macros["ip"]
		commit = getGithubLatestCommit(macros["project"], macros["repo"])
		if commit == "":
			print "Unable to get the latest commit"
			exit(3)

	# download tarball
	print "Download tarball"
	if not downloadTarball(macros["ip"], commit, macros["repo"]):
		print "Unable to download tarball"
		exit(4)

	# update spec file
	print "Updating spec file"
	if not updateSpec(spec, commit):
		print "Unable to update spec file"
		exit(5)

	# bump spec file
	print "Bumping spec file"
	if not bumpSpec(spec, commit):
		print "Unable to bump spec file"
		exit(6)

