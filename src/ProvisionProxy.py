#!/usr/bin/python
import logging
from wsgiref.simple_server import make_server 
import socket, httplib, os, string
import urlparse, time, threading, sys, signal
import argparse
import fcntl 
import struct


LOG = logging.getLogger(__name__)  
LOG.setLevel(logging.DEBUG)  
  
fh = logging.FileHandler('proxy.log')  
fh.setLevel(logging.DEBUG)  
  
ch = logging.StreamHandler()  
ch.setLevel(logging.DEBUG)  
 
formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')  
fh.setFormatter(formatter)  
ch.setFormatter(formatter)  
 
LOG.addHandler(fh)  
LOG.addHandler(ch)  

parser = argparse.ArgumentParser(description='Provision Proxy.')
parser.add_argument('--debug', default=False, action='store_true', help="if true, load configure from args instead of meta.js")
parser.add_argument('--meta', default=False, action='store_true', help="if true, load configure from args instead of meta.js")
parser.add_argument('--host-addr', default='0.0.0.0:8888', help='address of provision test-end.')
parser.add_argument('--proxy-port', default='8821', help='port of provision proxy.')
parser.add_argument('--report-offline', default=False, action='store_true', help='if true, report vm boot time after everything has finished')
parser.add_argument('--polling-interval', type=int, default=1, help='the interval that proxy report to host')
parser.add_argument('--http-timeout', type=int, default=2, help='timeout when httdp handle one request')

def singleton(class_):
    instances = {}
    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]
    return getinstance

@singleton
class MetaConfigure(object):
    def __init__(self):
	self.metadict={}
        self.config = parser.parse_args(sys.argv[1:])
	self._load_configure()

    def _load_configure(self):
	if not self.config.debug:
            meta_file=open('/meta.js','r')
            try:
                metastr=meta_file.readline()
                self.metadict=eval(metastr)
                LOG.debug("%s" % self.metadict)
            except Exception, e:
                print e
            finally:
                if meta_file:
                    meta_file.close()

	if 'host_addr' in self.metadict.keys():
	    self.config.host_addr = self.metadict['host_addr']
	else:
	    self.metadict['host_addr'] = self.config.host_addr

	if 'proxy_port' in self.metadict.keys():
	    self.config.proxy_port = self.metadict['proxy_port']
	else:
	    self.metadict['proxy_port'] = self.config.proxy_port

	if 'report_offline' in self.metadict.keys():
	    self.config.report_offline = self.metadict['report_offline']
	else:
	    self.metadict['report_offline'] = self.config.report_offline

	if 'polling_interval' in self.metadict.keys():
	    self.config.polling_interval = self.metadict['polling_interval']
	else:
	    self.metadict['polling_interval'] = self.config.polling_interval

	if 'http_timeout' in self.metadict.keys():
	    self.config.http_timeout = self.metadict['http_timeout']
	else:
	    self.metadict['http_timeout'] = self.config.http_timeout
        LOG.debug("%s" % self.metadict)

    def _is_debug(self):
	return self.config.debug

    def _get_provision_host_ip(self):
	return self.metadict['host_addr'].split(':')[0]

    def _get_provision_host_port(self):
	return string.atoi(self.metadict['host_addr'].split(':')[1])

    def _get_proxy_port(self):
	return string.atoi(self.metadict['proxy_port'])

    def _is_report_online(self):
	return not self.metadict['report_offline']

    def _get_polling_interval(self):
	return self.metadict['polling_interval']

    def _get_http_timeout(self):
	return self.metadict['http_timeout']

    def _get_key(self):
	return self.metadict['key']

    def _dump_configure(self):
	print self.metadict

@singleton
class ProvisionInstanceMetric(object):
	def __init__(self):
	    self.instance_list = []
	    self.instance_map = {}

	def _dump_instance_metric(self):
	    instances_dict = {}
            for inst in self.instance_list:
		instances_dict[inst.name] = inst._get_info()		
            return instance_dict

	def _append_instance(self, instance):
	    self.instance_list.append(instance)
	    print instance.name
	    self.instance_map[instance.name] = instance

	def _get_instance_by_name(self, inst_name):
	    if inst_name in self.instance_map.keys():
		return self.instance_map[inst_name]
	    return None

