from Utils import runCommand
from Config import Config
import os
import threading
import subprocess

BUILDURL="http://koji.fedoraproject.org/koji/taskinfo?taskID=%s"

# DRY MODE
# - don't run any command changing a state
#
# DECOMPOSITION
# - low level commands
# - simple commands (wrappers over low level commands)
# - multi commands (running simple commands over chosen branches)

# mappings of branches to build candidates
branch2bc = {
	'f20': 'f20-candidate',
	'f21': 'f21-candidate',
	'f22': 'f22-candidate',
	'f23': 'f23-candidate',
	'el6': 'el6-candidate'
}

branch2build = {
	'f20': 'f20-build',
	'f21': 'f21-build',
	'f22': 'f22-build',
	'f23': 'f23-build',
	'el6': 'dist-6E-epel-build'
}

branch2tag = {
	'f20': 'fc20',
	'f21': 'fc21',
	'f22': 'fc22',
	'f23': 'fc23',
	'el6': 'el6'
}


class LowLevelCommand:

	def __init__(self, dry=False, debug=False):
		self.dry = dry
		self.debug = debug

	def runFedpkgSrpm(self):
		"""
		Run 'fedpkg srpm'.
		It returns so, se, rc triple.
		"""
		if self.debug == True:
			print "Running 'fedpkg srpm'"

		if self.dry == True:
			so = "Wrote: gofed-test-0.6.2-0.3.git89088df.fc20.src.rpm"
			se = ""
			rc = 0
			return so, se, rc
		else:
			return runCommand("fedpkg srpm")

	def runFedpkgScratchBuild(self, srpm):
		"""
		Run 'fedpkg scratch-build --nowait --srpm=SRPM'
		"""
		if self.debug == True:
			print "Running 'fedpkg scratch-build --nowait --srpm=SRPM'"

		if self.dry == True:
			so = "Created task: 1"
			se = ""
			rc = 0
			return so, se, rc
		else:
			return runCommand("fedpkg scratch-build --nowait --srpm=%s" % srpm)

	def runFedpkgBuild(self):
		"""
		Run 'fedpkg build --nowait'
		"""
		if self.debug == True:
			print "Running 'fedpkg build --nowait'"

		if self.dry == True:
			so = "Created task: 1"
			se = ""
			rc = 0
			return so, se, rc
		else:
			return runCommand("fedpkg build --nowait")

	def runGitPull(self):
		"""
		Run 'git pull'.
		It returns so, se, rc triple.
		"""
		if self.debug == True:
			print "Running 'git pull'"

		if self.dry == True:
			so = ""
			se = ""
			rc = 0
			return so, se, rc
		else:
			return runCommand("git pull")

	def runFedpkgPush(self):
		"""
		Run 'fedpkg push'.
		It returns so, se, rc triple.
		"""
		if self.debug == True:
			print "Running 'fedpkg push'"

		if self.dry == True:
			so = ""
			se = ""
			rc = 0
			return so, se, rc
		else:
			return runCommand("fedpkg push")

	def runFedpkgUpdate(self):
		"""
		Run 'fedpkg update'.
		It returns so, se, rc triple.
		"""
		if self.debug == True:
			print "Running 'fedpkg update'"

		if self.dry == True:
			so = ""
			se = ""
			rc = 0
			return so, se, rc
		else:
			subprocess.call("fedpkg update", shell=True)
			return ""

	def runFedpkgSwitchBranch(self, branch):
		"""
		Run 'fedpkg switch-branch'.
		It returns so, se, rc triple.
		"""
		if self.debug == True:
			print "Running 'fedpkg switch-branch'"

		if self.dry == True:
			so = ""
			se = ""
			rc = 0
			return so, se, rc
		else:
			return runCommand("fedpkg switch-branch %s" % branch)

	def runGitCherryPick(self, commit="master"):
		"""
		Run 'git cherry-pick COMMIT'.
		It returns so, se, rc triple.
		"""
		if self.debug == True:
			print "Running 'git cherry-pick %s'" % commit

		if self.dry == True:
			so = ""
			se = ""
			rc = 0
			return so, se, rc
		else:
			return runCommand("git cherry-pick %s" % commit)

	def runGitReset(self, branch):
		"""
		Run 'git reset --hard remotes/origin/BRANCH'.
		It returns so, se, rc triple.
		"""
		if self.debug == True:
			print "Running 'git reset --hard remotes/origin/%s'" % branch

		if self.dry == True:
			so = ""
			se = ""
			rc = 0
			return so, se, rc
		else:
			return runCommand("git reset --hard remotes/origin/%s" % branch)

	def runGitMerge(self, branch):
		"""
		Run 'git merge BRANCH'.
		It returns so, se, rc triple.
		"""
		if self.debug == True:
			print "Running 'git merge %s'" % branch

		if self.dry == True:
			so = ""
			se = ""
			rc = 0
			return so, se, rc
		else:
			return runCommand("git merge %s" % branch)

	def runBodhiOverride(self, branch, name):
		"""
		Run 'bodhi --buildroot-override=BUILD for TAG --duration=DURATION --notes=NOTES'.
		It returns so, se, rc triple.
		"""
		build = "%s.%s" % (name, branch2tag[branch])
		long_tag = branch2bc[branch]
		build_tag = branch2build[branch]

		if self.debug == True:
			print "Running 'bodhi --buildroot-override=%s for %s --duration=20 --notes='temp non-stable dependecy waiting for stable''" % (build, long_tag)

		if self.dry == True:
			so = ""
			se = ""
			rc = 0
			return so, se, rc
		else:
			return runCommand("bodhi --buildroot-override=%s for %s --duration=20 --notes='temp non-stable dependecy waiting for stable'" % (build, long_tag))

	def runKojiWaitOverride(self, branch, name):
		"""
		Run 'koji wait-repo TAG --build=BUILD'.
		It returns so, se, rc triple.
		"""
		build = "%s.%s" % (name, branch2tag[branch])
		build_tag = branch2build[branch]

		if self.debug == True:
			print "Running 'koji wait-repo %s --build=%s'" % (build_tag, build)

		if self.dry == True:
			so = ""
			se = ""
			rc = 0
			return so, se, rc
		else:
			return runCommand("koji wait-repo %s --build=%s" % (build_tag, build))

	def runGitLog(self, depth):
		"""
		Run 'git log --pretty=format:"%%H" -n DEPTH'.
		It returns so, se, rc triple.
		"""
		if self.debug == True:
			print "Running 'git log --pretty=format:\"%%H\" -n %s'" % depth

		if self.dry == True:
			so = """4e604fecc22b498e0d46854ee4bfccdfc1932b12
c46cdd60710b184f834b54cff80502027b66c5e0
6170e22ecb5923bbd22a311f172fcf59c5f16c08
0fc92e675c90e7b9e1eaba0c4837093b9b365317
21cf1880e696fd7047f8b0f5605ffa72dde6c504
8025678aab1c404aecdd6d7e5b3afaf9942ef6c6
6ed91011294946fd7ca6e6382b9686e12deda9be
ec0ebc48684bccbd4793b83edf14c59076edb1eb
adf728db9355a86332e17436a78f54a769e194be"""
			se = ""
			rc = 0
			return so, se, rc
		else:
			return runCommand("git log --pretty=format:\"%%H\" -n %s" % depth)


