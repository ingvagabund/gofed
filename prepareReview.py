import os.path
import optparse
from modules.Config import Config
from modules.SpecParser import SpecParser
import shutil
from os.path import expanduser
from modules.Utils import runCommand
from glob import glob

if __name__ == "__main__":
	parser = optparse.OptionParser("%prog")

	parser.add_option(
	    "", "-u", "--user", dest="user", default = "",
	    help = "FAS username"
        )

	parser.add_option(
	    "", "", "--skip-koji", dest="skipkoji", action = "store_true", default = False,
	    help = "don't run koji build"
        )

	parser.add_option(
	    "", "", "--skip-rpmlint-errors", dest="skiprpmlint", action = "store_true", default = False,
	    help = "skip rpmlint errors if any"
        )

	parser.add_option(
	    "", "", "--just-update", dest="justupdate", action = "store_true", default = False,
	    help = "Update only spec file, no build, no rpmlint"
        )

	parser.add_option(
	    "", "", "--just-build", dest="justbuild", action = "store_true", default = False,
	    help = "Build spec file only"
        )

	options, args = parser.parse_args()

	phase_build = True
	srpm_only = False
	phase_koji = True
	phase_upload = True
	phase_review = True

	if options.justbuild:
		phase_koji = False
		phase_upload = False
		phase_review = False

	if options.justupdate:
		phase_build = False
		phase_koji = False
		srpm_only = True
		phase_review = False

	if options.skipkoji:
		phase_koji = False

	# no args => take the spec file from the current directory
	if len(args) == 0:
		specfiles = glob("*.spec")
		if len(specfiles) != 1:
			print "Synopsis: [--user=USER|-u USER] [--skip-koji] SPEC"
			exit(1)
		specfile = specfiles[0]
	else:
		specfile = args[0]

	user = options.user
	if user == "":
		user = Config().getFASUsername()

	if not os.path.exists(specfile):
		print "Spec file %s not found" % specfile
		exit(1)

	obj = SpecParser(specfile)
	if not obj.parse():
		print obj.getError()
		exit(1)

	provider = obj.getMacro("provider")
	repo = obj.getMacro("repo")
	if provider == "google":
		commit = obj.getMacro("rev")
	else:
		commit = obj.getMacro("commit")
	summary = obj.getTag("summary")
	name = obj.getTag("name")

	print "Parsing %s file" % specfile
	print "  Provider: %s" % provider
	print "  Repo: %s" % repo
	print "  Commit: %s" % commit
	print "  Name: %s" % name
	print "  Summary: %s" % summary
	print ""

	if provider == "":
		print "Provider macro is missing"
		exit(1)
	if repo == "":
		print "Repo macro is missing"
		exit(1)
	if commit == "":
		print "Commit macro is missing"
		exit(1)
	if name == "":
		print "Name tag is missing"
		exit(1)
	if summary == "":
		print "Summary tag is missing"
		exit(1)

	if provider == "bitbucket":
		tarball = "%s.zip" % commit[:12]
	elif provider == "google":
		tarball = "%s.tar.gz" % (commit)
	else:
		tarball = "%s-%s.tar.gz" % (repo, commit[:7])

	spec_dir = os.path.dirname(specfile);
	if spec_dir == "":
		spec_dir = "."

	if phase_build or srpm_only:
		# copy tarball to ~/rpmbuild/SOURCES
		print "Copying tarball %s to %s/rpmbuild/SOURCES" % ("%s/%s" % (spec_dir, tarball), expanduser("~"))
		try:
			shutil.copyfile("%s/%s" % (spec_dir, tarball), '%s/rpmbuild/SOURCES/%s' % (expanduser("~"), tarball))
		except IOError, e:
			print "Unable to copy tarball %s: %s" % (tarball, e)
			exit(1)

		# copy patches if available
		for patch in glob("%s/*.patch" % spec_dir):
			print "Copying patch %s to %s/rpmbuild/SOURCES" % (patch, expanduser("~"))
			try:
				shutil.copyfile(patch, '%s/rpmbuild/SOURCES/%s' % (expanduser("~"), patch))
			except IOError, e:
				print "Unable to copy patch %s: %s" % (patch, e)
				exit(1)

		print ""

		# build spec file
		print "Building spec file using rpmbuild"
		if srpm_only:
			so, se, rc = runCommand("rpmbuild -bs %s" % specfile)
		else:
			so, se, rc = runCommand("rpmbuild -ba %s" % specfile)

		if rc != 0:
			print "  Build failed. Check build.log."
			print "  Error: %s" % se
			exit(1)

		# line with builds end with .rpm sufix and consists of two columns seperated by whitespace
		# in a form "text: pathtorpm.rpm"
		builds = filter(lambda l: l.endswith(".rpm") and len(l.split(" ")) == 2, so.split("\n"))
		builds = map(lambda l: l.split(" ")[1], builds)
		srpm = filter(lambda l: l.endswith("src.rpm"), builds)[0]

		for build in builds:
			print "  %s" % build
		print ""

		# rpmlint
		print "Running rpmlint %s" % " ".join(builds)
		so, se, rc = runCommand("rpmlint %s" % " ".join(builds))

		rpmlint = so
		print so

		if rc != 0 and not options.skiprpmlint:
			print "Unable to run rpmlint: %s" % se
			exit(1)

	# build in koji
	if phase_koji:
		print "Running koji scratch build on srpm"
		print "koji build --scratch rawhide %s --nowait" % srpm
		so, se, rc = runCommand("koji build --scratch rawhide %s --nowait" % srpm)
		if rc != 0:
			print "Unable to run scratch build: %s" % se
			exit(1)

		task = filter(lambda l: l.startswith("Created task: "), so.split("\n"))
		if task == []:
			print "Unable to get task id"
			exit(1)

		task_id = task[0].split("Created task: ")[1]

		print "  Watching rawhide build, http://koji.fedoraproject.org/koji/taskinfo?taskID=%s" % task_id

		print "koji watch-task %s --quiet" % task_id
		_, _, rc = runCommand("koji watch-task %s --quiet" % task_id)
		if rc != 0:
			print "Koji watch task failed"
			exit(1)

		so, se, rc = runCommand("koji taskinfo %s" % task_id)
		if rc != 0:
			print "Unable to get task info: %s" % se
			exit(1)

		state = filter(lambda l: l.startswith("State"), so.split("\n"))
		if state == []:
			print "Unable to get task state"
			exit(1)

		state = state[0].split("State: ")[1].lower()
		if state != "closed":
			print "  koji scratch build failed"
			exit(1)

	if phase_build:
		# parse data for review request for bugzilla
		so, se, rc = runCommand("rpm -qpi %s" % srpm)
		if rc != 0:
			print "Unable to get info from srpm: %s" % se
			exit(1)

		# description is the last item
		index = 0
		lines = so.split("\n")
		for line in lines:
			if not line.startswith("Description"):
				index +=1
				continue
			break

		description = "\n".join(lines[index+1:-1])

	if phase_upload:
		# upload the srpm to my fedora account
		rc = 0
		print "Uploading srpm and spec file to @fedorapeople.org"
		print '%s@fedorapeople.org "mkdir -p public_html/reviews/%s"' % (user, name)
		so, se, rc = runCommand('ssh %s@fedorapeople.org "mkdir -p public_html/reviews/%s"' % (user, name))
		if rc != 0:
			print "Unable to create public_html/reviews/%s dir: %s" % (name, se)
			exit(1)

		print "scp %s %s@fedorapeople.org:public_html/reviews/%s/." % (srpm, user, name)
		so, se, rc = runCommand("scp %s %s@fedorapeople.org:public_html/reviews/%s/." % (srpm, user, name))
		if rc != 0:
			print "Unable to copy srpm to fedorapeople.org: %s" % se
			exit(1)

		print "scp %s %s@fedorapeople.org:public_html/reviews/%s/." % (specfile, user, name)
		so, se, rc = runCommand("scp %s %s@fedorapeople.org:public_html/reviews/%s/." % (specfile, user, name))
		if rc != 0:
			print "Unable to copy spec file to fedorapeople: %s" % se
			exit(1)

		print ""
		print ""

	if phase_review:
		# generate summary and header information
		print "Generating Review Request"
		print "###############################################################"
		print "Review Request: %s - %s" % (name, summary)
		print "###############################################################"
		print "Spec URL: https://%s.fedorapeople.org/reviews/%s/%s" % (user, name, os.path.basename(specfile))
		print ""
		print "SRPM URL: https://%s.fedorapeople.org/reviews/%s/%s" % (user, name, os.path.basename(srpm))
		print ""
		print "Description: %s" % description
		print ""
		print "Fedora Account System Username: %s" % user
		print ""
		if not options.skipkoji:
			print "Koji: http://koji.fedoraproject.org/koji/taskinfo?taskID=%s" % task_id
			print ""
		print "$ rpmlint %s" % " ".join(map(lambda l: os.path.basename(l), builds))
		print rpmlint
		print "###############################################################"
		print ""
		print ""
		print "Enter values at: https://bugzilla.redhat.com/enter_bug.cgi?product=Fedora&format=fedora-review"
