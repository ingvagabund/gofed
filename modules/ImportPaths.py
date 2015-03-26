import os
import re
from Utils import getScriptDir
from modules.Repos import detectGithub, detectGooglecode, detectGolangorg, detectGoogleGolangorg, detectGopkg
from modules.Repos import github2pkgdb, googlecode2pkgdb, googlegolangorg2pkgdb, golangorg2pkgdb 
from Config import Config
from xml.dom import minidom
from xml.dom.minidom import Node

GOLANG_IMPORTS = "data/golang.imports"
GOLANG_PKG_DB = "data/pkgdb"
script_dir = getScriptDir() + "/.."

# get imports from a file
def getFileImports(gofile):

	with open(gofile, 'r') as file:
		content = file.read()

		# delete one line comments
		content = re.sub(r'//[^\n]*\n', '\n', content)
		# delete multi-line comments
		p = re.compile(r'/\*.+?\*/', re.DOTALL)
		content = p.sub('\n', content)
		# delete all "import" strings
		content = re.sub(r'"import"', '', content)
		# import must be followed by white space
		content = re.sub(r'import[^\s]', '######', content)

		start = content.find('import')
		if start == -1:
			return []

		# import grammar: http://golang.org/ref/spec#Import_declarations
		#
		# ImportDecl       = "import" ( ImportSpec | "(" { ImportSpec ";" } ")" ) .
		# ImportSpec       = [ "." | PackageName ] ImportPath .
		# ImportPath       = string_lit .

		# make sure import is always followed only by one space
		content = re.sub(r'import[^("]+', 'import ', content)
		# replace ; with newline
		content = re.sub(';', '\n', content)
		# deal with one liners
		p = re.compile(r'import\s+"([^"]+)"')
		content = p.sub(r'import ("\1")', content)
		# get string in a form: import ([^)]*)
		end = content.find(')', start)
		imports = content[start+6:end]
		start = imports.find('(')
		imports = imports[start+1:].strip()

		imps = []
		for pot_imp in imports.split('\n'):
			if pot_imp == "":
				continue

			pot_imp = pot_imp.strip()
			pot_imp = re.sub(r'\s+', ' ', pot_imp)

			# get rid of PackageName and "."
			parts = pot_imp.split(' ')
			if len(parts) == 2:
				pot_imp = parts[1]

			if '"' in pot_imp:
				pot_imp = re.sub('"', '', pot_imp)

			# If the import path starts with . or /,
			# it is relative or absolute path.
			# Filter it out.
			if pot_imp == "" or pot_imp[0] == "." or pot_imp[0] == "/":
				continue

			imps.append(pot_imp)

		return imps

# get imports from all files in the directory (or actual directory), sort -u them
def getFileTreeImports(directory):
	imports = []
	for dirName, subdirList, fileList in os.walk(directory):
		for fname in fileList:
			# filter all non *.go files
			if fname.endswith(".go"):
				imports = imports + getFileImports(dirName + "/" + fname)

	return sorted(list(set(imports)))
	# Only for test purposes
	for item in sorted(list(set(imports))):
		print item

def getNativeImports():
	script_dir = getScriptDir() + "/.."
	with open('%s/%s' % (script_dir, GOLANG_IMPORTS), 'r') as file:
                content = file.read()
		return content.split('\n')

def decomposeImports(imports):
	classes = {}
	native = getNativeImports()
	for gimport in imports:
		prefix = gimport.split('/')[0]
		if prefix in native:
			key = "Native"
		elif gimport.startswith('github.com'):
			key = detectGithub(gimport)
		elif gimport.startswith('code.google.com'):
			key = detectGooglecode(gimport)
		elif gimport.startswith('golang.org'):
			key = detectGolangorg(gimport)
		elif gimport.startswith('google.golang.org'):
			key = detectGoogleGolangorg(gimport)
		elif gimport.startswith('gopkg.in'):
			key = detectGopkg(gimport)
		else:
			key = "Unknown"

		if key not in classes:
			classes[key] = [gimport]
		else:
			classes[key].append(gimport)

	return classes

def loadImportPathDb():
	"""
	For each subpackage return all imported and provided import paths
	"""
	# one package can have more *.xml files
	ip_provides = {}
	ip_imports = {}
	pkg_devel_main_pkg = {}

	native_imports = getNativeImports()

	for dirName, subdirList, fileList in os.walk("%s/%s" % (script_dir, GOLANG_PKG_DB)):
		for fname in fileList:
			if not fname.endswith(".xml"):
				continue

			xmldoc = minidom.parse("%s/%s" % (dirName,fname))
			prj_node = xmldoc.getElementsByTagName('project')
			if len(prj_node) != 1:
				continue

			pkg_nodes = prj_node[0].getElementsByTagName("packages")
			if len(pkg_nodes) != 1:
				continue

			pkg_nodes = pkg_nodes[0].getElementsByTagName("package")

			devel_name = fname.split(".")[0]

			ip_provides[devel_name] = []
			ip_imports[devel_name] = []
			for pkg_node in pkg_nodes:
				if "importpath" not in pkg_node.attributes.keys():
					continue

				ip_provides[devel_name].append(str(pkg_node.attributes["importpath"].value))

			imports_nodes = prj_node[0].getElementsByTagName("imports")
			if len(imports_nodes) != 1:
				continue

			import_nodes = imports_nodes[0].getElementsByTagName("import")
			for import_node in import_nodes:
				if "path" not in import_node.attributes.keys():
					continue

				ip = import_node.attributes["path"].value
				prefix = ip.split('/')[0]
				if prefix in native_imports:
					continue

				# does package imports itself?
				if ip in ip_provides[devel_name]:
					continue

				ip_imports[devel_name].append(str(ip))

			# get NVR
			if "nvr" not in prj_node[0].attributes.keys():
				continue

			pkg = "-".join(prj_node[0].attributes["nvr"].value.split("-")[:-2])
			pkg_devel_main_pkg[devel_name] = str(pkg)

		return ip_provides, ip_imports, pkg_devel_main_pkg

def getDevelImportedPaths():
	_, ip_i, _ = loadImportPathDb()
	return ip_i

def getDevelProvidedPaths():
	ip_p, _, _ = loadImportPathDb()
	return ip_p

