###############################################################################
# ========exported symbols (package units)========
# 1) list all directories containing go files
# 2) for each file in each directory list all its symbols
# 3) merge symbols belonging to the same package
# 4) for each import path make a database of all symbols
# 5) create gofed gosymbols script (--list, --importpath, --status)
#
# ========imported symbols (file units)========
# 1) for each file list all imports
# 2) for each file search for all used types, variables, constants, functions
# 3) 
#
# - if . imports are presented, it is not trivial to know from which package
# used symbols are imported. What I have to do is to:
#   a) check the package for all defined local functions, variables, constants
#      and types
#   b) from each . import, list all symbols. If symbols are not mutually
#      exclusive (this can change by any package  update), report error.
#   c) from each file list all symbols not found in a)
#   d) map symbols found in c) to symbols exported from all . imports
#
# Each day make a snapshot of all provided import paths and exported symbols.
# This will be used as a source for "used symbols" matching
#
###############################################################################
# Using GoSymbols scan will replace gofed scan-imports as it has a list of all
# packages and all imports. Exported symbols gives more informations about what
# is provided. Local database format has to be replaced with a more expressive
# one. Using xml for that as it can be read as it is.
#
# Extracted json should be transformed into a better representation (some keys
# are redundant, some types can be described in a more simple way.
###############################################################################

import os
import sys
from Utils import runCommand, getScriptDir
import json
from lxml import etree

def getGoDirs(directory, test = False):
	go_dirs = []
	for dirName, subdirList, fileList in os.walk(directory):
		# does the dirName contains *.go files
		nogo = True
		for fname in fileList:
			# find any *.go file
			if test == False and fname.endswith(".go"):
				nogo = False
				break
			elif test == True and fname.endswith("_test.go"):
				nogo = False
				break

		if nogo:
			continue

		relative_path = os.path.relpath(dirName, directory)
		go_dirs.append(relative_path)

	return go_dirs	

def getGoFiles(directory):
	go_dirs = []
	for dirName, subdirList, fileList in os.walk(directory):
		# skip all directories with no file
		if fileList == []:
			continue

		go_files = []
		for fname in fileList:
			# find any *.go file
			# but skip all test files
#			if fname.endswith("_test.go"):
#				continue

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

def getGoSymbols(path, imports_only=False):
	script_dir = getScriptDir() + "/.."
	options = ""
	if imports_only:
		options = "-imports"

	so, se, rc = runCommand("%s/parseGo %s %s" % (script_dir, options, path))
	if rc != 0:
		return (1, se)

	return (0, so)

def mergeGoSymbols(jsons = []):
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

def getSymbolsForImportPaths(go_dir, imports_only=False):
	bname = os.path.basename(go_dir)
	go_packages = {}
	ip_packages = {}
	ip_used = []
	for dir_info in getGoFiles(go_dir):
		#if sufix == ".":
		#	sufix = bname
		pkg_name = ""
		prefix = ""
		jsons = {}
		for go_file in dir_info['files']:
			go_file_json = {}
			err, output = getGoSymbols("%s/%s/%s" % 
				(go_dir, dir_info['dir'], go_file), imports_only)
			if err != 0:
				return "Error parsing %s: %s" % ("%s/%s" % (dir_info['dir'], go_file), output), {}, {}, {}
			else:
				#print go_file
				go_file_json = json.loads(output)

			for path in go_file_json["imports"]:
				if path["path"] not in ip_used:
					ip_used.append(path["path"])

			# don't check test files, read their import paths only
			if go_file.endswith("_test.go"):
				continue

			pname = go_file_json["pkgname"]
			# skip all main packages
			if pname == "main":
				continue

			if pkg_name != "" and pkg_name != pname:
				return "Error: directory %s contains defines of more packages, i.e. %s" % (dir_info['dir'], pkg_name), {}, {}, {}

			pkg_name = pname

			# build can contain two different prefixes
			# but with the same package name.
			prefix = dir_info["dir"] + ":" + pkg_name
			if prefix not in jsons:
				jsons[prefix] = [go_file_json]
			else:
				jsons[prefix].append(go_file_json)

		#print dir_info["dir"]
		#print dir_info['files']
		#print "#%s#" % pkg_name
		if prefix in jsons:
			go_packages[prefix] = mergeGoSymbols(jsons[prefix])
			ip_packages[prefix] = dir_info["dir"]

	return "", ip_packages, go_packages, ip_used

