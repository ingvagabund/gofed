from Utils import getScriptDir, runCommand, inverseMap
import re
import os
import tempfile
import shutil
from Repos import detectRepoPrefix
from ImportPaths import loadImportPathDb
import operator
from GoSymbols import ProjectToXml
from specParser import getPkgURL, fetchProvides
from Repos import Repos, IPMap
from xml.dom import minidom
from xml.dom.minidom import Node

GOLANG_PACKAGES="data/golang.packages"
GOLANG_PKG_DB="data/pkgdb"
script_dir = getScriptDir() + "/.."

def loadPackages():
	packages = []
	with open("%s/%s" % (script_dir, GOLANG_PACKAGES), "r") as file:
		for line in file.read().split('\n'):
			line = line.strip()
			if line == '' or line[0] == '#':
				continue

			packages.append(line)
	return packages

# detect if it packages is already in pkgdb
def packageInPkgdb(pkg):
	_, _, rt = runCommand("git ls-remote http://pkgs.fedoraproject.org/cgit/" + pkg + ".git/")

	if rt == 0:
		return True

	return False

class Package:

	def __init__(self, pkg_name):
		self.pkg_name = pkg_name
		self.latest_build = ""
		self.other_builds = []
		self.initTempDir()
		cwd = os.getcwd()
		os.chdir(self.tmp_dir)
		self.downloadBuilds()
		self.info = self.analyzeBuilds()
		os.chdir(cwd)
		self.clearTempDir()

	def getLatestBuilds(self, tag = 'rawhide'):
		so, _, rc = runCommand("koji -q latest-build %s %s" % (tag, self.pkg_name))
		if rc != 0:
			return ''
		return re.sub(r'[ \t]+', ' ', so.strip()).split(' ')[0]

	def downloadBuilds(self, tag = 'rawhide'):
		"""
		Download all builds in the currect directory
		"""
		self.latest_build = self.getLatestBuilds(tag)
		if self.latest_build == "":
			return False

		so, se, rc = runCommand("koji download-build %s" % self.latest_build)
		if rc != 0:
			return False

		return True

	def analyzeDevelBuild(self, name):
		"""
		Expects build in the current directory
		"""

		# create build directory in the current directory
		cwd = os.getcwd()
		if os.path.exists("%s/%s" % (cwd, 'build')):
			return {}

		_, _, rc = runCommand("mkdir build")
		if rc != 0:
			return {}

		os.chdir('build')
		runCommand('rpm2cpio ../%s | cpio -idmv' % name)

		# scan builds using native golang parser
		package_xml = ProjectToXml("", "%s/%s" % (os.getcwd(), 'usr/share/gocode/src/'), self.latest_build)

		return {
			"xmlobj": package_xml
			}
	
	def analyzeBuilds(self):
		"""
		For each build return its import paths and provides,
		which are computed from source codes, not from quering a build.
		"""

		builds = {}

		so, _, _ = runCommand("ls")
		
		for line in so.split('\n'):
			line = line.strip()

			if line == '':
				continue

			# from N-V-R get name
			parts = line.split('-')

			if len(parts) < 3:
				continue

			name = "-".join(parts[:-2])

			# all devel packages should end with devel sufix
			if name.endswith('devel'):
				info = self.analyzeDevelBuild(line)
				if info != {}:
					builds[name] = info
			# but some does not have to
			# 1) must be binary free or not? Maybe scripts are allowed?
			# 2) must contain at least one package different from
			#    example*, main
			else:
				info = self.analyzeDevelBuild(line)
				if info == {} or "xmlobj" not in info:
					continue

				if self.isBuildMinimalDevel(info["xmlobj"]):
					builds[name] = info
				else:
					self.other_builds.append(name)

		return builds

	def isBuildMinimalDevel(self, xmlobj):
		if not xmlobj.getStatus():
			return False

		root = xmlobj.getProject()
		# xml is valid
		pkgs = None
		imports = None
		for node in root:
			if node.tag == "packages":
				pkgs = node
			elif node.tag == "imports":
				imports = node

		# find at least one packages not starting with example prefix
		# main is filter out during parsing
		for pkg in pkgs:
			if pkg.tag != "package":
				continue

			pkg_name = os.path.basename(pkg.get("importpath"))

			if pkg_name.startswith("example"):
				continue

			return True

		return False

	def getOtherBuilds(self):
		return self.other_builds

	def initTempDir(self):
		self.tmp_dir = tempfile.mkdtemp()
		
	def clearTempDir(self):
		shutil.rmtree(self.tmp_dir)

	def getInfo(self):
		return self.info

