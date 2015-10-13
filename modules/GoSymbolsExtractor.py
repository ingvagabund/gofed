import os
import json
import sys
from Utils import getScriptDir, runCommand
from Base import Base

class GoSymbolsExtractor(Base):

	def __init__(self, directory, imports_only=False, noGodeps=[], skip_errors=False):
		self.directory = directory
		self.imports_only = imports_only
		self.noGodeps = noGodeps
		self.skip_errors = skip_errors

		self.symbols = []
		self.symbols_position = {}
		# list of packages imported for each project's package
		self.package_imports = {}
		# list of packages imported in entire project
		self.imported_packages = []
		# occurences of imported paths in packages
		self.package_imports_occurence = {}
		self.test_directories = []
		# main packages
		self.main_packages = []
		# Godeps directory is present
		self.godeps_on = False

	def godepsDirectoryExists(self):
		return self.godeps_on

	def getSymbols(self):
		return self.symbols

	def getSymbolsPosition(self):
		return self.symbols_position

	def getPackageImports(self):
		return self.package_imports

	def getImportedPackages(self):
		return self.imported_packages

	def getPackageImportsOccurences(self):
		return self.package_imports_occurence

	def getMainPackages(self):
		return self.main_packages

	def getTestDirectories(self):
		return self.test_directories

	def getGoFiles(self, directory):
		go_dirs = []
		for dirName, subdirList, fileList in os.walk(directory):
			# skip all directories with no file
			if fileList == []:
				continue

			go_files = []
			for fname in fileList:
				# find any *.go file
				if fname.endswith(".go"):
					go_files.append(fname)

			# skipp all directories with no *.go file
			if go_files == []:
				continue

			relative_path = os.path.relpath(dirName, directory)
			go_dirs.append({
				'dir': relative_path,
				'files': go_files,
			})

		return go_dirs

	def getGoSymbols(self, path, imports_only=False):
		script_dir = getScriptDir() + "/.."
		options = ""
		if imports_only:
			options = "-imports"

		so, se, rc = runCommand("%s/parseGo %s %s" % (script_dir, options, path))
		if rc != 0:
			return (1, se)

		return (0, so)

	def mergeGoSymbols(self, jsons = []):
		"""
		Exported symbols for a given package does not have any prefix.
		So I can drop all import paths that are file specific and merge
		all symbols.
		Assuming all files in the given package has mutual exclusive symbols.
		"""
		# <siXy> imports are per file, exports are per package
		# on the highest level we have: pkgname, types, funcs, vars, imports.

		symbols = {}
		symbols["types"] = []
		symbols["funcs"] = []
		symbols["vars"]  = []
		for file_json in jsons:
			symbols["types"] += file_json["types"]
			symbols["funcs"] += file_json["funcs"]
			symbols["vars"]  += file_json["vars"]

		return symbols

	def extract(self):
		"""

		"""
		bname = os.path.basename(self.directory)
		go_packages = {}
		ip_packages = {}
		test_directories = []
		ip_used = []
		package_imports = {}
		main_packages = []

		for dir_info in self.getGoFiles(self.directory):
			if dir_info["dir"].startswith("Godeps"):
				self.godeps_on = True

			#if sufix == ".":
			#	sufix = bname
			pkg_name = ""
			prefix = ""
			jsons = {}
			if self.noGodeps != []:
				skip = False
				path_components = dir_info['dir'].split("/")
				for nodir in self.noGodeps:
					parts = nodir.split(":")
					name = parts[0]
					# empty means all elements
					max_depth = len(path_components)
					if len(parts) == 2 and parts[1].isdigit():
						max_depth = int(parts[1])

					if name in path_components[0:max_depth]:
						skip = True
						break
				if skip:
					continue

			for go_file in dir_info['files']:
				go_file_json = {}
				err, output = self.getGoSymbols("%s/%s/%s" % 
					(self.directory, dir_info['dir'], go_file), self.imports_only)
				if err != 0:
					if self.skip_errors:
						continue
					else:
						self.err = "Error parsing %s: %s" % ("%s/%s" % (dir_info['dir'], go_file), output)
						return False
				else:
					#print go_file
					go_file_json = json.loads(output)

				pname = go_file_json["pkgname"]

				for path in go_file_json["imports"]:
					# filter out all import paths starting with ./
					if path["path"].startswith("./"):
						continue

					# filter out all .. import paths
					if path["path"] == "..":
						continue

					if dir_info['dir'] == ".":
						file_pkg_pair = "%s:%s" % (go_file, pname)
					else:
						file_pkg_pair = "%s/%s:%s" % (dir_info['dir'], go_file, pname)

					if path["path"] not in self.package_imports_occurence:
						self.package_imports_occurence[str(path["path"])] = [str(file_pkg_pair)]
					else:
						self.package_imports_occurence[str(path["path"])].append(str(file_pkg_pair))

					if path["path"] in ip_used:
						continue

					ip_used.append(path["path"])

				# don't check test files, read their import paths only
				if go_file.endswith("_test.go"):
					test_directories.append(dir_info['dir'])
					continue

				# skip all main packages
				if pname == "main":
					if dir_info['dir'] == ".":
						main_packages.append(go_file,)
					else:
						main_packages.append("%s/%s" % (dir_info['dir'], go_file))
					continue

				# all files in a directory must define the same package
				if (pkg_name != "" and pkg_name != pname):
					err_msg = "Error: directory %s contains definition of more packages, i.e. %s" % (dir_info['dir'], pname)
					if self.skip_errors:
						sys.stderr.write("%s\n" % err_msg)
						continue
					self.err = err_msg
					return False

				# convention is to have dirname = packagename, but not necesary
				if pname != os.path.basename(dir_info['dir']):
					self.warn = "Error: directory %s != package name %s" % (dir_info['dir'], pname)

				pkg_name = pname

				# build can contain two different prefixes
				# but with the same package name.
				prefix = dir_info["dir"] + ":" + pkg_name
				i_paths = map(lambda i: i["path"], go_file_json["imports"])
				if prefix not in jsons:
					jsons[prefix] = [go_file_json]
					package_imports[prefix] = i_paths
				else:
					jsons[prefix].append(go_file_json)
					package_imports[prefix] = package_imports[prefix] + i_paths

			#print dir_info["dir"]
			#print dir_info['files']
			#print "#%s#" % pkg_name
			if prefix in jsons:
				go_packages[prefix] = self.mergeGoSymbols(jsons[prefix])
				ip_packages[prefix] = dir_info["dir"]
				package_imports[prefix] = list(set(package_imports[prefix]))

		self.symbols = go_packages
		self.symbols_position = ip_packages
		self.package_imports = package_imports
		self.imported_packages = ip_used
		self.test_directories = list(set(test_directories))
		self.main_packages = main_packages

		return True