###############################################################################
# XML inner data representation
# <package path="code.google.com/p/gomock/gomock">
# 	<importList>
#		<import>fmt</import>
#		<import>reflect</import>
#		<import>strings</import>
#	</importList>
#	<typeList>
#		<type type="struct" name="Call">
#			<field name="t" type="ident" def="TestReporter" />
#			<field name="receiver" type="interface" />
#				
#			</field>
#			<field name="method" type="ident" def="string" />
#			<field name="args" type="array">
#				<type type="Matcher" />
#			</field>
#			<field name="rets" type="interface" />
#			<field name="preReqs" type="array">
#				<type type="pointer">
#					<type type="ident" def="Call" />
#				</type>
#			</field>
#			<field name="minCalls" type="ident" def="int" />
#			<field name="maxCalls" type="ident" def="int" />
#			<field name="numCalls" type="ident" def="int" />
#			<field name="doFunc" type="selector">
#				<prefix value="reflect" />
#				<type type="ident" def="Value" />
#			</field>
#			<field name="setArgs" type="map">
#				<keytype type="ident" def="int" />
#				<valuetype type="selector">
#					<prefix value="reflect" />
#					<type type="ident" def="Value" />
#				</valuetype>
#			</field>
#		</type>
#	</typeList>
# </package>

TYPE_IDENT = "ident"
TYPE_ARRAY = "array"
TYPE_SLICE = "slice"
TYPE_INTERFACE = "interface"
TYPE_POINTER = "pointer"
TYPE_SELECTOR = "selector"
TYPE_STRUCT = "struct"
TYPE_METHOD = "method"
TYPE_FUNC = "func"
TYPE_ELLIPSIS = "ellipsis"
TYPE_MAP = "map"
TYPE_CHANNEL = "channel"
TYPE_PARENTHESIS = "parenthesis"

