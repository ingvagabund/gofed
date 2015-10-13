# update spec-2.0 to spec-2.1

import sys

if len(sys.argv) != 2:
	print "Missing spec file"
	exit(1)

specfile = sys.argv[1]

lines = []
with open(specfile, "r") as file:
	lines = file.read().split("\n")

class LinePrinter(object):

	def __init__(self, file = ""):
		self.lines = []
		self.file = file

	def write(self, line):
		self.lines.append(line)

	def flush(self):
		if self.file != "":
			with open(self.file, "w") as spec:
				for line in self.lines:
					 spec.write("%s\n" % line)
		else:
			for line in self.lines:
				print line

copying_on = False
exclusive_on = 0
buildrequires_on = False
root_dir_own_on = False
install_for_on = False
gotest_definition = False
after_check = False
file_first_hit = False

lp = LinePrinter(specfile)

for line in lines:
	# print every devel subpackage name
	if line.startswith("%package"):
		print line

	# remove copying macro
	if not copying_on and line.startswith("%define copying"):
		copying_on = True
		continue

	# as long as there is no empty new line, drop lines
	if copying_on:
		if line != "":
			continue
		copying_on = False
		continue

	# replace ExclusiveArch for main package
	if exclusive_on == 0 and line.startswith("# If go_arches not defined fall through to implicit golang archs"):
		exclusive_on = 1
		continue

	if exclusive_on == 1:
		if line != "%endif":
			continue
		exclusive_on = 2
		lp.write("# e.g. el6 has ppc64 arch without gcc-go, so EA tag is required")
		lp.write("ExclusiveArch:  %{?go_arches:%{go_arches}}%{!?go_arches:%{ix86} x86_64 %{arm}}")
		continue

	# remove ExclusiveArch for unit-test subpackage
	if exclusive_on == 2 and line.startswith("# If go_arches not defined fall through to implicit golang archs"):
		exclusive_on = 3
		continue

	if exclusive_on == 3:
		if line != "%endif":
			continue
		exclusive_on = 4
		continue

	if not buildrequires_on and line.startswith("# If gccgo_arches does not fit or is not defined fall through to golang"):
		buildrequires_on = True
		continue

	if buildrequires_on:
		if line != "%endif":
			continue
		buildrequires_on = False
		lp.write("# If go_compiler is not set to 1, there is no virtual provide. Use golang instead.")
		lp.write("BuildRequires:  %{?go_compiler:compiler(go-compiler)}%{!?go_compiler:golang}")
		continue

	# add root directory to devel.file-list
	if not root_dir_own_on and line.startswith("install -d -p %{buildroot}/%{gopath}/src/%{import_path}/"):
		root_dir_own_on = True
		lp.write(line)
		lp.write("echo \"%%dir %%{gopath}/src/%%{import_path}/.\" >> devel.file-list")
		continue

	# generate unit-test only of devel is
	if line.startswith("%if 0%{?with_unit_test}"):
		lp.write("%if 0%{?with_unit_test} && 0%{?with_devel}")
		continue

	# devel owns every directory of source code (even of tests)
	if not install_for_on and line.startswith("for file in"):
		install_for_on = True
		lp.write(line)
		continue

	if install_for_on:
		lp.write("    echo \"%%dir %%{gopath}/src/%%{import_path}/$(dirname $file)\" >> devel.file-list")
		lp.write(line)
		install_for_on = False
		continue

	# add sort-unit on devel.file-list
	if line.startswith("%check"):
		lp.write("%if 0%{?with_devel}")
		lp.write("sort -u -o devel.file-list devel.file-list")
		lp.write("%endif\n")
		lp.write(line)
		after_check = True
		continue

	# remove definition of gotest if defined
	if not gotest_definition and line.startswith("%ifarch 0%{?gccgo_arches}"):
		gotest_definition = True
		continue

	if gotest_definition:
		if line != "":
			continue
		gotest_definition = False
		continue

	# update definition of GOPATH for tests (add if else for with_bundled macro)
	if after_check and line.startswith("export GOPATH"):
		lp.write("%if ! 0%{?with_bundled}")
		lp.write("export GOPATH=%{buildroot}/%{gopath}:%{gopath}")
		lp.write("%else")
		lp.write("export GOPATH=%{buildroot}/%{gopath}:$(pwd)/Godeps/_workspace:%{gopath}")
		lp.write("%endif\n")
		lp.write("%if ! 0%{?gotest:1}")
		lp.write("%global gotest go test")
		lp.write("%endif\n")
		continue

	# change gotest -> %gotest
	if after_check and "gotest %{import_path}" in line:
		lp.write(line.replace("gotest", "%gotest"))
		continue

	# remove %dir %{gopath}/src/%{import_path} from all %files sections
	if after_check and line.startswith("%dir %{gopath}/src/%{import_path}"):
		continue

	
	# replace %copying to license
	if after_check and not file_first_hit and line.startswith("%if 0%{?with_devel}"):
		file_first_hit = False
		lp.write("#define license tag if not already defined")
		lp.write("%{!?_licensedir:%global license %doc}\n")
		lp.write(line)
		continue

	if after_check:
		lp.write(line.replace("%copying", "%license"))
		continue

	lp.write(line)

lp.flush()