class SimpleCommand:

	def __init__(self, dry=False, debug=False):
		self.dry = dry
		self.debug = debug
		self.llc = LowLevelCommand(dry=self.dry, debug=self.debug)

	def makeSRPM(self):	
		so, _, rc = self.llc.runFedpkgSrpm()
		if rc != 0:
			return ""

		for line in so.split("\n"):
			line = line.strip()
			if line == "":
				continue

			parts = line.split(" ")
			if len(parts) != 2:
				continue

			return parts[1]

		return ""

	def runBuild(self):
		so, _, rc = self.llc.runFedpkgBuild()
		if rc != 0:
			return -1

		task_lines = filter(lambda l: l.startswith("Created task:"), so.split("\n"))
		if len(task_lines) != 1:
			return -1

		task_id = task_lines[0].strip().split(" ")[-1]
		if task_id.isdigit():
			return int(task_id)

		return -1

	def runScratchBuild(self, srpm):
		so, _, rc = self.llc.runFedpkgScratchBuild(srpm)
		if rc != 0:
			return -1

		task_lines = filter(lambda l: l.startswith("Created task:"), so.split("\n"))
		if len(task_lines) != 1:
			return -1

		task_id = task_lines[0].strip().split(" ")[-1]
		if task_id.isdigit():
			return int(task_id)

		return -1

	def pullBranch(self, branch):
		so, se, rc = self.llc.runGitPull()
		if rc != 0:
			return se

		return ""

	def pushBranch(self, branch):
		so, se, rc = self.llc.runFedpkgPush()
		if rc != 0:
			return se

		return ""

	def updateBranch(self, branch):
		self.llc.runFedpkgUpdate()

		return ""

	def mergeMaster(self):
		so, se, rc = self.llc.runGitMerge("master")
		if rc != 0 or se != "":
			return se

		return ""

	def overrideBuild(self, branch, name):
		so, se, rc = self.llc.runBodhiOverride(branch, name)
		if rc != 0 or se != "":
			return se

		return ""

	def waitForOverrideBuild(self, branch, name):
		so, se, rc = self.llc.runKojiWaitOverride(branch, name)
		if rc != 0:
			return se

		return ""

	def getGitCommits(self, depth):
		so, sr, rc = self.llc.runGitLog(depth)
		if rc != 0:
			return "Unable to list commits: %s" % se, []

		commits = []
		for line in so.split("\n"):
			line = line.strip()
			if line == "":
				continue
			commits.append(line)

		return "", commits