class PackageToXml:

	def typeToXML(self, type_def, elm_name = "type"):
		self.level += 1
		#print "LEVEL: %s, %s" % (self.level, type_def["type"])
		#print type_def
		node = etree.Element(elm_name)
		if self.level == 1:
			node.set("name", type_def["name"])

		type_name = type_def["type"]
		#print type_name

		if type_name == TYPE_IDENT:
			node.set("type", "ident")
			if type(type_def["def"]) == type({}):
				err, t_def = self.typeToXML(type_def["def"])
				if err != "":
					return err, None

				node.append(t_def)
			else:
				node.set("def", type_def["def"])

		elif type_name == TYPE_INTERFACE:
			node.set("type", "interface")
			for method in type_def["def"]:
				err, method_node = self.typeToXML(method, "method")
				if err != "":
					return err, None

				method_node.set("name", method["name"])
				node.append(method_node)

		elif type_name == TYPE_POINTER:
			node.set("type", "pointer")
			err, t_def = self.typeToXML(type_def["def"])
			if err != "":
				return err, None

			node.append(t_def)

		elif type_name == TYPE_ELLIPSIS:
			node.set("type", "ellipsis")
			err, elt_node = self.typeToXML(type_def["elt"])
			if err != "":
				return err, None

			node.append(elt_node)

		elif type_name == TYPE_CHANNEL:
			node.set("type", "channel")
			if "dir" not in type_def:
				node.set("dir", type_def["def"]["dir"])
				err, val_node = self.typeToXML(type_def["def"]["value"])
			else:
				node.set("dir", type_def["dir"])
				err, val_node = self.typeToXML(type_def["value"])

			if err != "":
				return err, None

			node.append(val_node)

		# <type name="args" type="slice">
		# 	<type type="ident" def="Matcher" />                         
		# </type>
		elif type_name == TYPE_SLICE:
			node.set("type", "slice")
			err, t_def = self.typeToXML(type_def["elmtype"], "elmtype")
			if err != "":
				return err, None

			node.append(t_def)

		elif type_name == TYPE_ARRAY:
			node.set("type", "array")
			err, t_def = self.typeToXML(type_def["elmtype"], "elmtype")
			if err != "":
				return err, None

			node.append(t_def)

		elif type_name == TYPE_PARENTHESIS:
			node.set("type", "parenthesis")
			err, t_def = self.typeToXML(type_def["def"])
			if err != "":
				return err, None

			node.append(t_def)
		
		elif type_name == TYPE_MAP:
			node.set("type", "map")
			err, t_def = self.typeToXML(type_def["def"]["keytype"], "keytype")
			if err != "":
				return err, None

			node.append(t_def)

			err, t_def = self.typeToXML(type_def["def"]["valuetype"], "valtype")
			if err != "":
				return err, None

			node.append(t_def)

		# <valuetype type="selector">
		#	<prefix value="reflect" />
		#	<type type="ident" def="Value" />
		# </valuetype>
		elif type_name == TYPE_SELECTOR:
			node.set("type", "selector")
			prefix_node = etree.Element("prefix")

			prefix = ""
			item = ""
			if "prefix" not in type_def:
				prefix = type_def["def"]["prefix"]["def"]
				item   = type_def["def"]["item"]
			else:
				prefix = type_def["prefix"]["def"]
				item   = type_def["item"]

			prefix_node.set("value", prefix)
			node.append(prefix_node)
			item_node = etree.Element("item")
			item_node.set("value", item)
			node.append(item_node)
	
		elif type_name == TYPE_METHOD:
			params_node = etree.Element("paramsList")
			for item in type_def["def"]["params"]:
				err, t_def = self.typeToXML(item)
				if err != "":
					return err, None

				params_node.append(t_def)

			results_node = etree.Element("resultsList")
			for item in type_def["def"]["results"]:
				err, t_def = self.typeToXML(item)
				if err != "":
					return err, None

				results_node.append(t_def)

			node.append(params_node)
			node.append(results_node)

		elif type_name == TYPE_FUNC:
			# receiver is defined on file scope
			node.set("type", "func")
			params_node = etree.Element("paramsList")

			params = []
			results = []
			if "params" not in type_def:
				params = type_def["def"]["params"]
				results = type_def["def"]["results"]
			else:
				params = type_def["params"]
				results = type_def["results"]

			for item in params:
				err, t_def = self.typeToXML(item)
				if err != "":
					return err, None

				params_node.append(t_def)

			results_node = etree.Element("resultsList")
			for item in results:
				err, t_def = self.typeToXML(item)
				if err != "":
					return err, None

				results_node.append(t_def)

			node.append(params_node)
			node.append(results_node)

		elif type_name == TYPE_STRUCT:
			ret = self.structToXML(type_def, elm_name)
			self.level -= 1
			return ret

		else:
			return "Type %s not yet implemented" % type_name, None

		self.level -= 1
		return "", node

	def structToXML(self, str_def, elm_name = "type"):
		root = etree.Element(elm_name)
		root.set("type", "struct")
		root.set("name", str_def["name"])
		for field in str_def["def"]:
			# <field name="t" type="ident" def="TestReporter" />
			err, node = self.typeToXML(field["def"], "field")
			if err != "":
				return err, None

			node.set("name", field["name"])	
			root.append(node)

		return "", root

	def funcToXML(self, func_def):
		self.level += 1
		#print "LEVEL: %s, %s" % (self.level, "func")
		root = etree.Element("function")
		root.set("name", func_def["name"])

		list_node = etree.Element("recvList")
		for item in func_def["def"]["recv"]:
			err, type_def = self.typeToXML(item)
			if err != "":
				return err, None

			list_node.append(type_def)

		root.append(list_node)

		list_node = etree.Element("paramsList")
		for item in func_def["def"]["params"]:
			err, type_def = self.typeToXML(item)
			if err != "":
				return err, None

			list_node.append(type_def)

		root.append(list_node)

		list_node = etree.Element("resultsList")
		for item in func_def["def"]["returns"]:
			err, type_def = self.typeToXML(item)
			if err != "":
				return err, None

			list_node.append(type_def)

		root.append(list_node)

		self.level -= 1
		return "", root

	def typesToXML(self, types):
		node = etree.Element("types")
		for item in types:
			err, type_def = self.typeToXML(item)
			if err != "":
				return err, None

			node.append(type_def)
		return "", node

	def functionsToXML(self, funcs):		
		node = etree.Element("functions")
		for item in funcs:
			err, type_def = self.funcToXML(item)
			if err != "":
				return err, None

			node.append(type_def)
		return "", node

	def __init__(self, symbols, import_path, imports=True):
		self.err = ""
		self.level = 0
		self.root = etree.Element("package")
		self.root.set("importpath", import_path)
		#print "IMPORTPATH: %s" % import_path

		self.err, types_node = self.typesToXML(symbols["types"])
		if self.err != "":
			return

		self.root.append(types_node)

		self.err, functions_node = self.functionsToXML(symbols["funcs"])
		if self.err != "":
			return

		self.root.append(functions_node)

		names_node = etree.Element("names")
		for item in symbols["vars"]:
			node = etree.Element("name")
			node.set("value", item)
			names_node.append(node)

		self.root.append(names_node)

		if imports:
			imports_node = etree.Element("imports")
			for item in symbols["imports"]:
				node = etree.Element("import")
				node.set("name", item["name"])
				node.set("path", item["path"])
				imports_node.append(node)

			self.root.append(imports_node)

	def getStatus(self):
		return self.err == ""

	def getError(self):
		return self.err

	def getPackage(self):
		return self.root

	def __str__(self):
		if self.err == "":
			return etree.tostring(self.root, pretty_print=True)
		else:
			return ""

