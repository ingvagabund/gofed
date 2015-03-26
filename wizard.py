# TODO
# [  ] - add check I am in a package folder

import modules.Tools
import optparse
from modules.Config import Config

STEP_CLONE_REPO=1
STEP_DOWNLOAD_SRPM=2
STEP_IMPORT_SRPM=3
STEP_HAS_RESOLVES=4
STEP_CLONE_TO_BRANCHES=5
STEP_SCRATCH_BUILD=6
STEP_PUSH=7
STEP_BUILD=8
STEP_UPDATE=9
STEP_OVERRIDE=10

phase_methods = {}
phase_methods[STEP_SCRATCH_BUILD] = modules.Tools.scratchBuildBranches
phase_methods[STEP_PUSH] = modules.Tools.pushBranches
phase_methods[STEP_BUILD] = modules.Tools.buildBranches
#phase_methods[STEP_UPDATE] = modules.Tools.updateBranches

phase_name = {}
phase_name[STEP_SCRATCH_BUILD] = "Scratch build phase"
phase_name[STEP_PUSH] = "Push phase"
phase_name[STEP_BUILD] = "Build phase"
phase_name[STEP_UPDATE] = "Update phase"

if __name__ == "__main__":

	parser = optparse.OptionParser()

	parser.add_option(
	    "", "", "--scratch", dest="scratch", action = "store_true", default = False,
	    help = "Start from scratch build"
	)

	parser.add_option(
	    "", "", "--push", dest="push", action = "store_true", default = False,
	    help = "Start from push"
	)

	parser.add_option(
	    "", "", "--build", dest="build", action = "store_true", default = False,
	    help = "Start from build"
	)

	parser.add_option(
	    "", "", "--update", dest="update", action = "store_true", default = False,
	    help = "Start from update"
	)

	options, args = parser.parse_args()

	phase = -1
	if options.scratch:
		phase = STEP_SCRATCH_BUILD
	elif options.push:
		phase = STEP_PUSH
	elif options.build:
		phase = STEP_BUILD
	elif options.update:
		phase = STEP_UPDATE
	else:
		print "Missing options, run --help."
		exit(1)

	branches = Config().getBranches()

	for i in range(1, 11):
		if i < phase:
			continue

		if i not in phase_methods:
			print "Unable to find method for %s" % phase_name[i]
			break

		print ""
		print phase_name[i]
		print ""

		if not phase_methods[i](branches):
			break
