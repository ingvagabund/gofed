# -*- coding: utf-8 -*-
# ####################################################################
# gofed - set of tools to automate packaging of golang devel codes
# Copyright (C) 2015  Fridolin Pokorny, fpokorny@redhat.com
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
# ####################################################################

import optparse
import sys
import json
import logging
from modules.RESTClient import RESTClient
from modules.Utils import format_output
from modules.Config import Config

# Logger
logger = logging.getLogger('gofed-client')
logger.addHandler(logging.StreamHandler(sys.stderr))

def check_opts(options):
	# is there something to do?
	if not options.list and not options.info and not options.commit and \
			not options.depth and not options.date and not options.check_commit:
			logger.error("Error: nothing to do, use --help to see all available commands")
			return False

	# disjoint commands
	if (options.list and options.info)    or (options.list and options.commit)        or \
		(options.list and options.depth)   or (options.list and options.date)          or \
		(options.list and options.check_commit) or                                        \
		(options.info and options.commit)  or (options.info and options.depth)         or \
		(options.info and options.date)    or (options.info and options.check_commit)  or \
		(options.commit and options.depth) or (options.commit and options.date)        or \
		(options.commit and options.check_commit) or                                      \
		(options.depth and options.date)   or (options.depth and options.check_commit) or \
		(options.date and options.check_commit):
			logger.error("Error: please specify only one action to do")
			return False

	if options.list:
		if options.project:
			logger.error("Error: --list does not require --project")
			return False

		if options.query_from or options.query_to or options.query_depth:
			logger.error("Error: --query-depth is not valid for --list")
			return False

	if options.graph and (options.json or options.fmt or options.fancy_fmt):
		logger.error("Error: could not make JSON nor formatted string from a graph")
		return False

	# all other commands need project defined
	if not options.list and not options.project:
		logger.error("Error: --project required in order to process this request")
		return False

	if options.info:
		if options.query_from or options.query_to or options.query_depth:
			logger.error("Error: --query-depth is not valid for --info")
			return False

	if options.commit:
		if options.query_depth:
			logger.error("Error: --query-depth is not valid for --commit")
			return False

		if not options.query_from: # query_to is optional
			logger.error("Error: --from is required for --commit")
			return False

	if options.depth:
		if options.query_to:
			logger.error("Error: --to is not valid for --depth")
			return False

	if options.date:
		if options.query_depth:
			logger.error("Error: --query_depth is not valid for --date")
			return False

	if options.check_commit:
		if options.query_depth:
			logger.error("Error: --query-depth is not valid for --check-deps")
			return False

		if options.query_from or options.query_to or options.query_depth:
			logger.error("Error: --check-deps does not require boundaries")
			return False

		if options.graph:
			logger.error("Error: --graph is not valid for --check-deps")
			return False

	if options.json and (options.fmt or options.fancy_fmt):
		logger.error("Error: JSON and formatting options are disjoint")
		return False

	if options.fmt and options.fancy_fmt:
		logger.error("Error: --fmt and --FMT are disjoint")
		return False

	return True