class ProjectToXml:

	def __init__(self, url, go_dir, nvr = ""):
		"""
		url	prefix used for import paths
		go_dir	root directory containing go source codes
		"""

		self.err, ip, symbols, ip_used = getSymbolsForImportPaths(go_dir)
		if self.err != "":
			return

		self.root = etree.Element("project")
		self.root.set("url", url)
		self.root.set("commit", "commit")
		self.root.set("nvr", nvr)

		packages_node = etree.Element("packages")
		for prefix in ip:
			full_import_path = "%s/%s" % (url, ip[prefix])
			if url == "":
				full_import_path = ip[prefix]

			obj = PackageToXml(symbols[prefix], full_import_path, imports=False)
			if not obj.getStatus():
				self.err = obj.getError()
				return

			packages_node.append(obj.getPackage())

		self.root.append(packages_node)

		# add imports
		imports_node = etree.Element("imports")
		for path in ip_used:
			node = etree.Element("import")
			node.set("path", path)
			imports_node.append(node)

		self.root.append(imports_node)

	def getStatus(self):
		return self.err == ""

	def __str__(self):
		if self.err == "":
			return etree.tostring(self.root, pretty_print=True, xml_declaration=True)
		else:
			return ""

	def getProject(self):
		return self.root

	def getError(self):
		return self.err