class ProvisionInstanceData:
	def __init__(self, instance_name, instance_ip, instance_booted_timestamp, ip_lease = 0, boot_reported = 0):
	    self.name = instance_name
	    self.ip = instance_ip
	    self.ip_lease = ip_lease

	    self.booted_timestamp = instance_booted_timestamp
	    self.boot_reported = boot_reported

	    self.terminated_timestamp = -1
	    self.terminated_flag = 0
	    self.terminate_reported = 0
	
	def _new_boot_req(self):
	    return '?VMType=instance'+'&VMStatus=BOOTED'+'&VMName='+self.name+'&VMIP='+self.ip+'&IPLease='+str(self.ip_lease)+'&Timestamp='+str(self.booted_timestamp)

	def _new_terminate_req(self):
	    return '?VMType=instance'+'&VMStatus=DELETED'+'&VMName='+self.name+'&VMIP='+self.ip+'&Timestamp='+str(self.terminated_timestamp)

	def _get_info(self):
	    info = {}
	    info['name'] = self.name
	    info['ip'] = self.ip
	    info['boot_report'] = self.boot_reported
	    info['booted_timestamp'] = str(self.booted_timestamp)
	    info['terminate_report'] = self.terminate_reported
	    info['terminated_tiemstamp'] = str(self.terminated_timestamp)
	    return info

	def _get_name(self):
	    return self.name

	def _get_ip(self):
	    return self.ip

	def _get_booted_timestamp(self):
	    return str(self.booted_timestamp)

	def _is_booted_reported(self):
	    return self.boot_reported

	def _set_report_of_booted_instance(self):
	    self.boot_reported = 1

	def _is_terminated_reported(self):
	    return self.boot_reported and self.terminated_flag and not self.terminate_reported

	def _set_timestamp_of_terminated_instance(self, terminated_timestamp):
	    self.terminated_timestamp = terminated_timestamp
	    self.terminated_flag = 1

	def _set_report_of_terminated_instance(self):
	    self.terminate_reported = 1

	def _get_terminated_timestamp(self):
	    return str(self.terminated_timestamp)

class Utils:
    @staticmethod
    def get_ip_address(ifname):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	ip_flag=False
	start=time.time()
	while not ip_flag:
	    try:
		print '%f' %(time.time() - start)
        	ip=socket.inet_ntoa(fcntl.ioctl(
                    s.fileno(),
                    0x8915,  # SIOCGIFADDR 
                    struct.pack('256s', ifname[:15])
                    )[20:24])
		ip_flag=True
		print '%f' %(time.time() - start)
		return ip, (time.time() - start)
	    except Exception, e:
		print e
		LOG.error( '%f' %(time.time() - start))
		time.sleep(1)

class ProxyPoolingInstance(threading.Thread):
    def __init__(self):
	threading.Thread.__init__(self)
	self.instance_metric = ProvisionInstanceMetric()
	self.self_stopped = 0

	self.metaConfigure = MetaConfigure()
	self.host_ip = self.metaConfigure._get_provision_host_ip()
	self.host_port = self.metaConfigure._get_provision_host_port()
	self.pooling_interval = self.metaConfigure._get_polling_interval()
	
	self.proxy_public_ip = Utils.get_ip_address('eth0')[0]
	self.proxy_private_ip = Utils.get_ip_address('eth0')[0]
	self.get_ip_lease = Utils.get_ip_address('eth0')[1]

	self.key = self.metaConfigure._get_key()

	self.proxy_base_time = -1
	self.host_base_time = -1

	self.connected_flag = False
#	self.monitorClient = self.connect_monitor()
#	self.lastNotifyItem = 0

    def run(self):
	while not self.self_stopped:
	    if not self.connected_flag:
		self.monitorClient = self.connect_monitor()
		self.lastNotifyItem = 0
	    self._pooling_instances()
	    time.sleep(self.pooling_interval)
	    if self.metaConfigure._is_debug():
		print 'polling instance ...'

    def terminate(self):
	self.self_stopped = False
	self.join()

    def connect_monitor(self):
	monitorClient = None
	while not self.connected_flag and not self.self_stopped:
    	    try:
		LOG.info( "proxy(%s) is connecting to host server:%s" % (self.proxy_private_ip, self.host_ip))
                monitorClient = httplib.HTTPConnection(self.host_ip, self.host_port, timeout=30)
                monitorClient.request('GET','?VMType=proxy'+'&PublicIP='+str(self.proxy_public_ip)+'&PrivateIP='+str(self.proxy_private_ip)+ '&Key=' + self.key  +'&CurTime='+str(time.time()))
                response = monitorClient.getresponse()
		self.connected_flag = True
            except Exception as e:
                LOG.error("%s" % e)
	    time.sleep(2)
	return monitorClient

    def send_notification_to_monitor(self, req_str):
        try:
            self.monitorClient.request('GET', req_str)
            response = self.monitorClient.getresponse()
	    if response.status == 200:
	        return True
	    return False
        except Exception, e:
            print e
	    return False

    def _pooling_instances(self):
	for inst in self.instance_metric.instance_list:
	    if not inst._is_booted_reported():
		#send notification to host
		LOG.debug( 'report one booted instance %s' % str(inst._get_info()))
		ret=self.send_notification_to_monitor(inst._new_boot_req())
		if ret:
		    inst._set_report_of_booted_instance()
	    elif inst._is_terminated_reported():
		#send notification to host
		LOG.debug('report one terminated instance %s' % str(inst._get_info()))
		ret=self.send_notification_to_monitor(inst._new_terminate_req())
		if ret:
		    inst._set_report_of_terminated_instance()

