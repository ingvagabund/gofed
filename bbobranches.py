from modules.Config import Config
from modules.Utils import runCommand

import sys

# mappings of branches to build candidates
branch2bc = {
	'f20': 'f20-candidate',
	'f21': 'f21-candidate',
	'f22': 'f22-candidate',
	'el6': 'el6-candidate'
}

branch2build = {
	'f20': 'f20-build',
	'f21': 'f21-build',
	'f22': 'f22-build',
	'el6': 'dist-6E-epel-build'
}

branch2tag = {
	'f20': 'fc20',
	'f21': 'fc21',
	'f22': 'fc22',
	'el6': 'el6'
}

def buildrootOveride(build, long_tag, build_tag):
	cmd = "bodhi --buildroot-override=%s for %s --duration=20 --notes='temp non-stable dependecy waiting for stable'" % (build, long_tag)
	print cmd
	so, se, rc = runCommand(cmd)
	if rc != 0:
		print se
	else:
		print "koji wait-repo %s --build=%s" % (build_tag, build)
	print 20*"#"

if __name__ == "__main__":

	if len(sys.argv) < 2:
		print "Build name missing"
		exit(1)

	build = sys.argv[1]
	cfg = Config()
	branches = cfg.getOverrides().split(" ")
	for branch in branches:
		branch = branch.strip()

		if branch not in branch2bc:
			print "build candidate for %s branch not found" % branch
			continue

		buildrootOveride("%s.%s" % (build, branch2tag[branch]), branch2bc[branch], branch2build[branch])
