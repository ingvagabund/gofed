# -*- coding: utf-8 -*-
import json
import urllib2
from modules.Config import Config
from dateutil.parser import parse as datetime_parse
from datetime import datetime

class RESTClient:

	def __init__(self, url = Config().getGofedWebUrl()):
		self.url = url
		pass

	def __url_append(self, url, what):
		if type(what) is list:
			for item in what:
				if url[-1] != '/':
					url += '/'
				if item:
					url += str(item)
				else:
					url += '/'
		else:
			if url[-1] != '/':
				url += '/'
			url += what

		return url

	def __get_rest_url(self):
		return self.__url_append(self.url, 'rest/')

	def __get_graph_url(self):
		return self.__url_append(self.url, 'graph/')

	def __get_http_data(self, url):
		#print "query: " + url
		response = urllib2.urlopen(url)
		ret = response.read()
		return ret

	def __prepare_date(self, date):
		if not date:
			return ""
		if type(date) is str:
			date = datetime_parse(date)
		return date.strftime("%Y-%m-%d")

	# REST
	def query_list(self):
		url = self.__url_append(self.__get_rest_url(), 'list/')
		ret = self.__get_http_data(url)
		return json.loads(ret)

	def query_info(self, project):
		url = self.__url_append(self.__get_rest_url(), ['info/', project])
		ret = self.__get_http_data(url)
		return json.loads(ret)

	def query_commit(self, project, qfrom, qto):
		url = self.__url_append(self.__get_rest_url(), ['commit/', project, qfrom, qto])
		ret = self.__get_http_data(url)
		return json.loads(ret)

	def query_depth(self, project, qdepth, qfrom):
		url = self.__url_append(self.__get_rest_url(), ['depth/', project, qdepth, qfrom])
		ret = self.__get_http_data(url)
		return json.loads(ret)

	def query_date(self, project, qfrom, qto):
		if not qfrom:
			qfrom = datetime.now()
		url = self.__url_append(self.__get_rest_url(),
								['date/', project, self.__prepare_date(qfrom), self.__prepare_date(qto)])
		ret = self.__get_http_data(url)
		return json.loads(ret)

	def query_check_deps(self, project, qcommit):
		url = self.__url_append(self.__get_rest_url(), ['check-deps/', project, qcommit])
		ret = self.__get_http_data(url)
		return json.loads(ret)

	# GRAPH
	def graph_commit(self, project, qfrom, qto, graph_type):
		url = self.__url_append(self.__get_graph_url(),
								[graph_type, 'commit/', project, qfrom, qto, 'graph.svg'])
		return self.__get_http_data(url)

	def graph_depth(self, project, qdepth, qfrom, graph_type):
		url = self.__url_append(self.__get_graph_url(),
								[graph_type, 'depth/', project, qdepth, qfrom, 'graph.svg'])
		return self.__get_http_data(url)

	def graph_date(self, project, qfrom, qto, graph_type):
		url = self.__url_append(self.__get_graph_url(), [graph_type, 'date/', project,
									self.__prepare_date(qfrom), self.__prepare_date(qto), 'graph.svg'])
		return self.__get_http_data(url)