class WatchTaskThread(threading.Thread):
	def __init__(self, task_id):
		super(WatchTaskThread, self).__init__()
		self.task_id = task_id
		self.err = ""

	def run(self):
		runCommand("koji watch-task %s --quiet" % self.task_id)

	def getError(self):
		return self.err

class WaitTaskThread(threading.Thread):
	def __init__(self, task_id):
		super(WaitTaskThread, self).__init__()
		self.task_id = task_id
		self.state = False
		self.err = ""

	def run(self):
		so, se, rc = runCommand("koji taskinfo %s" % self.task_id)
		if rc != 0:
			self.err = "Unable to get taskinfo for %s branch's %s task: %s" % (branch, task_id, se)
			return

		state_lines = filter(lambda l: l.startswith("State"), so.split("\n"))

		state = state_lines[0].split(" ")[1]
		if state == "closed":
			self.state = True

	def getState(self):
		return self.state

	def getError(self):
		return self.err

class MultiCommand:

	def __init__(self, dry=False, debug=False):
		self.dry = dry
		self.debug = debug
		self.sc = SimpleCommand(debug=self.debug, dry=self.dry)
		self.llc = LowLevelCommand(debug=self.debug, dry=self.dry)

	def _buildBranches(self, branches, scratch=True):

		task_ids = {}
		# init [scratch] builds
		for branch in branches:
			print "Branch %s" % branch

			so, _, rc = self.llc.runFedpkgSwitchBranch(branch)
			if rc != 0:
				print "Unable to switch to %s branch" % branch
				continue

			srpm = ""
			if scratch:
				srpm = self.sc.makeSRPM()
				if srpm == "":
					print "Unable to create srpm"
					continue

			task_id = -1
			if scratch:
				task_id = self.sc.runScratchBuild(srpm)
			else:
				task_id = self.sc.runBuild()

			if task_id == -1:
				print "Unable to initiate task"
				continue

			task_ids[branch] = task_id
		
			if scratch:
				print "Scratch build %s initiated" % (BUILDURL % task_id)
			else:
				print "Build %s initiated" % (BUILDURL % task_id)

		return task_ids

	def _waitForTasks(self, task_ids):

		thread_list = {}
		for branch in task_ids:
			task_id = task_ids[branch]
			print "Watching %s branch, %s" % (branch, BUILDURL % task_id)
			if self.dry == False:
				thread_list[branch] = WatchTaskThread(task_id)
				thread_list[branch].start()

		if self.dry == False:
			for branch in task_ids:
				thread_list[branch].join()
				err = thread_list[branch].getError()
				if err != "":
					print err

	def _checkTasks(self, task_ids):
		all_done = True
		print "Checking finished tasks..."
		thread_list = {}

		if self.dry == False:
			for branch in task_ids:
				task_id = task_ids[branch]
				thread_list[branch] = WaitTaskThread(task_id)
				thread_list[branch].start()

			for branch in task_ids:
				thread_list[branch].join()

		for branch in task_ids:
			if self.dry == True:
				print "%s: closed" % branch
				continue

			if thread_list[branch].getState():
				print "%s: closed" % branch
			else:
				all_done = False
				print "%s: failed" % branch

		return all_done

	def scratchBuildBranches(self, branches):
		# init [scratch] builds
		task_ids = self._buildBranches(branches)
		print ""

		# wait for builds
		self._waitForTasks(task_ids)
		print ""

		# check out builds
		return self._checkTasks(task_ids)

	def buildBranches(self, branches):

		# init [scratch] builds
		task_ids = self._buildBranches(branches, scratch=False)
		print ""

		# wait for builds
		self._waitForTasks(task_ids)
		print ""

		# check out builds
		return self._checkTasks(task_ids)

	def pullBranches(self, branches):
		print "Pulling from branches: %s" % ", ".join(branches)

		all_done = True
		for branch in branches:
			print "Branch %s" % branch
			so, _, rc = self.llc.runFedpkgSwitchBranch(branch)
			if rc != 0:
				print "Unable to switch to %s branch" % branch
				all_done = False
				continue

			err = self.sc.pullBranch(branch)
			if err != "":
				print "%s: %s" % (branch, err)
				all_done = False

		return all_done

	def pushBranches(self, branches):
		print "Pushing to branches: %s" % ",".join(branches)

		all_done = True
		for branch in branches:
			print "Branch %s" % branch
			so, _, rc = self.llc.runFedpkgSwitchBranch(branch)
			if rc != 0:
				print "Unable to switch to %s branch" % branch
				all_done = False
				continue

			err = self.sc.pushBranch(branch)
			if err != "":
				print "%s: %s" % (branch, err)
				all_done = False

		return all_done

	def updateBranches(self, branches):
		print "Updating branches: %s" % ",".join(branches)

		all_done = True
		for branch in branches:
			print "Branch %s" % branch
			so, _, rc = self.llc.runFedpkgSwitchBranch(branch)
			if rc != 0:
				print "Unable to switch to %s branch" % branch
				all_done = False
				continue

			err = self.sc.updateBranch(branch)
			if err != "":
				print "%s: %s" % (branch, err)
				all_done = False

		return all_done

	def overrideBuilds(self, branches, name):
		print "Overriding builds for branches: %s" % ",".join(branches)

		all_done = True
		for branch in branches:
			print "Branch %s" % branch
			print "Overriding..."
			err = self.sc.overrideBuild(branch, name)
			if err != "":
				print "%s: %s" % (branch, err)
				all_done = False

		return all_done

	def waitForOverrides(self, branches, name):
		print "Waiting for overrided builds for branches: %s" % ",".join(branches)

		all_done = True
		for branch in branches:
			print "Branch %s" % branch
			print "Waiting..."
			err = self.sc.waitForOverrideBuild(branch, name)
			if err != "":
				print "%s: %s" % (branch, err)
				all_done = False

		return all_done

	def cherryPickMaster(self, branches, verbose=True, start_commit="", depth=20):
		err = []
		gcp_commits = ["master"]
		if start_commit != "":
			if verbose:
				print "Switching to master branch"

			_, _, rc = self.llc.runFedpkgSwitchBranch('master')
			if rc != 0:
				err.append("Unable to switch to master branch")
				return err

			if verbose:
				print "Searching for %s commit in the last %s commits" % (start_commit, depth)

			e, commits = self.sc.getGitCommits(depth)
			if e != "":
				err.append(e)
				return err

			try:
				index = commits.index(start_commit)
				gcp_commits = commits[:index + 1]
				gcp_commits = gcp_commits[::-1]
			except ValueError:
				err.append("Commit %s not found in the last %s commits" % (start_commit, depth))
				return err

			if verbose:
				print "Commits found:"
				for commit in gcp_commits:
					print commit

	def mergeMaster(self, branches, verbose=True):
		print "Merging branches: %s" % ",".join(branches)

		err = []

		for branch in branches:
			if branch == "master":
				continue

			_, _, rc = self.llc.runFedpkgSwitchBranch(branch)
			if rc != 0:
				err.append("Unable to switch to %s branch" % branch)
				err.append("Skipping %s branch" % branch)
				if verbose:
					print "\n".join(err)
				continue

			if verbose:
				print "Switched to %s branch" % branch

			se = self.sc.mergeMaster()
			if se != "":
				err.append("%s: unable to git merge master: %s" % (branch, se))
				if verbose:
					print err[-1]

				return err

		return err

	def resetBranchesToOrigin(self, branches):
		for branch in branches:
			_, _, rc = self.llc.runFedpkgSwitchBranch(branch)
			if rc != 0:
				print "Warning: unable to switch to %s branch" % branch
				print "Skipping %s branch" % branch
				continue

			print "Switched to %s branch" % branch
			so, se, rc = self.llc.runGitReset(branch)


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

