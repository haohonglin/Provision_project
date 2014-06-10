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
  
fh = logging.FileHandler('vm.log')  
fh.setLevel(logging.DEBUG)  
  
ch = logging.StreamHandler()  
ch.setLevel(logging.DEBUG)  
 
formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')  
fh.setFormatter(formatter)  
ch.setFormatter(formatter)  
 
LOG.addHandler(fh)  
LOG.addHandler(ch)  


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
	self._load_configure()

    def _load_configure(self):
        meta_file=open('/meta.js','r')
        try:
            metastr=meta_file.readline()
            self.metadict=eval(metastr)
            LOG.debug("%s" % self.metadict)
        except Exception, e:
            LOG.error('%s' % str(e))
        finally:
            if meta_file:
                meta_file.close()

    def _is_debug(self):
	return self.config.debug

    def _get_provision_proxy_ip(self):
	return self.metadict['proxy_addr'].split(':')[0]

    def _get_provision_proxy_port(self):
	return string.atoi(self.metadict['proxy_addr'].split(':')[1])

    def _get_hostname(self):
	return self.metadict['hostname']

    def _get_boot_req_time(self):
	return self.metadict['req_time']

    def _dump_configure(self):
	print self.metadict

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
		lease = time.time() - start
		LOG.info('%f' % lease)
		return ip, lease
	    except Exception, e:
		print e
		LOG.error( '%s, %f' %(e,(time.time() - start)))
		time.sleep(1)

class ProxyVMInstance:
    def __init__(self):
	self.metaConfigure = MetaConfigure()
	self.proxy_ip = self.metaConfigure._get_provision_proxy_ip()
	self.proxy_port = self.metaConfigure._get_provision_proxy_port()
	
	self.my_ip, self.get_ip_lease = Utils.get_ip_address('eth0')

	self.my_hostname=self.metaConfigure._get_hostname()
	self.proxy_base_time = -1
	self.host_base_time = -1

	self.boot_req_time=self.metaConfigure._get_boot_req_time()
	self.os_inited=str(time.time())
	self.connected_flag = False

    def ping_proxy(self):
	monitorClient = None
	while not self.connected_flag:
    	    try:
		LOG.info( "vm(%s) is connecting to proxy server:%s" % (self.my_ip, self.proxy_ip))
                proxyClient = httplib.HTTPConnection(self.proxy_ip, self.proxy_port, timeout=30)
                proxyClient.request('GET','?hostname='+self.my_hostname+'&ip='+str(self.my_ip)+'&inited='+self.os_inited+'&alloc='+str(self.get_ip_lease)+'&status=boot'+'&booted='+str(time.time())+ '&req='+self.boot_req_time)
                response = proxyClient.getresponse()
		if response.status == 200:
		    self.connected_flag = True
		LOG.debug( 'report one booted instance')
            except Exception as e:
                LOG.error("%s" % e)
	    time.sleep(1)

if __name__ == '__main__':
    MetaConfigure()._dump_configure()
    ProxyVMInstance().ping_proxy()