def savePackageInfo(pkg_info):
	errs = []
	for build in pkg_info:
		obj = pkg_info[build]["xmlobj"]
		if not obj.getStatus():
			errs.append("Warning: unable to parse %s. Error: %s" % (build, obj.getError()))
			continue

		with open("%s/%s/%s.xml" % (script_dir, GOLANG_PKG_DB, build), "w") as f:
			f.write(str(obj))

	return errs

def getPackagesFromPkgDb():
	so, _, rc = runCommand("koji search --regex package '^golang-'")
	if rc != 0:
		return []

	pkgs = []

	for line in so.split('\n'):
		line = line.strip()

		if line == "":
			continue

		line = line.strip()
		pkgs.append(line)

	return pkgs

# based on http://www.fit.vutbr.cz/study/courses/GAL/public/gal-slides.pdf
def transposeGraph(graph):
	nodes, edges = graph
	tedges = {}
	for u in edges:
		for v in edges[u]:
			# (u,v) -> (v,u)
			if v not in tedges:
				tedges[v] = [u]
			else:
				tedges[v].append(u)

	return (nodes, tedges)

class DFS:

	def __init__(self, graph):
		self.nodes, self.edges = graph

		self.WHITE=0
		self.GRAY=1
		self.BLACK=2

		self.color = {}
		self.d = {}
		self.f = {}
		self.time = 0
		self.pred = {}



	def DFSVisit(self, node):
		self.color[node] = self.GRAY
		self.time += 1
		self.d[node] = self.time

		if node in self.edges:
			for adj in self.edges[node]:
				if self.color[adj] == self.WHITE:
					self.pred[adj] = node
					self.DFSVisit(adj)

		self.color[node] = self.BLACK
		self.time += 1
		self.f[node] = self.time

	def DFSSimpleWalk(self, start_node):
		for node in self.nodes:
			self.color[node] = self.WHITE
			self.pred[node] = ""

		self.time = 0
		self.DFSVisit(start_node)

		reachable = []		
		for node in self.nodes:
			if self.color[node] != self.WHITE:
				reachable.append(node)

		return reachable

	def DFSWalk(self, f = []):
		for node in self.nodes:
			self.color[node] = self.WHITE
			self.pred[node] = ""

		self.time = 0

		if f == []:
			for node in self.nodes:
				if self.color[node] == self.WHITE:
					self.DFSVisit(node)
			return (self.f, self.d)
		else:
			start_nodes = []
			for node, _ in sorted(f.items(), key=operator.itemgetter(1), reverse=True):
				if self.color[node] == self.WHITE:
					self.DFSVisit(node)
				start_nodes.append(node)

			return (start_nodes, self.pred)

def getSucc(s, pred):
	if pred[s] == '':
		return [s]
	else:
		return [s] + getSucc(pred[s], pred)

def getSCC(graph):
	nodes, edges = graph
	f, d = DFS(graph).DFSWalk()
	tgraph = transposeGraph(graph)
	start_nodes, pred = DFS(tgraph).DFSWalk(f)
	trees = []
	for node in start_nodes:
		trees.append(getSucc(node, pred))

	# some trees can overlap
	scc = []
	for i_tree in trees:
		iss = False
		for j_tree in trees:
			if i_tree == j_tree:
				continue
			if set(i_tree).issubset(j_tree):
				iss = True
		if iss == False:
			scc.append(i_tree)

	return scc

class ConnectedComponent:
	def __init__(self, graph, node):
		self.nodes, self.edges = graph
		dfs = DFS(graph)
		self.reacheable = dfs.DFSSimpleWalk(node)

	def getCC(self):
		edges = {}
		for u in self.reacheable:
			if u not in self.edges:
				continue

			edges[u] = []
			for v in self.edges[u]:
				if v in self.reacheable:
					edges[u].append(v)

		return (self.reacheable, edges)

def joinGraphs(g1, g2):
	g1_nodes, g1_edges = g1
	g2_nodes, g2_edges = g2

	nodes = g1_nodes
	edges = g1_edges

	for u in g2_nodes:
		if u not in nodes:
			nodes.append(u)

		if u not in g2_edges:
			continue

		for v in g2_edges[u]:
			if u in edges:
				if v in edges[u]:
					continue
				edges[u].append(v)
			else:
				edges[u] = [v]

	return (nodes, edges)


