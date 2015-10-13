from Utils import getScriptDir
from os import path, environ

class Config:

	def __init__(self):
		if environ.get("GOFED_TEST_CONFIG_FILE") == None:
			cfg_file = "/etc/gofed.conf"
		else:
			cfg_file = "config/gofed.conf"

		self.db = {}
		self.parseConfigFile(cfg_file)

	def parseConfigFile(self, cfg_file):
		lines = []
		try:
			with open(cfg_file, 'r') as file:
				lines = file.read().split('\n')
		except IOError, e:
			print "Unable to parse configuration file: %s" % e
			exit(1)

		for line in lines:
			line = line.strip()

			if line == '' or line[0] == '#':
				continue

			parts = line.split(':')
			key = parts[0]
			value = ':'.join(parts[1:])

			key = key.strip()
			value = value.strip()

			if key == '':
				continue

			self.db[key] = value

	def getValueFromDb(self, key):
		if key in self.db:
			return self.db[key]
		return ""

	def getBranches(self):
		branches = self.getValueFromDb('branches').split(" ")
		return filter(lambda b: b != "", branches)

	def getUpdates(self):
		branches = self.getValueFromDb('updates').split(" ")
		return filter(lambda b: b != "", branches)

	def getOverrides(self):
		branches = self.getValueFromDb('overrides').split(" ")
		return filter(lambda b: b != "", branches)

	def getImportPathDb(self):
		return self.getValueFromDb('import_path_db')

	def getRepoPathPrefix(self):
		return self.getValueFromDb('repo_path_prefix')

	def getFASUsername(self):
		return self.getValueFromDb('fasuser')

	def getSkippedDirectories(self):
		branches = self.getValueFromDb('skipped_directories').split(" ")
		return filter(lambda b: b != "", branches)

	def getSkippedProvidesWithPrefix(self):
		branches = self.getValueFromDb('skipped_provides_with_prefix').split(" ")
		return filter(lambda b: b != "", branches)

	def makePathAbsolute(self, cpath):
		if cpath == "":
			return ""
		# add gofed's script directory
		if cpath[0] == "@":
			# modules directory
			script_dir = path.dirname(path.realpath(__file__))
			return "%s/..%s" % (script_dir, cpath[1:])
		if cpath[0] != "/":
			return "/var/lib/gofed/%s" % cpath
		else:
			return cpath

	def getGolangMapping(self):
		path = self.getValueFromDb('golang_mapping')
		return self.makePathAbsolute(path)

	def getGolangCustomizedImportsMapping(self):
		path = self.getValueFromDb('golang_customized_imports')
		return self.makePathAbsolute(path)

	def getGolangCommonProviderPrefixes(self):
		path = self.getValueFromDb('golang_common_provider_prefixes')
		return self.makePathAbsolute(path)

	def getGolangNativeImports(self):
		path = self.getValueFromDb('golang_native_imports')
		return self.makePathAbsolute(path)

	def getGolangPkgdb(self):
		path = self.getValueFromDb('golang_pkgdb')
		return self.makePathAbsolute(path)

	def getGolangPackages(self):
		path = self.getValueFromDb('golang_packages')
		return self.makePathAbsolute(path)

	def getGolangIp2pkgMapping(self):
		path = self.getValueFromDb('golang_ip2pkg_mapping')
		return self.makePathAbsolute(path)

	def getGolangRepos(self):
		path = self.getValueFromDb('golang_repos')
		return self.makePathAbsolute(path)

	def getGolangImPrPackages(self):
		path = self.getValueFromDb('golang_im_pr_packages')
		return self.makePathAbsolute(path)

	def getGolangPlugins(self):
		path = self.getValueFromDb('golang_plugins')
		return self.makePathAbsolute(path)

	def getGofedWebUrl(self):
		url = self.getValueFromDb('golang_gofed_web_url')
		return url

	def getGofedWebDepth(self):
		depth = self.getValueFromDb('golang_gofed_web_depth')
		return int(depth)

if __name__ == "__main__":
	cfg = Config()
	print cfg.getBranches()
	print cfg.getImportPathDb()
