import optparse
from modules.Packages import buildRequirementGraph, getSCC, getLeafPackages, getRootPackages, ConnectedComponent, joinGraphs
from modules.Utils import runCommand
import tempfile
import shutil
from time import time, strftime, gmtime


def printSCC(scc):
	print "Cyclic dep detected (%s): %s" % (len(scc), ", ".join(scc))

def getGraphvizDotFormat(graph):
	nodes, edges = graph

	#digraph { a -> b; b -> c; c -> d; d -> a; }
	content = "digraph {\n"
	for u in nodes:
		if u in edges:
			for v in edges[u]:
				content += "%s -> %s;\n" % (u.replace('-', '_'), v.replace('-', '_'))

	# add nodes with no outcoming edge
	leaves = getLeafPackages(graph)
	for leaf in leaves:
		content += "%s [style=filled, fillcolor=orange]" % leaf.replace('-', '_')

	# add nodes with no incomming edge
	roots = getRootPackages(graph)
	for root in roots:
		content += "%s [style=filled, fillcolor=red3]" % root.replace('-', '_')

	# add cyclic deps
	scc = getSCC(graph)

	colors = ['purple', 'salmon', 'forestgreen', 'dodgerblue', 'yellow']
	col_len = len(colors)

	counter = 0
	for comp in scc:
		if len(comp) > 1:
			for elem in comp:
				content += "%s [style=filled, fillcolor=%s]" % (elem.replace('-', '_'), colors[counter])
			counter = (counter + 1) % col_len


	content += "}\n"
	return content

def showGraph(graph, out_img = "./graph.png"):
	tmp_dir = tempfile.mkdtemp()
	f = open("%s/graph.dot" % (tmp_dir), "w")
	f.write(getGraphvizDotFormat(graph))
	f.close()
	# fdp -Tpng test.dot > test.png
	_, _, rc = runCommand("fdp -Tpng %s/graph.dot > %s" % (tmp_dir, out_img))
	if rc != 0:
		print "Unable to generate graph"
		return

	print "Graph saved to: %s\nYou can use eog %s to open it." % (out_img, out_img)
	# eog test.png
	shutil.rmtree(tmp_dir)

def truncateGraph(graph, pkg_name, pkg_devel_main_pkg):
	"""
	Return graph containing only pkg_name and all its dependencies
	"""
	# 1. get all devel subpackages belonging to pkg_name
	root_nodes = []
	for devel in pkg_devel_main_pkg:
		if pkg_devel_main_pkg[devel] == pkg_name:
			root_nodes.append(devel)

	# 2. create a set of all nodes containg the subpackages and
	# all nodes reacheable from them
	subgraph = None
	for node in root_nodes:
		cc = ConnectedComponent(graph, node)
		if subgraph == None:
			subgraph = cc.getCC()
		else:
			subgraph = joinGraphs(subgraph, cc.getCC())

	return subgraph
	
if __name__ == "__main__":

	parser = optparse.OptionParser("%prog -c|-l|-r|-g [-v] [PACKAGE]")

	parser.add_option(
	    "", "-v", "--verbose", dest="verbose", action = "store_true", default = False,
	    help = "Display all warnings and errors as well"
	)

	parser.add_option(
	    "", "-c", "--cyclic", dest="cyclic", action = "store_true", default = False,
	    help = "Get cyclic dependencies between golang packages"
	)

	parser.add_option(
	    "", "-l", "--leaves", dest="leaves", action = "store_true", default = False,
	    help = "Get golang packages without dependencies, only native imports"
	)

	parser.add_option(
	    "", "-r", "--roots", dest="roots", action = "store_true", default = False,
	    help = "Get golang packages not required by any package"
	)

	parser.add_option(
	    "", "-g", "--graphviz", dest="graphviz", action = "store_true", default = False,
	    help = "Output graph in a graphviz dot format. Red are packages not required, orange leaf packages, colored are packages with cyclic dependency."
	)

	parser.add_option(
	    "", "-o", "--outfile", dest="outfile", default = "",
	    help = "Get golang packages not required by any package"
	)

	parser.add_option_group( optparse.OptionGroup(parser, "PACKAGE", "Display the smallest subgraph containing PACKAGE and all its dependencies.") )

	# get list of tools/packages providing go binary

	options, args = parser.parse_args()
	pkg_name = ""
	if len(args) > 0:
		pkg_name = args[0]

	if options.cyclic or options.leaves or options.roots or options.graphviz:

		print "Reading packages..."
		scan_time_start = time()
		graph, pkg_devel_main_pkg = buildRequirementGraph(options.verbose)
		nodes, _ = graph
		graph_cnt = len(nodes)

		if pkg_name != "":
			graph = truncateGraph(graph, pkg_name, pkg_devel_main_pkg)
			nodes, _ = graph
			subgraph_cnt = len(nodes)
			
		scan_time_end = time()
		print strftime("Completed in %Hh %Mm %Ss", gmtime(scan_time_end - scan_time_start))
		if pkg_name != "":
			print "%s nodes of %s" % (graph_cnt, subgraph_cnt)
		else:
			print "%s nodes in total" % (graph_cnt)


		if options.cyclic:
			scc = getSCC(graph)

			for comp in scc:
				if len(comp) > 1:
					printSCC(comp)

		elif options.leaves:
			leaves = getLeafPackages(graph)
			for leaf in leaves:
				print leaf

		elif options.roots:
			roots = getRootPackages(graph)
			for root in roots:
				print root

		elif options.graphviz:
			if options.outfile != "":
				showGraph(graph, options.outfile)
			else:
				showGraph(graph)
			

	else:
		print "Synopsis: prog -c|-l|-r|-g [-v] [PACKAGE]"
