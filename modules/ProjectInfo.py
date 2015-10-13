from modules.GoSymbolsExtractor import GoSymbolsExtractor
from modules.ImportPathsDecomposer import ImportPathsDecomposer
from glob import glob
from os import path
import sys

class ProjectInfo:

	def __init__(self, noGodeps = []):
		self.err = ""
		self.warn = ""
		self.imported_packages = []
		self.package_imports_occurence = {}
		self.provided_packages = []
		self.docs = []
		self.noGodeps = noGodeps
		self.godeps_on = False

	def getError(self):
		return self.err

	def getWarning(self):
		return self.warn

	def getImportedPackages(self):
		return self.imported_packages

	def getPackageImportsOccurences(self):
		return self.package_imports_occurence

	def getProvidedPackages(self):
		return self.provided_packages

	def getTestDirectories(self):
		return self.test_directories

	def getDocs(self):
		return self.docs

	def _getDocFiles(self, archive_directory):
		docs = []

		for doc in glob( path.join(archive_directory, '*.md') ):
			docs.append(path.basename(doc))

		for doc in ['Readme', 'README', 'LICENSE', 'License', 'AUTHORS', 'COPYING', 'LICENSE.txt', 'README.txt', 'CONTRIBUTORS', 'HACKING', 'COPYRIGHT', 'PATENTS']:
			if path.exists("%s/%s" % (archive_directory, doc)):
				docs.append(doc)

		return docs

	def godepsDirectoryExists(self):
		return self.godeps_on

	def retrieve(self, directory, skip_errors = False):
		"""
		Retrieve information about project from directory
		"""
		# directory exists?
		if not path.exists(directory):
			self.err = "Directory %s does not exist" % directory
			return False

		gse_obj = GoSymbolsExtractor(directory, skip_errors=skip_errors, noGodeps=self.noGodeps)
		if not gse_obj.extract():
			self.err = gse_obj.getError()
			return False

		self.godeps_on = gse_obj.godepsDirectoryExists()
		ip_used = gse_obj.getImportedPackages()
		self.package_imports_occurence = gse_obj.getPackageImportsOccurences()
		packages = gse_obj.getSymbolsPosition()
		tests = gse_obj.getTestDirectories()

                ips_imported = []
		ips_provided = []

		# imported paths
		ipd = ImportPathsDecomposer(ip_used)
		if not ipd.decompose():
			self.err = ipd.getError()
			return False

		self.warn = ipd.getWarning()

		classes = ipd.getClasses()
	        sorted_classes = sorted(classes.keys())

		for ip_class in sorted_classes:
			if ip_class == "Native":
				continue

			for ip in classes[ip_class]:
				self.imported_packages.append(ip)

		# provided paths
		for pkg in packages:
			self.provided_packages.append(packages[pkg])

		# project documentation
		self.docs = self._getDocFiles(directory)

		self.imported_packages = sorted(self.imported_packages)
		self.provided_packages = sorted(self.provided_packages)
		self.test_directories = sorted(tests)

		return True

