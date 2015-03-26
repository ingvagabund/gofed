import optparse
from modules.GoSymbols import getSymbolsForImportPaths, PackageToXml, ProjectToXml
import json

def displaySymbols(symbols, all = False, stats = False):
	# types, funcs, vars
	if all:
		names = []
		for item in symbols["types"]:
			names.append(item["name"])
		for item in symbols["funcs"]:
			names.append(item["name"])
		for item in symbols["vars"]:
			names.append(item)

		if stats:
			print "  Total symbols: %s" % len(names)
		else:
			for item in sorted(names):
				print "  %s" % item

	else:
		names = []
		for item in symbols["types"]:
			names.append(item["name"])

		if stats:
			print "  Total types: %s" % len(names)
		else:
			for item in sorted(names):
				print "  type: %s" % item

		names = []
		for item in symbols["funcs"]:
			names.append(item["name"])

		if stats:
			print "  Total funcs: %s" % len(names)
		else:
			for item in sorted(names):
				print "  func: %s" % item

		names = []
		for item in symbols["vars"]:
			names.append(item)

		if stats:
			print "  Total vars:  %s" % len(names)
		else:
			for item in sorted(names):
				print "  var:  %s" % item

def setOptionParser():

	parser = optparse.OptionParser("%prog -l|-u|-p [-a] [-s] [-x] dir")

        parser.add_option_group( optparse.OptionGroup(parser, "dir", "Directory to scan at.") )

	parser.add_option(
	    "", "-l", "--list", dest="list", action = "store_true", default = False,
	    help = "List all symbols for all import paths of a golang devel package."
	)

	parser.add_option(
	    "", "", "--prefix", dest="prefix", default = "",
	    help = "Prefix prepended to all listed import paths followed by slash /."
	)

	parser.add_option(
	    "", "-a", "--all", dest="all", action = "store_true", default = False,
	    help = "Normally symbols are prefixed by its type. This flag ignores the type and list all symbols as equal."
	)

	parser.add_option(
	    "", "-s", "--stats", dest="stats", action = "store_true", default = False,
	    help = "Don't list symbols, show their count for each import path instead."
	)

	parser.add_option(
	    "", "-x", "--xml", dest="xml", action = "store_true", default = False,
	    help = "List symbols in xml format."
	)

	parser.add_option(
	    "", "-u", "--usedip", dest="usedip", action = "store_true", default = False,
	    help = "List all imported paths/packages."
	)

	parser.add_option(
	    "", "-p", "--provides", dest="provides", action = "store_true", default = False,
	    help = "List all provided import paths."
	)

	return parser


if __name__ == "__main__":

	parser = setOptionParser()

	options, args = parser.parse_args()

	if len(args) < 1:
		print "Synopsis: prog -l|-u|-p [-a] [-s] [-x] dir"
		exit(1)

	go_dir = args[0]

	prefix = ""
	if options.prefix != "":
		prefix = options.prefix + "/"

	#obj = ProjectToXml(options.prefix, go_dir)
	#print obj
	#print obj.getError()
	#exit(0)

	ip_used = []
	if options.provides:
		err, ip, _, _ = getSymbolsForImportPaths(go_dir)
		if err != "":
			print err
			exit(1)

		ips = []
		for pkg in ip:
			ips.append(ip[pkg])

		for ip in sorted(ips):
			if ip == "." and options.prefix != "":
				print options.prefix
			else:
				print "%s%s" % (prefix, ip)

	elif options.list:
		err, ip, symbols, ip_used = getSymbolsForImportPaths(go_dir)
		if err != "":
			print err
			exit(1)
		for pkg in ip:
			print "Import path: %s%s" % (prefix, ip[pkg])
			#print json.dumps(symbols[pkg])
			if options.xml:
				obj = PackageToXml(symbols[pkg], "%s%s" % (prefix, ip[pkg]),  imports=False)
				if obj.getStatus():
					print obj#.getError()
				else:
					print obj.getError()
					exit(0)
			else:
				displaySymbols(symbols[pkg], options.all, options.stats)

	elif options.usedip:
		if ip_used != []:
			print ""
			print "Used import paths:"
		else:
			err, _, _, ip_used = getSymbolsForImportPaths(go_dir, imports_only=True)
			if err != "":
				print err
				exit(1)
	
		for uip in sorted(ip_used):
			print uip

