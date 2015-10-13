from Base import Base
from Utils import runCommand
import re

RPM_SCRIPTLETS = ('pre', 'post', 'preun', 'postun', 'pretrans', 'posttrans',
                  'trigger', 'triggerin', 'triggerprein', 'triggerun',
                  'triggerun', 'triggerpostun', 'verifyscript')

SECTIONS = ('build', 'changelog', 'check', 'clean', 'description', 'files',
               'install', 'package', 'prep') + RPM_SCRIPTLETS

# import_paths macros: evaluate all macros with import and path infix in
#                      the macro's name and try to detect to which subpackage
#                      it belongs
# 
# steps: 1) parse spec file header (macros)
#        2) parse package header (Name, Version, ...)
#        3) parse subpackages ([B]R, Provides)
# 
# create 

class PackageSection(Base):

	def __init__(self, name):
		self.name = name
		self.br = []
		self.r = []
		self.p = []

	def setBuildRequires(self, br):
		self.br = br

	def setRequires(self, r):
		self.r = r

	def setProvides(self, p):
		self.p = p

	def getBuildRequires(self):
		return self.br

	def getRequires(self):
		return self.r

	def getProvides(self):
		return self.p

class Sources(Base):

	def __init__(self, sources):
		Base.__init__(self)
		self.sources = sources
		self.files = {}

	def getFiles(self):
		return self.files

	def parse(self):
		lines = []
		try:
			with open(self.sources, 'r') as file:
				lines = file.read().split("\n")
		except IOError, e:
			self.err = e
			return False

		for line in lines:
			line = line.strip()
			if line == "":
				continue

			# checksum    FILE
			line = re.sub(r'[ \t]+', ' ', line)
			parts = line.split(' ')
			if len(parts) != 2:
				self.err = "%s, '%s' is not in 'checksum  FILE' form" % (self.sources, line)
				return False

			self.files[ parts[1] ] = parts[0]

		return True

class Changelog(Base):

	def __init__(self):
		self._header = ""
		self._comment = ""

	@property
	def header(self):
		return self._header

	@header.setter
	def header(self, value):
		self._header = value

	@property
	def comment(self):
		return self._comment

	@comment.setter
	def comment(self, value):
		self._comment = value

