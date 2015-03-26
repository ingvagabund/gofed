import os
import optparse
from modules.Tools import cherryPickMaster, resetBranchesToOrigin
from modules.Tools import pullBranches, pushBranches, updateBranches
from modules.Tools import scratchBuildBranches, buildBranches
from modules.Config import Config

if __name__ == "__main__":

	parser = optparse.OptionParser("%prog")

	parser.add_option(
	    "", "", "--gcp", dest="gcp", action = "store_true", default = False,
	    help = "git cherry-pick master all branches"
	)

	parser.add_option(
	    "", "", "--git-reset", dest="greset", action = "store_true", default = False,
	    help = "git reset --hard all branches to remoter/origin/*"
	)

	parser.add_option(
	    "", "", "--pull", dest="pull", action = "store_true", default = False,
	    help = "git pull all branches"
	)

	parser.add_option(
	    "", "", "--push", dest="push", action = "store_true", default = False,
	    help = "fedpkg push all branches"
	)

	parser.add_option(
	    "", "", "--scratch", dest="scratch", action = "store_true", default = False,
	    help = "fedpkg scratch-build all branches"
	)

	parser.add_option(
	    "", "", "--build", dest="build", action = "store_true", default = False,
	    help = "fedpkg build all branches"
	)

	parser.add_option(
	    "", "", "--update", dest="update", action = "store_true", default = False,
	    help = "fedpkg update all branches"
	)

	options, args = parser.parse_args()

	if options.gcp:
		branches = Config().getBranches()
		cherryPickMaster(branches)
	if options.greset:
		branches = Config().getBranches()
		resetBranchesToOrigin(branches)
	if options.pull:
		branches = Config().getBranches()
		pullBranches(branches)
	if options.push:
		branches = Config().getBranches()
		pushBranches(branches)
	if options.scratch:
		branches = Config().getBranches()
		if scratchBuildBranches(branches):
			exit(0)
		else:
			exit(1)
	if options.build:
		branches = Config().getBranches()
		if buildBranches(branches):
			exit(0)
		else:
			exit(1)
	if options.update:
		branches = Config().getBranches()
		updateBranches(branches)

