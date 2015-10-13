from ImportPathDB import ImportPathDB
from Base import Base

class DependencyGraphBuilder(Base):

	def __init__(self, verbose=False, cache=False, loops=False):
		Base.__init__(self)
		self.warn = []
		self.verbose = verbose
		self.cache = cache
		self.loops = loops
		# list of package names
		self.nodes = []
		# adjacency list
		self.edges = {}
		# {..., 'subpackage': 'package', ...}
		# subpackage \in package relationship
		self.pkg_devel_main_pkg = {}

	def getNodes(self):
		return self.nodes

	def getEdges(self):
		return self.edges

	def getGraph(self):
		return (self.nodes, self.edges)

	def getSubpackageMembership(self):
		return self.pkg_devel_main_pkg

	def build(self):
		# load imported and provided paths
		ipdb_obj = ImportPathDB(cache=self.cache)
		if not ipdb_obj.load():
			self.err = "Error: %s" % ipdb_obj.getError()
			return False

		ip_provides = ipdb_obj.getProvidedPaths()
		ip_imports = ipdb_obj.getImportedPaths()
		pkg_devel_main_pkg = ipdb_obj.getDevelMainPkg()

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

				provides_mapping[ip.split(":")[0]] = pkg_devel

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
					self.warn.append("%s path of %s subpackage is not provided by any package" % (ip, pkg_devel))
					continue

				if not self.loops:
					# skip all loops
					if pkg_devel == provides_mapping[ip]:
						continue

				if pkg_devel not in edges:
					edges[pkg_devel] = [provides_mapping[ip]]
				else:
					if provides_mapping[ip] not in edges[pkg_devel]:
						edges[pkg_devel].append(provides_mapping[ip])

		self.nodes = pkgs
		self.edges = edges
		self.pkg_devel_main_pkg = pkg_devel_main_pkg
		return True

