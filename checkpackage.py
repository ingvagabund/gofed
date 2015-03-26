# Requires: python-PyGithub
import sys
from github import Github
import urllib2
import re

if len(sys.argv) != 2:
	print "Synopsis: %s <repo_url>" % sys.argv[0]
	exit(0)

repo_url = sys.argv[1]

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

#https://github.com/kr/pretty
def detectRepo(repo_url):
	if "github" in repo_url:
		repo = repo_url.split("github.com")[1]
		repo = repo[1:]
		pkg_name = "golang-github-%s" % repo.replace("/","-")
		return (repo,  pkg_name)
	return ("","")

# get upstream latest commit
def getGithubLatestCommit(repo_name):
	g = Github()

	for branch in g.get_repo(repo_name).get_branches():
		if branch.name == "master":
			return branch.commit.sha

	return ""

# get fedora latest commit
def getFedoraLatestCommit(pkg_name):
#	"http://pkgs.fedoraproject.org/cgit/golang-github-kr-pretty.git/plain/golang-github-kr-pretty.spec"
	spec = "http://pkgs.fedoraproject.org/cgit/%s.git/plain/%s.spec" % (pkg_name, pkg_name)
	for line in urllib2.urlopen(spec):
		if "%global commit" in line:
			commit = re.sub("[ \t]+", " ", line).split(' ')[2].strip()
			return commit

	return ""

(repo, pkg_name) = detectRepo(repo_url)
upstream_commit = getGithubLatestCommit(repo)
fedora_commit = getFedoraLatestCommit(pkg_name)

status = "%s up2date  %s" % (GREEN, ENDC)
if upstream_commit != fedora_commit:
	status = "%s outdated %s" % (RED, ENDC)

print "%s %s %s %s" % (upstream_commit, fedora_commit, status, repo_url)

#print "Upstream commit:  %s" % upstream_commit
#print "Commit in Fedora: %s" % fedora_commit