STEP_END=9

class PhaseMethods:

	def __init__(self, dry=False, debug=False):
		self.phase = STEP_END
		self.endphase = STEP_END
		self.mc = MultiCommand(dry=dry, debug=debug)
		self.branches = Config().getBranches()

	def setBranches(self, branches):
		self.branches = branches

	def startWithScratchBuild(self):
		self.phase = STEP_SCRATCH_BUILD

	def stopWithScratchBuild(self):
		self.endphase = STEP_SCRATCH_BUILD

	def startWithPush(self):
		self.phase = STEP_PUSH

	def stopWithPush(self):
		self.endphase = STEP_PUSH

	def startWithBuild(self):
		self.phase = STEP_BUILD

	def stopWithBuild(self):
		self.endphase = STEP_BUILD

	def startWithUpdate(self):
		self.phase = STEP_UPDATE

	def stopWithUpdate(self):
		self.endphase = STEP_UPDATE

	def runPhase(self, phase):
		if phase == STEP_SCRATCH_BUILD:
			return self.mc.scratchBuildBranches(self.branches)

		if phase == STEP_PUSH:
			return self.mc.pushBranches(self.branches)

		if phase == STEP_BUILD:
			return self.mc.buildBranches(self.branches)

		if phase == STEP_UPDATE:
			branches = Config().getUpdates()
			branches = list(set(branches) & set(self.branches))
			return self.mc.updateBranches(branches)

		return 1

	def getPhaseName(self, phase):
		if phase == STEP_SCRATCH_BUILD:
			return "Scratch build phase"

		if phase == STEP_PUSH:
			return "Push phase"

		if phase == STEP_BUILD:
			return "Build phase"

		if phase == STEP_UPDATE:
			return "Update phase"

		return ""	

	def run(self):

		for i in range(1, self.endphase + 1):
			if i < self.phase:
				continue

			phase_name = self.getPhaseName(i)
			if phase_name == "":
				print "Phase %s unknown" % i
				break

			print 60*"#"
			sl = len(phase_name)
			print ((60-sl)/2)*" " + phase_name
			print 60*"#"
			print ""

			if not self.runPhase(i):
				break	