class SpecParser(Base):

	def __init__(self, spec):
		Base.__init__(self)
		self.spec = spec
		self.tags = {}
		self.macros = {}
		self.subpackages = {}
		self.changelogs = []

	def getDevelSubpackage(self):
		# If there is only one devel subpackage, take it
		# If there are more devel subpackages, take pkg_name-devel
		# Otherwise return None
		devel = ""
		devel_counter = 0
		subpkg_keys = self.subpackages.keys()
		for key in subpkg_keys:
			if key.endswith('devel'):
				devel = key
				devel_counter += 1

		if devel == "":
			self.err = "No devel subpackage found"
			return None

		if devel_counter == 1:
			return self.subpackages[devel]

		# devel_main macro?
		devel_main = self.getMacro('devel_main')
		if devel_main != "":
			if devel_main not in subpkg_keys:
				self.err = "Devel package speficied by %{devel_main} macro not found"
				return None
			return self.subpackages[devel_main]

		if devel_counter == 2:
			if ("%s-devel" % self.pkg_name) not in subpkg_keys:
				self.err = "No %s-devel found" % self.pkg_name
				return None
			return self.subpackages["%s-devel" % self.pkg_name]

		return None

	def getBugIdFromLastChangelog(self):
		log = self.getLastChangelog()
		if log == None:
			return -1

		# resolves: #1209666
		# related: #1209666
		# resolves: bz1209666
		# related: rhbz1209666
		# colon or sharp does not have to presented
		# the same for bz and rhbz prefix
		# search for the first number and return it
		for line in log.comment:
			pos = line.find('resolves')
			if pos == -1:
				pos = line.find('related')
			if pos != -1:
				regex = re.compile(r'([0-9]+)')	
				res = regex.search(line[pos:]).groups()
				if len(res) == 0:
					continue
				return int(res[0])
		return -1

	def getLastChangelog(self):
		if self.changelogs == []:
			return None

		return self.changelogs[0]

	def getSubpackages(self):
		return self.subpackages.keys()

	def getProvides(self):
		if self.subpackages == {}:
			return {}

		provides = {}
		for item in self.subpackages:
			ps = self.subpackages[item].getProvides()
			if ps != []:
				provides[item] = ps

		return provides

	def parse(self):
		lines = self.getRawSpecLines(self.spec)
		if lines == []:
			return False

		plines = self.getSpecLines(self.spec)
		if plines == []:
			return False

		# read macros
		self.macros = self.readMacros(lines)
		# get package name
		self.pkg_name = self.parsePkgName(plines)
		# decompose sections
		sections = self.decomposeIntoSections(self.pkg_name, plines)

		# parse main section
		if 'main' not in sections:
			self.err = "spec file has no main section"
			return False

		self.parseMainSection(sections['main'])

		# parse package sections
		if 'package' not in sections:
			self.err = "spec file does not define any package section"
			return False

		self.subpackages = self.parsePackageSections(sections['package'])
		if self.subpackages == {}:
			self.err = "no package section found"
			return False

		# parse changelog
		if 'changelog' not in sections:
			self.err = "spec file does not define changelog section"
			return False

		self.changelogs = self.parseChangelog(sections['changelog'])
		if self.changelogs == []:
			self.err = "no changelog available"
			return False

		return True
		
	def getMacro(self, name):
		if name not in self.macros:
			return ""
		else:
			value, ok = self.evalMacro(name, self.macros)
			if ok:
				return value
			else:
				return ""

	def getTag(self, name):
		if name not in self.tags:
			return ""
		else:
			return self.tags[name]

	def readMacros(self, spec_lines = []):
		macros = {}
		for line in spec_lines:
			line = line.strip()
			if line == '' or  line.startswith((' ', '\t', '#', '\n')):
				continue

			if line.startswith('%global'):
				line = re.sub(r'[ \t]+', ' ', line, count=2)
				# %global <name> <body>
				parts = line.split(' ')
				macros[parts[1]] = ' '.join(parts[2:])
				continue
		return macros

	def reevalMacro(self, old_value, macros):
		value = ''
		# what macros are inside? %{macro_name} or %macro_name          
                # %(...) is a script invocation and is not interpreted
		# no macro in macro use
		key = ''
		mfound = False
		mbracket = False
		for c in old_value:
			if c == '%':
				key = ''
				mfound = True
				continue
			if mfound:
				if c == '{':
					if not mbracket:
						mbracket = True
						continue
					else:
						return '', False
				elif c == '(':
					mfound = False
					value += "%("
					continue
				if re.match('[a-zA-Z0-9_]', c):
					key += c
				else:
					if key not in macros:
						return '', False
					value += macros[key]
					if not mbracket:
						mfound = False
						value += c
						continue
					if c != '}':
						return '', False
					mbracket = False
					mfound = False
			else:
				value += c
		return value, True

	def evalMacro(self, name, macros):

		if name not in macros:
			return "", False	
		value = ""

		evalue, rc = self.reevalMacro(macros[name], macros)
		if rc == False:
			return '', False

		while evalue != value:
			value = evalue
			evalue, rc = self.reevalMacro(value, macros)
			if rc == False:
				return '', False

		return value, True

	def parsePkgName(self, spec_lines = []):
		for line in spec_lines:
			line = line.strip()
			if line.upper().startswith('NAME'):
				_, value = self.parseTag(line)
				return value

		print ""

	def getRawSpecLines(self, spec):
		"""
		Get uninterpreted content of spec file
		"""
		try:
			with open(spec, 'r') as file:
				return file.read().split('\n')
		except IOError, e:
			self.err = e
			return []

	def getSpecLines(self, spec):
		"""
		Get interpreted content of spec file
		"""
		stdout, stderr, rt = runCommand('rpmspec -P %s' % spec)
		if rt != 0:
			self.err = stderr
			return []
		return stdout.split('\n')

	def getPackageName(self, pkg_name, line):
		"""
		Get a name for package, description or files section
		"""
		line = line.strip()
		line = re.sub(r'[ \t]+', ' ', line)
		items = line.split(' ')
		items_len = len(items)

		if items_len == 1:
			return pkg_name

		i = 1
		while i < items_len:
			item = items[i]
			i += 1
			if item.startswith('-n'):
				return items[i]
			if item[0] == '-':
				continue
			return '%s-%s' % (pkg_name, item)
		return ""

	def decomposeIntoSections(self, pkg_name, plines):
		sections = {}
		last_section = ""
		last_name = ""
		last_list = []

		for line in plines:
			#print line

			skip = False
			for sec in SECTIONS:
				if line.lower().startswith("%%%s" % sec):
					if last_section != "":
						if last_section in ["files", "package", "description"]:
							sections[last_section]['value'][last_name] = last_list
						else:
							sections[last_section] = last_list
					# end of package header (Name, Version , ...)
					else:
						sections['main'] = last_list

					# clean saved lines
					last_list = []

					if sec not in sections:
						sections[sec] = {'name': [], 'value': {}}

					if sec in ["files", "package", "description"]:
						name = self.getPackageName(pkg_name, line)
						sections[sec]['name'].append(name)
						# main subpackage has empty name
					else:
						name = line

					last_section = sec
					last_name = name
					#sections[sec]['value'][name] = []
					skip = True
					break

			if skip:
				continue

			last_list.append(line)

		if last_section != "":
			if last_section in ["files", "package", "description"]:
				sections[last_section]['value'][last_name] = last_list
			else:
				sections[last_section] = last_list

		return sections

	def parseTag(self, line):
		if line == "":
			return ()

		parts = line.split(':')
		if len(parts) < 2:
			return ()

		key = parts[0].strip()
		value = ":".join(parts[1:]).strip()

		return (key, value)

	def parseMainSection(self, section):
		for line in section:
			line = line.strip()
			if line == "":
				continue

			tag = self.parseTag(line)
			if tag == ():
				self.warn += "; can not parse %s" % line
				continue

			key, value = tag
			if key == "":
				self.warn += "; missing tag name for %s" % line
				continue

			key = key.lower()
			if key == "source0":
				key = "source"

			value = value.strip()
			self.tags[key] = value

	def parsePackageSections(self, sections):
		packageSections = {}
		for name in sections['name']:
			br = []
			r = []
			p = []
			for line in sections['value'][name]:
				line = line.strip()
				if line.lower().startswith('buildrequires'):
					tag = self.parseTag(line)
					if tag == ():
						self.warn += "; can not parse %s" % line
						continue

					_, value = tag
					value = re.sub(r'[ \t]+', ' ', value)
					vbr = value.split(' ')[0]
					br.append(vbr)
				if line.lower().startswith('requires'):
					tag = self.parseTag(line)
					if tag == ():
						self.warn += "; can not parse %s" % line
						continue

					_, value = tag
					value = re.sub(r'[ \t]+', ' ', value)
					vr = value.split(' ')[0]
					r.append(vr)
				if line.lower().startswith('provides'):
					tag = self.parseTag(line)
					if tag == ():
						self.warn += "; can not parse %s" % line
						continue
					_, value = tag
					value = re.sub(r'[ \t]+', ' ', value)
					vp = value.split(' ')[0]
					p.append(vp)
			
			obj = PackageSection(name)
			obj.setBuildRequires(br)
			obj.setRequires(r)
			obj.setProvides(p)
			packageSections[name] = obj

		return packageSections

	def parseChangelog(self, section):
		"""
		Each changelog starts with *
		"""
		changelogs = []
		log = []
		chlog_obj = None
		for line in section:
			sline = line.strip()
			if sline == "":
				continue

			if sline[0] == "*":
				if chlog_obj != None:
					chlog_obj.comment = log
					changelogs.append(chlog_obj)
				log = []
				chlog_obj = Changelog()
				chlog_obj.header = sline
			else:
				log.append(line)

		if chlog_obj != None:
			chlog_obj.comment = log
			changelogs.append(chlog_obj)

		return changelogs
