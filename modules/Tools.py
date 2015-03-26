from Utils import runCommand
from Config import Config
import os
import threading
import subprocess

####################### build and scratch build routines ######################

def makeSRPM():
	so, se, rc = runCommand("fedpkg srpm")
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

def runBuild():
	so, se, rc = runCommand("fedpkg build --nowait")
	if rc != 0:
		return -1

	task_lines = filter(lambda l: l.startswith("Created task:"), so.split("\n"))
	if len(task_lines) != 1:
		return -1

	task_id = task_lines[0].strip().split(" ")[-1]
	if task_id.isdigit():
		return int(task_id)

	return -1

def runScratchBuild(srpm):
	so, se, rc = runCommand("fedpkg scratch-build --nowait --srpm=%s" % srpm)
	if rc != 0:
		return -1

	task_lines = filter(lambda l: l.startswith("Created task:"), so.split("\n"))
	if len(task_lines) != 1:
		return -1

	task_id = task_lines[0].strip().split(" ")[-1]
	if task_id.isdigit():
		return int(task_id)

	return -1

def _buildBranches(branches, scratch=True):

	task_ids = {}

	# init [scratch] builds
	for branch in branches:
		print "Branch %s" % branch
		so, _, rc = runCommand("fedpkg switch-branch %s" % branch)
		if rc != 0:
			print "Unable to switch to %s branch" % branch
			continue

		srpm = ""
		if scratch:
			srpm = makeSRPM()
			if srpm == "":
				print "Unable to create srpm"
				continue

		task_id = -1
		if scratch:
			task_id = runScratchBuild(srpm)
		else:
			task_id = runBuild()

		if task_id == -1:
			print "Unable to initiate task"
			continue

		task_ids[branch] = task_id
		
		if scratch:
			print "Scratch build http://koji.fedoraproject.org/koji/taskinfo?taskID=%s initiated" % task_id
		else:
			print "Build http://koji.fedoraproject.org/koji/taskinfo?taskID=%s initiated" % task_id

	return task_ids

class WatchTaskThread(threading.Thread):
	def __init__(self, task_id):
		super(WatchTaskThread, self).__init__()
		self.task_id = task_id
		self.err = ""

	def run(self):
		runCommand("koji watch-task %s --quiet" % self.task_id)

	def getError(self):
		return self.err

def _waitForTasks(task_ids):

	thread_list = {}
	for branch in task_ids:
		task_id = task_ids[branch]
		print "Watching %s branch, http://koji.fedoraproject.org/koji/taskinfo?taskID=%s" % (branch, task_id)
		thread_list[branch] = WatchTaskThread(task_id)
		thread_list[branch].start()

	for branch in task_ids:
		thread_list[branch].join()
		err = thread_list[branch].getError()
		if err != "":
			print err

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

def _checkTasks(task_ids):
	all_done = True
	print "Checking finished tasks..."
	thread_list = {}
	for branch in task_ids:
		task_id = task_ids[branch]
		thread_list[branch] = WaitTaskThread(task_id)
		thread_list[branch].start()

	for branch in task_ids:
		thread_list[branch].join()

	for branch in task_ids:
		if thread_list[branch].getState():
			print "%s: closed" % branch
		else:
			all_done = False
			print "%s: failed" % branch

	return all_done

def scratchBuildBranches(branches):
	# init [scratch] builds
	task_ids = _buildBranches(branches)
	print ""

	# wait for builds
	_waitForTasks(task_ids)
	print ""

	# check out builds
	return _checkTasks(task_ids)

def buildBranches(branches):

	# init [scratch] builds
	task_ids = _buildBranches(branches, scratch=False)
	print ""

	# wait for builds
	_waitForTasks(task_ids)
	print ""

	# check out builds
	return _checkTasks(task_ids)

####################### pull, push and update routines ########################

def pullBranch(branch):
	so, se, rc = runCommand("git pull")
	if rc != 0:
		return se

	return ""

def pushBranch(branch):
	so, se, rc = runCommand("fedpkg push")
	if rc != 0:
		return se

	return ""

def updateBranch(branch):
	subprocess.call("fedpkg update", shell=True)
	return ""

def pullBranches(branches):
	print "Pulling from branches: %s" % ", ".join(branches)
	all_done = True
	for branch in branches:
		print "Branch %s" % branch
		so, _, rc = runCommand("fedpkg switch-branch %s" % branch)
		if rc != 0:
			print "Unable to switch to %s branch" % branch
			all_done = False
			continue

		err = pullBranch(branch)
		if err != "":
			print "%s: %s" % (branch, err)
			all_done = False

	return all_done

def pushBranches(branches):
	print "Pushing to branches: %s" % ",".join(branches)
	all_done = True
	for branch in branches:
		print "Branch %s" % branch
		so, _, rc = runCommand("fedpkg switch-branch %s" % branch)
		if rc != 0:
			print "Unable to switch to %s branch" % branch
			all_done = False
			continue

		err = pushBranch(branch)
		if err != "":
			print "%s: %s" % (branch, err)
			all_done = False

	return all_done

def updateBranches(branches):
	print "Pushing to branches: %s" % ",".join(branches)
	all_done = True
	for branch in branches:
		print "Branch %s" % branch
		so, _, rc = runCommand("fedpkg switch-branch %s" % branch)
		if rc != 0:
			print "Unable to switch to %s branch" % branch
			all_done = False
			continue

		err = updateBranch(branch)
		if err != "":
			print "%s: %s" % (branch, err)
			all_done = False

	return all_done

####################### git cherry-pick from master ###########################
def cherryPickMaster(branches, verbose=True):
	err = []
	for branch in branches:
		if branch == "master":
			continue

		_, _, rc = runCommand("fedpkg switch-branch %s" % branch)
		if rc != 0:
			err.append("Unable to switch to %s branch" % branch)
			err.append("Skipping %s branch" % branch)
			if verbose:
				print "\n".join(err)
			continue

		if verbose:
			print "Switched to %s branch" % branch

		_, se, rc = runCommand("git cherry-pick master")
		if rc != 0:
			err.append("%s: unable to cherry pick master: %s" % (branch, se))
			if verbose:
				print err[-1]

	return err

def resetBranchesToOrigin(branches):
	for branch in branches:
		_, _, rc = runCommand("fedpkg switch-branch %s" % branch)
		if rc != 0:
			print "Warning: unable to switch to %s branch" % branch
			print "Skipping %s branch" % branch
			continue

		print "Switched to %s branch" % branch
		so, se, rc = runCommand("git reset --hard remotes/origin/%s" %
			branch)

if __name__ == "__main__":

	branches = Config().getBranches()
	#cherryPickMaster(branches)
	#resetBranchesToOrigin(branches)