class CompareTypes:

	def __init__(self, debug=False):
		self.debug = debug
		self.position = []

	def compareIdents(self, ident1, ident2):
		"""
		Identifier is defined by type (def attribute) and name (name attribute).
		Name attribute is presented only for the top most definitions.

		Both identifiers are identical if their names (if presented) and defs are the same.

		ident1, ident2: etree.Element nodes
		"""
		#<field type="ident" def="string"[ name="Action"]/>
		err = []

		if ident1.get("def") != ident2.get("def"):
			err.append("-identifiers differ in type: %s != %s" % (ident1.get("def"), ident2.get("def")))

		if "name" in ident1.keys() and "name" in ident2.keys():
			if ident1.get("name") != ident2.get("name"):
				err.append("-identifiers differ in name: %s != %s" % (ident1.get("name"), ident2.get("name")))

			if self.debug:
				print "#NAME: " + ident1.get("name")

		return err

	def comparePointers(self, pointer1, pointer2):
		"""
		Pointer is defined by a type it points to.
		Type is a child element.

		pointer1, pointer2: etree.Element nodes
		"""
		# <field type="pointer" name="Node">
		return self.compareTypes(pointer1[0], pointer2[0])

	def compareSelectors(self, selector1, selector2):
		"""
		Selector is defined by prefix and item.

		expression.selector

		Two selectors are identical if they have the same
		expression (prefix tag) and selector (item tag).

		Expression is always identifier.
		"""
		err = []

		prefix1, prefix2 = None, None
		item1, item2 = None, None

		for node in selector1:
			if node.tag == "prefix":
				prefix1 = node
			elif node.tag == "item":
				item1 = node

		for node in selector2:
			if node.tag == "prefix":
				prefix2 = node
			elif node.tag == "item":
				item2 = node

		if prefix1.get("value") != prefix2.get("value"):
			msg = "-Selector differs in selector: %s != %s, at %s"
			pos = " -> ".join(self.position)
			err.append(msg % (prefix1.get("value"),
				prefix2.get("value"), pos))

		if item1.get("value") != item2.get("value"):
			msg = "-Selector differs in expression: %s != %s, at %s"
			pos = " -> ".join(self.position)
			err.append(msg % (item1.get("value"),
				item2.get("value"), pos))

		return err

	def compareChannels(self, chan1, chan2):
		"""
		Channel is defined by a direction (dir attribute)
		and type (type tag).

		Channels are identical if their direction and type
		are identical.

		chan1, chan2: etree.Element nodes
		"""
		#<field type="chan" dir="3" name="stop">
		#  <type type="struct" name=""/>
		#</field>
		err = []

		if chan1.get("dir") != chan2.get("dir"):
			err.append("-Channels has different direction:"
			  " %s != %s" % (chan1.get("dir"), chan2.get("dir")))

		e = self.compareTypes(chan1[0], chan2[0])
		if e != []:
			err += e

		return err	

	def compareEllipsises(self, ellipsis1, ellipsis2):

		"""
		Ellipsis is defined by a type (type tag).

		Two ellipsises are identical if their types are identical.

		ellipsis1, ellipsis2: etree.Element nodes
		"""
		#<type type="ellipsis">
		#  <type type="ident" def="string"/>
		#</type>
		return self.compareTypes(ellipsis1[0], ellipsis2[0])

	def compareSlices(self, slice1, slice2):
		"""
		Slice is defined by element type (elmtype tag).

		Slices are identical if element types are identical.
		"""
		# <elmtype type="ident" def="string"/>
		return self.compareTypes(slice1[0], slice2[0])

	def compareMaps(self, map1, map2):

		"""
		Map is defined by a keytype (keytype tag) and
		valuetype (valuetype tag).

		Two maps are identical if keytypes and valuetypes
		are identical.

		map1, map2: etree.Element nodes
		"""
		err = []

		value1, value2 = None, None
		key1, key2 = None, None

		for node in map1:
			if node.tag == "keytype":
				key1 = node
			elif node.tag == "valtype":
				value1 = node

		for node in map2:
			if node.tag == "keytype":
				key2 = node
			elif node.tag == "valtype":
				value2 = node

		e = self.compareTypes(key1, key2)
		if e != []:
			err += e

		e = self.compareTypes(value1, value2)
		if e != []:
			err += e

		return err

	def compareFunctions(self, function1, function2):

		"""
		Function is defined by signature.
		Signature consists of:
		  methods' name (name attribute)
		  list of parameters (<paramsList>)
		  list of results (<resultsList>)

		Two functions are identical if their signatures are identical.

		function1, function2: etree.Element nodes

		"""
		#<type name="InterruptHandler" type="func">
		#   <paramsList/>
		#   <resultsList/>
		#</type>
		err = []

		# check names
		if function1.get("name") != function2.get("name"):
			err.append("-function's name changed: %s -> %s" %
				(function1.get("name"), function2.get("name")))
			return err

		self.position.append("function: %s" % function1.get("name"))

		params1 = None
		params2 = None
		results1 = None
		results2 = None

		for node in function1:
			if node.tag == "paramsList":
				params1 = node
			elif node.tag == "resultsList":
				results1 = node
		for node in function2:
			if node.tag == "paramsList":
				params2 = node
			elif node.tag == "resultsList":
				results2 = node

		# check parameters
		l1 = len(params1)
		l2 = len(params2)
		if l1 != l2:
			err.append("-function %s: parameter count changed: "
				"%s -> %s" % (function1.get("name"), l1, l2))
			return err

		for i in range(0, len(params1)):
			e = self.compareTypes(params1[i], params2[i])
			if e != []:
				err += e

		# check results
		l1 = len(results1)
		l2 = len(results2)
		if l1 != l2:
			err.append("-function %s: result count changed: "
				"%s -> %s" % (function1.get("name"), l1, l2))
			return err

		for i in range(0, len(results1)):
			e = self.compareTypes(results1[i], results2[i])
			if e != []:
				err += e

		self.position.pop()

		return err

	def compareMethods(self, method1, method2):
		"""
		Method is defined by signature.
		Signature consists of:
		  methods' name (name attribute)
		  reciever
		  list of parameters (<paramsList>)
		  list of results (<resultsList>)

		Two methods are identical if their signatures are identical.

		method1, method2: etree.Element nodes
		"""

		err = []

		# check names
		if method1.get("name") != method2.get("name"):
			err.append("-method's name differs: %s != %s" %
				(method1.get("name"), method2.get("name")))
			return err

		self.position.append("method:%s" % method1.get("name"))

		params1 = None
		params2 = None
		results1 = None
		results2 = None

		for node in method1:
			if node.tag == "paramsList":
				params1 = node
			elif node.tag == "resultsList":
				results1 = node
			else:
				print "method receiver tag????"

		for node in method2:
			if node.tag == "paramsList":
				params2 = node
			elif node.tag == "resultsList":
				results2 = node
			else:
				print "method receiver tag????"

		# check parameters
		if len(params1) != len(params2):
			err.append("-methods differs in parameter count")
			return err

		for i in range(0, len(params1)):
			e = self.compareTypes(params1[i], params2[i])
			if e != []:
				err += e

		# check results
		if len(results1) != len(results2):
			err.append("-methods differs in result count")
			return err

		for i in range(0, len(results1)):
			e = self.compareTypes(results1[i], results2[i])
			if e != []:
				err += e

		# check receivers?
		self.position.pop()
		return err

	def compareInterfaces(self, interface1, interface2):
		err = []

		# check names
		if interface1.get("name") != interface2.get("name"):
			err.append("-interface name differs: %s != %s" %
			    (interface1.get("name"), interface2.get("name")))
			return err

		self.position.append("interface:%s" % interface1.get("name"))

		if self.debug:
			print "#INTERFACE: %s" % interface1.get("name")

		m1_set = set(map(lambda m: m.get("name"), interface1[:]))
		m2_set = set(map(lambda m: m.get("name"), interface2[:]))

		new_ms = list(m2_set - m1_set)
		rem_ms = list(m1_set - m2_set)
		com_ms = list(m1_set & m2_set)

		if new_ms != []:
			err.append("+new methods: " + ", ".join(new_ms))

		if rem_ms != []:
			err.append("-interface %s removed methods: %s" %
				(interface1.get("name"), ", ".join(rem_ms)))

		m1s_dir = {}
		m2s_dir = {}
		for method in interface1:
			name = method.get("name")
			if name in com_ms:
				m1s_dir[name] = method

		for method in interface2:
			name = method.get("name")
			if name in com_ms:
				m2s_dir[name] = method

		for method_name in com_ms:
			e = self.compareMethods(m1s_dir[method_name],
				m2s_dir[method_name])
			if e != []:
				err += e

			if self.debug:
				print "#METHOD: %s" % method_name

		self.position.pop()

		return err

	def skipParenthesis(self, parent1, parent2):
		"""
		Parenthesis is defined by expression it surrounds.

		Skip all parenthesis in a way. Why? What about selector?
		- all types are transparent to paranthesis (no matter if
		  the parenthesis are used, its definition is unchanged).
		- selector always consists only of two identifiers separeted
		  by dot.
		"""
		# <type type="parenthesis">
		#  <type type="ident" def="Map"/>
		# </type>
		while parent1.get("type") == TYPE_PARENTHESIS:
			parent1 = parent1[0]

		while parent2.get("type") == TYPE_PARENTHESIS:
			parent2 = parent2[0]

		return parent1, parent2

	def compareTypes(self, type1, type2):

		err = []

		type1, type2 = self.skipParenthesis(type1, type2)

		type = type1.get("type")
		if type != type2.get("type"):
			err.append("-type differs: %s != %s" % (type, type2.get("type")))
			return err

		if type == TYPE_INTERFACE:
			return self.compareInterfaces(type1, type2)
		elif type == TYPE_IDENT:
			return self.compareIdents(type1, type2)
		elif type == TYPE_POINTER:
			return self.comparePointers(type1, type2)
		elif type == TYPE_SELECTOR:
			return self.compareSelectors(type1, type2)
		elif type == TYPE_CHANNEL:
			return self.compareChannels(type1, type2)
		elif type == TYPE_ELLIPSIS:
			return self.compareEllipsises(type1, type2)
		elif type == TYPE_SLICE:
			return self.compareSlices(type1, type2)
		elif type == TYPE_MAP:
			return self.compareMaps(type1, type2)
		elif type == TYPE_STRUCT:
			return self.compareStructs(type1, type2)
		elif type == TYPE_FUNC:
			return self.compareFunctions(type1, type2)
		else:
			#TYPE_ARRAY = "array"
			print "%s type not implemented yet" % type
			exit(0)
			return []

		return []

	def constructTypeQualifiedName(self, type, full=False):
		"""
		For given type construct its full qualified name.

		AnonymousField = [ "*" ] TypeName .
		TypeName  = identifier | QualifiedIdent .
		QualifiedIdent = PackageName "." identifier .
		"""
		t = type.get("type")
		if t == "ident":
			if self.debug:
				print "#FQN: %s" % type.get("def")
			return type.get("def")
		elif t == "pointer":
			return self.constructTypeQualifiedName(type[0])
		elif t == "selector":
			expr, sel = None, None
			for node in type:
				if node.tag == "prefix":
					expr = node.get("value")
				elif node.tag == "item":
					sel = node.get("value")
			if full:
				return "%s.%s" % (expr, sel)
			else:
				return sel
		else:
			print "Type %s can not be used for FQN" % t
			return ""

	def compareStructs(self, struct1, struct2):
		"""
		Struct is defined by its fields.
		Field consists of a name (name attribute) and type definition.

		Order of fields is important but can be different.

		For anonymous field an unqualified type name is taken.

		Structs are identical if they have the same number of fields
		and list of fiels are identical.

		struct1, struct2: etree.Element nodes
		"""
		err = []

		if self.debug:
			print "#STRUCT: %s" % struct1.get("name")

		self.position.append("struct")

		# get a list of field names (with anynomous as well)
		fs1 = map(lambda f: f.get("name") if f.get("name") != ""
			else self.constructTypeQualifiedName(f), struct1)
		fs2 = map(lambda f: f.get("name") if f.get("name") != ""
			else self.constructTypeQualifiedName(f), struct2)

		index1, index2 = 0, 0
		l1, l2 = len(struct1), len(struct2)

		if l1 != l2:
			err.append("struct %s has different number of"
				" fields" % struct1.get("name"))

		while index1 < l1 and index2 < l2:

			name1 = fs1[index1]
			name2 = fs2[index2]

			if name1 != name2:
				err.append("struct %s: fields are reordered" %
					struct1.get("name"))
				break

			index1 += 1
			index2 += 1

		s1_dict, s2_dict = {}, {}
		for node in struct1:
			name = node.get("name")
			if name == "":
				name = self.constructTypeQualifiedName(node)

			s1_dict[name] = node

		for node in struct2:
			name = node.get("name")
			if name == "":
				name = self.constructTypeQualifiedName(node)

			s2_dict[name] = node

		# check individual fields
		fs1 = sorted(fs1)
		fs2 = sorted(fs2)
		while index1 < l1 and index2 < l2:
			# check types
			name1 = fs1[index1]
			name2 = fs2[index2]
			if name1 == name2:
				index1 += 1
				index2 += 1
				e = self.compareTypes(s1_dict[name1],
					s2_dict[name2])
				if e != []:
					err += e
			elif name1 < name2:
				index1 += 1
				err.append("-struct %s: %s field removed" %
					(struct1.get("name"), name1))
			else:
				index2 += 1
				err.append("+struct %s: new field '%s'" %
					(struct1.get("name"), name2))

		# some fields not checked?
		while index1 < l1:
			err.append("-struct %s: field '%s' removed" %
				(struct1.get("name"), fs1[index1]))
			index1 += 1

		while index2 < l2:
			err.append("+struct %s: new field '%s'" %
				(struct1.get("name"), fs2[index2]))
			index2 += 1

		self.position.pop()

		return err