if __name__ == "__main__":
	output = None

	parser = optparse.OptionParser("%prog OPTIONS [FILE]")

	parser.add_option_group(optparse.OptionGroup(
												parser,
												"FILE",
												"Output file for the request output"
												)
	)

	parser.add_option_group(optparse.OptionGroup(
												parser,
												"FROM",
		"Specify `from' in a range based filter. For --commit and --depth "
		"specify starting commit by its hash. If date filtering is requested, "
		"specify starting date in ISO-style format (YYYY-MM-DD). "
		"If omitted, the newest commit (current date respectively) is used."
												)
	)

	parser.add_option_group(optparse.OptionGroup(
												parser,
												"TO",
		"Specify `to' in a range based filter. For --commit "
		"specify ending commit by its hash. If date filtering is requested, "
		"specify ending date in ISO-style format (YYYY-MM-DD)."
												)
	)

	parser.add_option_group(optparse.OptionGroup(
												parser,
												"QUERY_DEPTH",
		"Specify depth for depth filtering. "
		"If omitted, it defaults to %d." % Config().getGofedWebDepth()
												)
	)

	parser.add_option_group(optparse.OptionGroup(
												parser,
												"GRAPH",
		'Available graphs: "added", "modified", "cpc"; '
		'also available in abbreviate forms "a", "m" and "c". Output is in an '
		'SVG format.',
												)
	)

	parser.add_option_group(optparse.OptionGroup(
												parser,
												"FORMAT",
		'Specify format for output string. Format should be specified by keys '
		'from response delimited by ":" - e.g. to print only "author" '
		'and "commit" in this order use `--fmt "author:commit"\'. To print output '
		'in a fancy way, use `--FMT "author:commit"\'. Invalid keys are ignored.'
												)
	)

	parser.add_option(
		"", "-p", "--project", dest="project", action = "store", type = "string",
		help = "name of the project"
	)

	parser.add_option(
		"", "-l", "--list", dest="list", action = "store_true", default = False,
		help = "list all available golang projects"
	)

	parser.add_option(
		"", "-i", "--info", dest="info", action="store_true", default = False,
		help = "show info about specific golang project"
	)

	parser.add_option(
		"", "-c", "--commit", dest="commit", action = "store_true", default = False,
		help = "show APIdiff of a project based on commit range"
	)

	parser.add_option(
	    "", "-m", "--depth", dest="depth", action = "store_true", default = False,
	    help = "show APIdiff of a project based on depth"
	)

	parser.add_option(
		"", "-d", "--date", dest="date", action = "store_true", default = False,
		help = "show APIdiff of a project based on a date frame"
	)

	parser.add_option(
		"", "-w", "--url", dest="url", action = "store", type="string",
		default = Config().getGofedWebUrl(),
		help = "URL of gofed-web (default: %s)" % Config().getGofedWebUrl()
	)

	parser.add_option(
		"", "-f", "--from", dest="query_from", action = "store", type="string",
		help = "specify from filtering, see `FROM' for more details"
	)

	parser.add_option(
		"", "-t", "--to", dest="query_to", action = "store", type="string",
		help = "specify to filtering, see `TO' for more details"
	)

	parser.add_option(
		"", "-g", "--graph", dest="graph", action = "store", type="choice",
		choices=["added", "modified", "a", "m", "cpc"],
		help = "specify graph type, see GRAPH for more details"
	)

	parser.add_option(
		"", "-q", "--query-depth", dest="query_depth", action = "store", type="int",
		help = "specify depth filtering, see `QUERY_DEPTH' "
				 "for more details (default: %d)" % Config().getGofedWebDepth()
	)

	parser.add_option(
		"", "-a", "--check-deps", dest="check_commit", action = "store", type="string",
		help = "compare commit CHECK_COMMIT with current Fedora package"
	)

	parser.add_option(
		"", "-J", "--json", dest="json", action = "store_true", default=False,
		help = "output in formatted JSON"
	)

	parser.add_option(
		"", "", "--fmt", dest="fmt", action = "store", type = "string",
		help = "define format string, see FORMAT for more details"
	)

	parser.add_option(
		"", "", "--FMT", dest="fancy_fmt", action = "store", type = "string",
		help = "define format string; output is formatted to be more fancy, "
				 "see FORMAT for more details"
	)

	parser.add_option(
		"", "-v", "--verbose", dest="verbose", action = "store_true", default = False,
		help = "print debug messages"
	)

	options, args = parser.parse_args()

	if len(args) > 1:
		logger.error("Error: Incorrect number of arguments")
		exit(1)

	if not check_opts(options):
		exit(2)

	if len(args) == 1:
		output = args[0]

	if options.verbose:
		logger.setLevel(logging.DEBUG)

	rest_client = RESTClient(options.url)

	# server probing
	try:
		if options.list:
			ret = rest_client.query_list()
		elif options.info:
			ret = rest_client.query_info(options.project)
		elif options.commit:
			if options.graph:
				ret = rest_client.graph_commit(options.project, options.query_from, options.query_to, options.graph)
			else:
				ret = rest_client.query_commit(options.project, options.query_from, options.query_to)
		elif options.depth:
			if not options.query_depth:
				options.query_depth = Config().getGofedWebDepth()
			if options.graph:
				ret = rest_client.graph_depth(options.project, options.query_depth, options.query_from, options.graph)
			else:
				ret = rest_client.query_depth(options.project, options.query_depth, options.query_from)
		elif options.date:
			if options.graph:
				ret = rest_client.graph_date(options.project, options.query_from, options.query_to, options.graph)
			else:
				ret = rest_client.query_date(options.project, options.query_from, options.query_to)
		elif options.check_commit:
			ret = rest_client.query_check_deps(options.project, options.check_commit)
		else:
			"Error: nothing to do, use --help to see all available commands"
	except Exception as e:
		logger.error("Error: %s" % str(e))
		sys.exit(3)

	# finishing output
	if options.json:
		ret = json.dumps(ret, sort_keys = True, indent = 2, separators = (',', ': '))
	elif options.fmt:
		ret = format_output(options.fmt, ret, fancy=False)
	elif options.fancy_fmt:
		ret = format_output(options.fancy_fmt, ret, fancy=True)
	elif not options.graph:
		ret = json.dumps(ret)

	if output:
		try:
			logger.debug("writting output to " + output)
			with open(output, 'w') as f:
				f.write(ret)
		except Exception as e:
			logger.error("Error: %s" % str(e))
			exit(4)
	else:
		if len(ret) > 0:
			print ret