def buildRequirementGraph(verbose=False):
	# load imported and provided paths
	ip_provides, ip_imports, pkg_devel_main_pkg = loadImportPathDb()
	# 1) for each package get a list of all packages it needs
	# 2) in this list find all cyclic dependencies

	# create mapping of import paths of provides to pkg_devel_name
	provides_mapping = {}
	pkgs = []
	for pkg_devel in ip_provides:
		pkgs.append(pkg_devel)
		for ip in ip_provides[pkg_devel]:
			if ip == "":
				continue

			provides_mapping[ip] = pkg_devel



	#print provides_mapping
	#pkgs = list(set(pkgs))
	#for line in sorted(pkgs):
	#	print line

	# Assuming all dependencies will create a sparse matrix, lets use a list of edges instead
	# (u, v) \in Pkgs \times Pkgs \eq u [B]R v (u needs v)
	edges = {}
	for pkg_devel in ip_imports:
		for ip in ip_imports[pkg_devel]:
			if ip == "":
				continue

			if ip not in provides_mapping:
				if verbose:
					print "Error: %s path of %s subpackage is not provided by any package" % (ip, pkg_devel)
				continue

			if pkg_devel not in edges:
				edges[pkg_devel] = [provides_mapping[ip]]
			else:
				if provides_mapping[ip] not in edges[pkg_devel]:
					edges[pkg_devel].append(provides_mapping[ip])

	return (pkgs, edges), pkg_devel_main_pkg

def getLeafPackages(graph):
	nodes, edges = graph

	leaves = []

	for u in nodes:
		# u has no edges or edges[u] is empty
		if u not in edges or edges[u] == []:
			leaves.append(u)

	return leaves

def getRootPackages(graph):
	nodes, edges = graph

	roots = []

	visited = {}
	for u in nodes:
		visited[u] = 0

	for u in nodes:
		if u in edges:
			for v in edges[u]:
				visited[v] = 1

	for u in nodes:
		if visited[u] == 0:
			roots.append(u)

	return roots

def compareNVRs(nvr1, nvr2):
	so, se, rc = runCommand("rpmdev-vercmp %s %s" % (nvr1, nvr2))
	if rc != 0:
		# if the command is not working => nvr1 < nvr2
		return 1;

	so = so.split("\n")[0]
	if "<" in so:
		return -1
	elif ">" in so:
		return 1
	return 0