class ComparePackages:

	def __init__(self, pkg_name, debug=False):
		self.pkg_name = pkg_name
		self.debug = debug
		self.msg = []

	def getStatus(self):

		return {
			"name": self.pkg_name,
			"status": self.msg
		}

	def compareNames(self, names1, names2):
		msg = []

		names1_set = set(map(lambda i: i.get('value'), names1))
		names2_set = set(map(lambda i: i.get('value'), names2))

		new_names = list(names2_set - names1_set)
		rem_names = list(names1_set - names2_set)

		for item in new_names:
			msg.append("+%s variable/constant added" % item)

		for item in rem_names:
			msg.append("-%s variable/constant removed" % item)

		return msg

	def compareFunctions(self, funcs1, funcs2):
		msg = []

		# get types names
		funcs1_set = set(map(lambda x: x.get("name"), funcs1[:]))
		funcs2_set = set(map(lambda x: x.get("name"), funcs2[:]))

		new_funcs = list(funcs2_set - funcs1_set)
		rem_funcs = list(funcs1_set - funcs2_set)
		com_funcs = list(funcs1_set & funcs2_set)

		for item in new_funcs:
			msg.append("+%s func added" % item)

		for item in rem_funcs:
			msg.append("-%s func removed" % item)

		fs1_dict, fs2_dict = {}, {}
		for node in funcs1:
			node.set("type", "func")
			fs1_dict[node.get("name")] = node

		for node in funcs2:
			node.set("type", "func")
			fs2_dict[node.get("name")] = node

		for name in com_funcs:
			e = CompareTypes().compareTypes(fs1_dict[name], fs2_dict[name])
			if e != []:
				msg += e

		return msg

	def compareTypes(self, type1, type2):
		msg = []

		# get types names
		type1_set = set(map(lambda x: x.get("name"), type1[:]))
		type2_set = set(map(lambda x: x.get("name"), type2[:]))

		new_types = list(type2_set - type1_set)
		rem_types = list(type1_set - type2_set)
		com_types = list(type1_set & type2_set)

	
		for item in new_types:
			msg.append("+%s type added" % item)

		for item in rem_types:
			msg.append("-%s type removed" % item)

		types1_dir = {}
		types2_dir = {}
		for type in type1:
			if type.get("name") in com_types:
				types1_dir[type.get("name")] = type

		for type in type2:
			if type.get("name") in com_types:
				types2_dir[type.get("name")] = type

		for type in com_types:
			err = CompareTypes().compareTypes(types1_dir[type], types2_dir[type])
			if err != []:
				msg += err

		return msg

	def comparePackages(self, pkg1, pkg2):

		"""
		Top most definitions can contain method definition.
		However as the method is field of a struct, it is already
		checked during checking of all types.
		"""
		types1 = None
		funcs1 = None
		names1 = None

		types2 = None
		funcs2 = None
		names2 = None

		for elm in pkg1:
			if elm.tag == "types":
				types1 = elm
			elif elm.tag == "functions":
				funcs1 = elm
			elif elm.tag == "names":
				names1 = elm

		for elm in pkg2:
			if elm.tag == "types":
				types2 = elm
			elif elm.tag == "functions":
				funcs2 = elm
			elif elm.tag == "names":
				names2 = elm

		# check names
		self.msg += self.compareNames(names1, names2)
		# check types
		self.msg += self.compareTypes(types1, types2)
		# check funcs
		self.msg += self.compareFunctions(funcs1, funcs2)

		if self.debug and self.msg != []:
			print "Package: %s" % self.pkg_name
			print "\n".join(map(lambda m: "\t" + m, self.msg))