class ProxyServer(threading.Thread):
    def __init__(self):
	threading.Thread.__init__(self)
	self.instance_metric = ProvisionInstanceMetric()
        self.terminate_flag = 0

        self.metaConfigure = MetaConfigure()

	self.host_ip = self.metaConfigure._get_provision_host_ip()
	self.host_port = self.metaConfigure._get_provision_host_port()
	self.proxy_port = self.metaConfigure._get_proxy_port()
	self.report_online =self.metaConfigure._is_report_online()

	self.self_stopped = False
	self.httpd = make_server('', self.proxy_port, self.provision_proxy_app) 
	self.httpd.timeout = self.metaConfigure._get_http_timeout()

    def terminate(self):
	self.self_stopped = True
	self.join()

    def run(self):
	self.serve()

    def serve(self):
	LOG.info( "Serving on port %d..." % self.proxy_port)
	while not self.self_stopped:
	    self.httpd.handle_request()
	print "Stop proxy server..."
	LOG.info( "Stop proxy server...")
	#self.httpd.serve_forever()
  
    def provision_proxy_app(self, environ, start_response):  
	print 'one request coming'
        status = '200 OK' # HTTP Status  
        headers = [('Content-type', 'text/plain')] # HTTP Headers  
        start_response(status, headers) 

	instance_info = urlparse.parse_qs(environ['QUERY_STRING'])
	LOG.info( instance_info)
	print time.ctime()
	print time.ctime(float(instance_info['req'][0]))
	print "%s:boot time:%f" % (instance_info['hostname'], (float(time.time()) - float(instance_info['req'][0])))
	LOG.info( "%s:boot time:%f" % (instance_info['hostname'], (float(time.time()) - float(instance_info['req'][0]))))
	LOG.info( "arrvial:%f" % float(instance_info['req'][0]))
	LOG.info( "arrvial:%f" % float(time.time()))
	LOG.info('instance network time: %.2f' % (float(instance_info['booted'][0]) - float(instance_info['inited'][0])))
	LOG.info( "get ip:%f" % float(instance_info['alloc'][0]))
	#if 'hostname' in instance_info.keys() and 'ip' in instance_info.keys() and 'status' in instance_info.keys():
	if 'hostname' in instance_info.keys() and 'status' in instance_info.keys():
	    if instance_info['status'] == ['boot']:
		print 'instance booted post'
		instance = self.instance_metric._get_instance_by_name(instance_info['hostname'][0])
		if instance is None:
            	    instance = ProvisionInstanceData(instance_info['hostname'][0], instance_info['ip'][0], time.time(), float(instance_info['alloc'][0]))
	    	    self.instance_metric._append_instance(instance)
		    print 'add instance'
		    print '##########################3'
                return ["200 OK"]
	    elif instance_info['status'] == ['terminate']:
		print 'instance terminate post'
		instance = self.instance_metric._get_instance_by_name(instance_info['hostname'][0])
		if instance is None:
		    print "instance is not existed"
		else:
		    instance._set_timestamp_of_terminated_instance(time.time())
                return ["200 OK"]
	
	LOG.info("Error:(%s) do not include \'hostname\', \'ip\' and \'status[boot|terminate]\'" % environ['QUERY_STRING'])
	return ["Error:(%s) do not include \'hostname\', \'ip\' and \'status[boot|terminate]\'" % environ['QUERY_STRING']]


if __name__ == '__main__':
    MetaConfigure()._dump_configure()
    thread_pool = []
    thread_pool.append(ProxyPoolingInstance())
    thread_pool.append(ProxyServer())
    for th in thread_pool:
	th.start()

    def signal_handler(signal, frame):
        for th in thread_pool:
	    th.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
