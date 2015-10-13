from subprocess import PIPE, Popen, call
import os
import sys

RED = '\033[91m'
GREEN = '\033[92m'
BLUE = '\033[94m'
CYAN = '\033[96m'
WHITE = '\033[97m'
YELLOW = '\033[93m'
MAGENTA = '\033[95m'
GREY = '\033[90m'
BLACK = '\033[90m'
DEFAULT = '\033[99m'
ENDC = '\033[0m'

def getScriptDir():
	return os.path.dirname(os.path.realpath(__file__))

LOG_LEVEL_ERROR = 0
LOG_LEVEL_WARNING = 1
LOG_LEVEL_INFO = 2

LOG_FILE = "/var/lib/gofed/gofed.log"

class Logger:

	def __init__(self, level=LOG_LEVEL_INFO):
		self.level = level
		#self.log_file = open(LOG_FILE, "w")
		self.log_file = sys.stderr

	#def __del__(self):
	#	self.log_file.close()

	def log(self, msg, level=""):
		print msg
		print LOG_FILE

		if level == "":
			self.log_file.write("%s: %s\n" % (self.level, msg))
		else:
			self.log_file.write("%s: %s\n" % (level, msg))

class FormatedPrint:

	def __init__(self, formated=True):
		self.formated = formated

	def printError(self, msg):
		if self.formated:
			sys.stderr.write("%sError: %s%s\n" % (RED, msg, ENDC))
		else:
			sys.stderr.write("Error: %s\n" % msg)

	def printWarning(self, msg):
		if self.formated:
			sys.stderr.write("%sWarning: %s%s\n" % (YELLOW, msg, ENDC))
		else:
			sys.stderr.write("Warning: %s\n" % msg)

	def printInfo(self, msg):
		if self.formated:
			sys.stdout.write("%s%s%s\n" % (BLUE, msg, ENDC))
		else:
			sys.stdout.write("%s\n" % msg)

	def printProgress(self, msg):
		if self.formated:
			sys.stdout.write("%s%s%s\n" % (CYAN, msg, ENDC))
		else:
			sys.stdout.write("%s\n" % msg)


def runCommand(cmd):
	#cmd = cmd.split(' ')
	process = Popen(cmd, stderr=PIPE, stdout=PIPE, shell=True)
	stdout, stderr = process.communicate()
	rt = process.returncode

	return stdout, stderr, rt

def execCommand(command):
	call(command, shell=True)

def inverseMap(mfnc):
	"""inverse mapping of multifunction

	Keyword arguments:
	mfnc -- multifunction
	"""
	imap = {}
	for key in mfnc:
		for image in mfnc[key]:
			if image not in imap:
				imap[image] = [key]
			else:
				imap[image].append(key)
	return imap

def format_output(fmt, out, fancy = False):
	def format_filter(fmt, line):
		column = []
		for pattern in fmt:
			if pattern in line:
				column.append(line[pattern])
		return column

	def normal_format_str(fmt):
			ret = ''.join(['{} ' for num in xrange(len(fmt))])
			return ret[:-1] # omit space at the end of line

	ret = ""
	fmt = fmt.split(':')

	if type(out) is list:
		row_format = ""
		if fancy:
			for pattern in fmt:
				l = 0
				for item in out:
					if pattern in item:
						if l < len(str(item[pattern])) + 1:
							l = len(str(item[pattern])) + 1
				if len(row_format) > 0 and l > 0:
					row_format  += "{:>%d}" % l # first row is left aligned
				elif l > 0: # do not add non existing key -- STFU and ignore it
					row_format  += "{:<%d}" % l
		else:
			row_format = normal_format_str(fmt)

		for line in out:
			column = format_filter(fmt, line)
			if column:
				ret += row_format.format(*tuple(column)) + '\n'
	else: # actually we don't need to be fancy with one-liners
		row_format = normal_format_str(fmt)
		column = format_filter(fmt, out)
		if column:
			ret = row_format.format(*tuple(column)) + '\n'

	return ret[:-1] # omit confusing blank line in output

