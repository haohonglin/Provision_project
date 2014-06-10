#!/usr/bin/python

from wsgiref.simple_server import make_server 
import socket, httplib, os, string
import urlparse, time, threading, sys, signal
import common
from common import MetaConfigure
from common import ProvisionInstanceMetric
from common import ProvisionInstanceData
from common import ProvisionProxyMonitorData

class ProvisionReporter(threading.Thread):
    def __init__(self):
	threading.Thread.__init__(self)
	self.instance_metric = ProvisionInstanceMetric()
	self.self_stopped = 0

	self.metaConfigure = MetaConfigure()

    def run(self):
	while not self.self_stopped:
	    self._pooling_instances()
	    time.sleep(self.pooling_interval)
	    if self.metaConfigure._is_debug():
		print 'polling instance ...'
	print 'stop connect to monitor'

    def join_reporter(self):
	self.self_stopped = 1
	self.join()

    def _pooling_instances(self):
	count=0
	for inst in self.instance_metric.instance_list:
	    if instance.status == "RUNNING":
		count =count + 1
	    if not inst._is_booted_reported():
		#send notification to host
		print 'report one booted instance %s' % str(inst._get_info())
		inst._set_report_of_booted_instance()
	    elif inst._is_terminated_reported():
		#send notification to host
		print 'report one terminated instance %s' % str(inst._get_info())
		inst._set_report_of_terminated_instance()


class ProvisionMonitor(threading.Thread):
    def __init__(self):
	threading.Thread.__init__(self)
	self.instance_metric = ProvisionInstanceMetric()
        self.terminate_flag = 0

        self.metaConfigure = MetaConfigure()

	self.host_ip = self.metaConfigure._get_provision_host_ip() or '0.0.0.0'
	self.host_port = self.metaConfigure._get_provision_host_port() or 8675
	self.proxy_port = self.metaConfigure._get_proxy_port() or 8821
	self.report_online =self.metaConfigure._is_report_online()

	self.self_stopped = False
	self.httpd = make_server('', self.host_port, self.provision_monitor_app) 
	self.httpd.timeout = self.metaConfigure._get_http_timeout()

	self.proxy_data = ProvisionProxyMonitorData(host_port = self.host_port)

    def terminate_monitor(self):
	self.self_stopped = True
	self.join()

    def run(self):
	self.serve()

    def serve(self):
	print "Serving on port %d..." % self.host_port
	while not self.self_stopped:
	    self.httpd.handle_request()
	    if self.metaConfigure._is_debug():
		print 'handle one request or timeout ...'
	print "Stop monitor server..."
	#self.httpd.serve_forever()
  
    def provision_monitor_app(self, environ, start_response):  
	print 'one request coming'
        status = '200 OK' # HTTP Status  
        headers = [('Content-type', 'text/plain')] # HTTP Headers  
        start_response(status, headers) 

	proxy_req = urlparse.parse_qs(environ['QUERY_STRING'])
	print proxy_req.keys()
	if 'VMType' in proxy_req.keys():
	    if proxy_req['VMType'] == ['proxy'] and 'PublicIP' in proxy_req.keys() and 'CurTime' in proxy_req.keys():
		print "proxy private ip: %s" % self.proxy_data.priv_ip
		#if proxy_req['PrivateIP'][0] != self.proxy_data.priv_ip :
		if proxy_req['Key'][0] != self.proxy_data.key :
		    print "recieve old proxy vm connection: %s" % proxy_req
		    return ["Error: old provison proxy connection"]
		self.proxy_data.connected_with_proxy=True
		#if 'PrivateIP' in proxy_req.keys():
		#    self.proxy_data._set_pub_priv_ip(proxy_req['PublicIP'][0], proxy_req['PrivateIP'][0])
		#else:
		#    self.proxy_data._set_pub_ip(proxy_req['PublicIP'][0])
		
		monitor_base = time.time()
		self.proxy_data._sync_time(proxy_req['CurTime'][0], monitor_base)
		print self.proxy_data._get_info()
		print "hahhah, proxy connection is coming!!!!"
                return ["200 OK!!!%s" % monitor_base]

	    #if proxy_req['VMType'] == ['instance'] and 'VMStatus' in proxy_req.keys() and 'VMName' in proxy_req.keys() and  'VMIP' in proxy_req.keys() and 'Timestamp' in proxy_req.keys():
	    if proxy_req['VMType'] == ['instance'] and 'VMStatus' in proxy_req.keys() and 'VMName' in proxy_req.keys() and 'Timestamp' in proxy_req.keys():
		instance = self.instance_metric._get_instance_by_name(proxy_req['VMName'][0])
		if instance is None:
		    print 'can not find instance from metric'
		    print proxy_req['VMName']
		    return ["no found"]

		if proxy_req['VMStatus'][0] == 'BOOTED' :
		    ip_lease = 0
		    if 'IPLease' in proxy_req.keys():
			ip_lease = proxy_req['IPLease'][0]
		    ProvisionInstanceMetric()._update_instance(instance, "RUNNING", proxy_req['Timestamp'][0], ip_lease) #time.time())
		    print "instance[%s] has finished booted, booted time[%s], dhcp time:%s" % (proxy_req['VMName'], proxy_req['Timestamp'], str(proxy_req['IPLease'][0]))  
		elif proxy_req['VMStatus'][0] == 'DELETED' :
		    ProvisionInstanceMetric()._update_instance(instance, "DELETED", proxy_req['Timestamp'][0]) #time.time())
		    print "instance[%s] has been deleted, deleted time[%s]" % (proxy_req['VMName'], proxy_req['Timestamp'])  
                return ["200 OK"]
	
	return ["Error:(%s) do not include \'hostname\', \'ip\' and \'status[boot|terminate]\'" % environ['QUERY_STRING']]