class LocalDB:

	def __init__(self):
		self.local_pkgs = []

	def loadPackages(self):
		packages = []
		with open("%s/%s" % (script_dir, GOLANG_PACKAGES), "r") as file:
			for line in file.read().split('\n'):
				line = line.strip()
				if line == '' or line[0] == '#':
					continue

				if line not in packages:
					packages.append(line)
		return packages

	def savePackages(self, packages):
		if packages == []:
			return False

		with open("%s/%s.tmp" % (script_dir, GOLANG_PACKAGES), "w") as file:
			for pkg in packages:
				file.write("%s\n" % pkg)	

		return True

	def flush(self):
		os.rename("%s/%s.tmp" % (script_dir, GOLANG_PACKAGES),
			"%s/%s" % (script_dir, GOLANG_PACKAGES))

	# 1) get a list of new packages
	# 2) add the list into golang.packages
	# 3) update golang.repos (detect import path from import_path macro)
	# 4) update golang.imap for mapping of import paths into their builds (devel packages)
	# 5) regenerate golang.importdb (or remove it and use pkg?)
	# -- if possible, regenerate only a part of golang.importdb/pkg only for new packages
	def addPackages(self, new_packages):
		err = []

		if new_packages == []:
			err.append("No new packages to add")
			return err, False

		# update golang.repos
		new_repos = {}

		checked_packages = []
		for pkg in new_packages:
			url = getPkgURL(pkg)
			if url == "":
				err.append("Unable to get URL tag from %s's spec file" % pkg)	
				continue

			# remove all / at the end of url
			url = re.sub(r'[/]+$', '', url)
			# change http to https
			url = re.sub(r'^http://', 'https://', url)
			if not url.startswith('https://'):
				url = "https://%s" % url

			# remove godoc.org/
			url = re.sub(r'https://godoc.org/', 'https://', url)

			checked_packages.append(pkg)
			# BUILD   go-spew https://github.com/davecgh/go-spew.git
			dir = os.path.basename(url)
			# git or hg?
			repo = ""
			# github
			if url.startswith("https://github.com"):
				repo = "%s.git" % url
			# bitbucker, googlecode, ...
			else:
				repo = url

			new_repos[pkg] = (dir, repo)

		new_packages = checked_packages

		# get current packages
		curr_pkgs = self.loadPackages()
		for pkg in new_packages:
			curr_pkgs.append(pkg)

		# add new packages
		if not self.savePackages(sorted(curr_pkgs)):
			err.append("Unable to save new packages")
			return err, False


		repos = Repos().loadRepos()
		for repo in new_repos:
			repos[repo] = new_repos[repo]

		if not Repos().saveRepos(repos):
			err.append("Unable to save new repositories")
			return err, False

		# update import paths
		mapping = IPMap().loadIMap()

		for pkg in new_packages:
			provides = fetchProvides(pkg, 'master')
			imap = inverseMap(provides)
			for arg in imap:
				for image in imap[arg]:
					mapping[arg] = (pkg, image)

		if not IPMap().saveIMap(mapping):
			err.append("Unable to save mapping of import paths of new packages")
			return err, False

		self.flush()
		Repos().flush()
		IPMap().flush()
		return err, True

	def updatePackages(self, outdated_packages):
		err = []

		if outdated_packages == []:
			err.append("No outdated packages to add")
			return err, False

		# update import paths
		mapping = IPMap().loadIMap()

		for pkg in outdated_packages:
			provides = fetchProvides(pkg, 'master')
			imap = inverseMap(provides)
			for arg in imap:
				for image in imap[arg]:
					mapping[arg] = (pkg, image)

		if not IPMap().saveIMap(mapping):
			err.append("Unable to save mapping of import paths of updated packages")
			return err, False

		IPMap().flush()
		return err, True

	def loadLatestBuilds(self, cache=False):
		if cache:
			return self.loadBuildsFromCache()

		builds = {}
		for dirName, subdirList, fileList in os.walk("%s/%s" % (script_dir, GOLANG_PKG_DB)):
			for fname in fileList:
				if not fname.endswith(".xml"):
					continue
				xmldoc = minidom.parse("%s/%s" % (dirName,fname))
				prj_node = xmldoc.getElementsByTagName('project')
				if len(prj_node) < 1:
					continue

				if "nvr" not in prj_node[0].attributes.keys():
					continue

				nvr = prj_node[0].attributes["nvr"].value
				parts = nvr.split("-")
				pkg = "-".join(parts[0:-2])
				builds[pkg] = nvr	

		self.saveBuildsToCache(builds)
		return builds

	def saveBuildsToCache(self, builds):
		with open("%s/%s/nvrs.cache" % (script_dir, GOLANG_PKG_DB), "w") as file:
			sbuilds = sorted(builds.keys())
			for build in sbuilds:
				file.write("%s\n" % builds[build])

	def updateBuildsInCache(self, new_builds):
		if self.local_pkgs == []:
			self.local_pkgs = self.loadBuildsFromCache()

		for pkg in new_builds:
			self.local_pkgs[pkg] = new_builds[pkg]

		self.saveBuildsToCache(self.local_pkgs)


	def loadBuildsFromCache(self):
		builds = {}
		if not os.path.exists("%s/%s/nvrs.cache" % (script_dir, GOLANG_PKG_DB)):
			return self.loadLatestBuilds(cache=False)

		with open("%s/%s/nvrs.cache" % (script_dir, GOLANG_PKG_DB), "r") as file:
			for line in file.read().split("\n"):
				line = line.strip()
				if line == "":
					continue

				parts = line.split("-")
				pkg = "-".join(parts[0:-2])

				builds[pkg] = line

		return builds

	def fetchLatestBuilds(self, tag="rawhide"):
		pkgs = self.loadPackages()
		outdated = {}

		so, se, rc = runCommand("koji -q latest-build %s %s" % (tag, " ".join(pkgs)))
		if rc != 0:
			print se
			return {}

		for line in so.split("\n"):
			line = line.strip()

			if line == "":
				continue

			nvr = re.sub(r'[ \t]+', ' ', line).split(' ')[0]
			parts = nvr.split("-")
			pkg = "-".join(parts[0:-2])
			outdated[pkg] = nvr

		return outdated

	def getOutdatedBuilds(self, tag="rawhide"):
		self.local_pkgs = self.loadLatestBuilds()
		fetched_pkgs = self.fetchLatestBuilds(tag)

		err = []
		outdated = {}

		for pkg in fetched_pkgs:
			if pkg not in self.local_pkgs:
				err.append("%s not in localDB" % pkg)
				outdated[pkg] = fetched_pkgs[pkg]
				continue

			if compareNVRs(self.local_pkgs[pkg], fetched_pkgs[pkg]):
				outdated[pkg] = fetched_pkgs[pkg]
				#print "%s %s %s" % (self.local_pkgs[pkg], fetched_pkgs[pkg], compareNVRs(self.local_pkgs[pkg], fetched_pkgs[pkg]))

		return err, outdated

if __name__ == "__main__":
	#pkg = Package('golang-googlecode-net')
	#print pkg.getInfo()
	getPackagesFromPkgDb()