class CompareSourceCodes:

	def __init__(self, directory_old, directory_new):
		self.err = []
		self.status = {}
		self.compare(directory_old, directory_new)

	def compare(self, directory_old, directory_new):
		msg = []

		e, ip1, symbols1, ip_used2 = getSymbolsForImportPaths(directory_old)
		if e != "":
			self.err.append("Error at %s: %s" % (directory_old, e))
			return

		e, ip2, symbols2, ip_used2 = getSymbolsForImportPaths(directory_new)
		if e != "":
			self.err.append("Error at %s: %s" % (directory_new, e))
			return

		ip1_set = set(ip1.keys())
		ip2_set = set(ip2.keys())

		new_ips = list( ip2_set - ip1_set )
		rem_ips = list( ip1_set - ip2_set )
		com_ips = sorted(list( ip1_set & ip2_set ))

		# list new packages
		if new_ips != []:
			msg.append("+new packages: " + ", ".join(map(lambda i: i.split(":")[0], new_ips)))

		# list removed packages
		if rem_ips != []:
			msg.append("-removed packages: " + ", ".join(map(lambda i: i.split(":")[0], rem_ips)))

		# compare common packages
		for pkg in com_ips:
			pkg_name = pkg.split(":")[0]
			obj1 = PackageToXml(symbols1[pkg], "%s" % (ip1[pkg]), imports=False)
			if not obj1.getStatus():
				self.err.append("Error at %s due to json2xml parsing: " % (pkg_name, obj1.getError()))
				continue

			obj2 = PackageToXml(symbols2[pkg], "%s" % (ip2[pkg]), imports=False)
			if not obj2.getStatus():
				self.err.append("Error at %s due to json2xml parsing: " % (pkg_name, obj2.getError()))
				continue

			comp_pkgs = ComparePackages(pkg.split(":")[0])
			comp_pkgs.comparePackages(obj1.getPackage(), obj2.getPackage())
			status = comp_pkgs.getStatus()
			if status["status"] != []:
				self.status[pkg_name] = status["status"]

	def getStatus(self):
		return self.status

	def getError(self):
		return self.err