'''WARNING:  ProvisionMonitorNovaList is using nova list to poll and detect instance status. 
However as we found, it will add extra stress to neutron server because nova list will introduce the list port action.
Meanwhile, the spend time of nova list is not steadable, it will enlarge when the vm number in openstack becomes large.'''

class ProvisionMonitorNovaList(threading.Thread):
	''' The class is a thread to monitor all the provisions '''
	def __init__(self, cloud_api, client_list):
		threading.Thread.__init__(self)
		self.client_list=client_list
		self.start_flag=False
		self.terminate_flag=False
		self.cloud_api=cloud_api
		self.loop_interval=4

	def run(self):
		self.monitor_provision()

	def terminate_monitor(self):
		self.terminate_flag=True
		self.join_monitor()
		self.terminate_flag=False	
	
	def start_monitor(self):
		self.start_flag=True
		self.start()

	def join_monitor(self):
		self.start_flag=False
		self.join()

	def _translate_keys(self, collection, convert):
    		for item in collection:
        		keys = item.__dict__.keys()
        		for from_key, to_key in convert:
            			if from_key in keys and to_key not in keys:
                			setattr(item, to_key, item._info[from_key])

	def _list_instances(self):
		formatters={}
		field_titles=[]
		id_col = 'ID'
		servers=self.cloud_api.list_instances()
	    	convert = [('OS-EXT-SRV-ATTR:host', 'host'),
               		('OS-EXT-STS:task_state', 'task_state'),
               		('OS-EXT-SRV-ATTR:instance_name', 'instance_name'),
               		('hostId', 'host_id')]
    		self._translate_keys(servers, convert)
    		if field_titles:
        		columns = [id_col] + field_titles
    		else:
        		columns = [id_col, 'Name', 'Status', 'Networks']
    		formatters['Networks'] = utils._format_servers_list_networks
    		utils.print_list(servers, columns,
                     	formatters, sortby_index=1)


	def monitor_provision(self):
		while not (self.start_flag or self.terminate_flag) :
			sleep(self.loop_interval)

#		while not self.terminate_flag:
#			self._list_instances()
#			sleep(self.loop_interval)

		while not self.terminate_flag:
			count=0
			start_time=time.time()
			#print self.cloud_api.list_instance()
			os.system("nova list|grep client_ > nova.list")	
			for provision in self.client_list:
				if provision._update_instance_status("nova.list"):
					count = count + 1
		
			print "##monitor loop## client:%d, finished: %d, loop time: %d" % ( len(self.client_list), count, time.time() - start_time )

			if count == len(self.client_list) :
				print self.start_flag
			if (count == len(self.client_list)) and ( not self.start_flag) :
				break
			
			sleep(self.loop_interval)
