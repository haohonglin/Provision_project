#!/usr/bin/python
import os, sys, argparse, string
from api import Openstack_API
import time
import random
import prettytable

DEBUG=False

DEFAULT_TIME_OUT = 60
DEFAULT_LIFE_TIME = 50
DEFAULT_CLIENT_NUMBER = 1
DEFAULT_BOOT_TYPE = 'single-image'
DEFAULT_MAX_INSTANCES = 1
DEFAULT_MIN_LIFETIME = 30
DEFAULT_MAX_LIFETIME = 50
DEFAULT_CLIENT_GENERATE = "increasing"
DEFAULT_CLIENT_INTERVAL = 5
DEFAULT_ITER_TIME = 2
DEFAULT_RANDOM_LIEFTIME = "False"
OPERATION_TIMEOUT = 30 
CHECK_STATUS_SLEEP = 1
CHECK_DELETE_SLEEP = 1
DEFAULT_MAX_RUNNING_INSTANCES = 1
DEFAULT_REPORT_INTERVAL = 5

POOL_SIZE = 999

parser = argparse.ArgumentParser(description='Provision Application.')
parser.add_argument('--debug', default=False, action='store_true', help="if true, load configure from args instead of meta.js")
parser.add_argument('--disable-host', default=False, action='store_true', help="if true, get the host of booted VM")
parser.add_argument('--cloud', required=True, choices=['aws','openstack'], help='One of AWS or OpenStack Cloud.')
parser.add_argument('--version', choices=['Folsom','Grizzly','Havana'], help='Version of OpenStack API: Folsom or Grizzly.')
parser.add_argument('--aws-access-key-id', help='aws access key id of your account')
parser.add_argument('--aws-secret-access-key', help='aws secret access key of your account')
parser.add_argument('--user-name', help='OS User Name of your openstack account')
parser.add_argument('--user-passwd', help='OS Password of your openstack account')
parser.add_argument('--user-tenant', help='OS Tenant of your openstack account')
parser.add_argument('--auth-url', help='authentication url of keystone')
parser.add_argument('--client-generate',choices=['increasing','fixed'], default=DEFAULT_CLIENT_GENERATE, help="using increasing way or static one-time creation way to generate the clients",)
parser.add_argument('--client-interval', type=float, default=DEFAULT_CLIENT_INTERVAL, help='the interval between launching clients',)
parser.add_argument('--client-number', type=int, default=DEFAULT_CLIENT_NUMBER, help='the number of provisioning clients')
parser.add_argument('--boot-type', choices=['single-image','volume','multi-image','hybrid'], default=DEFAULT_BOOT_TYPE, help='boot type, one of single-image, volume or multi-image, or in a mixed way')
parser.add_argument('--net-ids', nargs='*', help='network to boot from')
parser.add_argument('--net-proxy', nargs='*', help='proxy network to boot from')
parser.add_argument('--meta', nargs='*', help='meta that instance needs')
parser.add_argument('--file', nargs='*', help='meta that instance needs')
parser.add_argument('--image-ids', nargs='*', help='image ids to boot from')
parser.add_argument('--volume-ids', nargs='*', help='volume ids to boot from')
parser.add_argument('--flavor-ids', nargs='*', help='flavor ids for instance')
parser.add_argument('--image-names', nargs='*', help='image names to boot from')
parser.add_argument('--volume-names', nargs='*', help='volume names to boot from')
parser.add_argument('--flavor-names', nargs='*', help='flavor names for instance')
parser.add_argument('--runtime', type=float, dest="timeout", default=DEFAULT_TIME_OUT, help='timeout for the whole provision process.')
parser.add_argument('--lifetime', type=float, default=DEFAULT_LIFE_TIME, help='life time for an instance.')
parser.add_argument('--max-lifetime', type=float, default=DEFAULT_MAX_LIFETIME, help='maxmum life time for an instance.')
parser.add_argument('--min-lifetime', type=float, default=DEFAULT_MIN_LIFETIME, help='minmum life time for an instance.')
parser.add_argument('--iter-time', type=float, default=DEFAULT_ITER_TIME, help='time for an instance iteration.')
parser.add_argument('--random-lifetime', choices=["True","False"], default=DEFAULT_RANDOM_LIEFTIME, help='generate random lifetime for different instance.')
parser.add_argument('--clean', choices=["True","False"], default="True", help='clean all vms after reach run time.')
parser.add_argument('--report-interval', type=float, default=DEFAULT_REPORT_INTERVAL, help="the interval of reporting current runnng state...")
parser.add_argument('--max-instances', type=int, default=DEFAULT_MAX_INSTANCES, help='maxmum number of instances launced by one client.')
parser.add_argument('--max-running-instances', type=int, default=DEFAULT_MAX_RUNNING_INSTANCES, help='maxmum number of instances running at the same time.')

parser.add_argument('--host-addr', default='0.0.0.0:8675', help='address of provision test-end.')
parser.add_argument('--proxy-port', default='8821', help='port of provision proxy.')
parser.add_argument('--report-offline', default=False, action='store_true', help='if true, report vm boot time after everything has finished')
parser.add_argument('--polling-interval', type=int, default=1, help='the interval that proxy report to host')
parser.add_argument('--http-timeout', type=int, default=1, help='timeout when httdp handle one request')

def singleton(class_):
    instances = {}
    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]
    return getinstance

@singleton
class ProvisionProxyMonitorData:
    def __init__(self, host_port = 0, pub_ip = None, priv_ip = None, key = None):
        self.pub_ip = pub_ip
        self.priv_ip = priv_ip
        self.host_port = host_port
	self.key = key
        self.proxy_base_time = -1
        self.monitor_base_time = -1
        self.connected_with_proxy=False

    def _set_key(self, key):
	self.key = key

    def _set_pub_priv_ip(self, pub_ip, priv_ip):
        self.pub_ip = pub_ip
        self.priv_ip = priv_ip

    def _set_priv_ip(self, priv_ip):
        self.priv_ip = priv_ip

    def _set_pub_ip(self, pub_ip):
        self.pub_ip = pub_ip

    def _sync_time(self, proxy_base, monitor_base = -1):
        self.proxy_base_time = float(proxy_base)
        self.monitor_base_time = float(monitor_base)
        self.lease= float(proxy_base)- float(monitor_base)

    def _get_info(self):
        info={}
        info['pub']=str(self.pub_ip)
        info['priv']=str(self.priv_ip)
        info['proxytime']=str(self.proxy_base_time)
        info['monitor']=str(self.monitor_base_time)
        return info


@singleton
class MetaConfigure(object):
    def __init__(self):
	print "hello, it is Metaconfigure"
	self.metadict={}
        self.config = parser.parse_args(sys.argv[1:])
	self._load_configure()

    def _load_configure(self):
	    self.metadict['host_addr'] = self.config.host_addr
	    self.metadict['proxy_port'] = self.config.proxy_port
	    self.metadict['report_offline'] = self.config.report_offline
	    self.metadict['polling_interval'] = self.config.polling_interval
	    self.metadict['http_timeout'] = self.config.http_timeout

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

    def _dump_configure(self):
	print self.metadict

@singleton
class ProvisionInstanceMetric(object):
    def __init__(self):
	print "it is provision instance metric"
	self.instance_list = []
	self.instance_map = {}

    def _dump_instance_metric(self):
	instances_dict = {}
	for inst in self.instance_list:
	    instances_dict[inst.name] = inst._get_info()		
	return instance_dict

    def _pretty_metric(self):
        print "Total Launched Instances", len(self.instance_list)
        mtable = prettytable.PrettyTable(["Client","Instance","Host","BootTime","NetAccessTime","Lifetime","SurvivedTime","TerminateTime","StartTime","OPT Send Time"])
	for inst in self.instance_list:
	    inst_info = inst._get_info()
            rowarray=[]
            rowarray.append(inst_info.get("provision_name"))
            rowarray.append(inst_info.get("name"))
            rowarray.append(inst_info.get("host"))
            rowarray.append(inst_info.get("boot_time"))
            rowarray.append(inst_info.get("ip_lease"))
            rowarray.append(inst_info.get("lifetime"))
            rowarray.append(inst_info.get("survivedtime"))
            rowarray.append(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime( float(inst_info.get("terminate_time")))))
            rowarray.append(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime( float(inst_info.get("start_time")))))
            rowarray.append(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime( float(inst_info.get("opt_send_time")))))

            mtable.add_row(rowarray)
        return mtable

    def _wait_for_all_instances_get_host(self, cloud):
	servers = cloud.get_all_instance_host()
	get_all_host = True
    	for instance in self.instance_list:
	    try:
		if servers[instance.id]:
		    if servers[instance.id]['host'] != '':
			instance.host = servers[instance.id]['host']
		    print 'update instance host: %s' % instance.host

		    if servers[instance.id]['status'] == 'ERROR':
		        instance.status = "ERROR"
	    except Exception, e:
		print e

    	for instance in self.instance_list:
	    if not instance._get_instance_host():
		get_all_host = False
	    
	return get_all_host

    def _instance_GC(self, cloud):
	expired_instances_count = 0

    def _update_instances_info(self, cloud):
	fresh = False
	servers={}
    	for instance in self.instance_list:
	    if not instance._get_instance_host():
		if len(servers) == 0:
		    servers = cloud.get_all_instance_host()
		fresh = True
		break

	if fresh:
    	    for instance in self.instance_list:
		try:
		    if servers[instance.id]:
		        if servers[instance.id]['host'] != '':
			    instance.host = servers[instance.id]['host']
		        print 'update instance host: %s' % instance.host

		        if servers[instance.id]['status'] == 'ERROR':
		            instance.status = "ERROR"
		except Exception, e:
		    print e
	return fresh

    def _instance_GC(self, cloud):
	expired_instances_count = 0
    	for instance in self.instance_list:
	    if instance._is_deleting() or instance._is_deleted():
		expired_instances_count = expired_instances_count + 1
            elif instance._should_be_terminated():
		print 'delete one instance ...'

            	instance._delete(cloud)
		expired_instances_count = expired_instances_count + 1

	return expired_instances_count, len(self.instance_list)

    def _append_instance(self, instance):
	print "appending one instance"
	instance.append_into_metric = True
	self.instance_list.append(instance)
	print instance.name
	self.instance_map[instance.name] = instance

    def _update_instance(self, instance, status, arr_time = None, ip_lease = 0):
	print instance._get_info()
	if status == "RUNNING":
	    instance._set_instance_booted(arr_time, ip_lease)
	elif status == "DELETING":
	    instance._set_instance_terminating(arr_time)
	elif status == "DELETED":
	    if instance._is_running():
		instance._set_instance_terminated(arr_time)
	    elif instance._is_deleting():
		instance._set_instance_terminated(arr_time)
	    else:
	        pass

    def _get_instance_by_name(self, inst_name):
	if inst_name in self.instance_map.keys():
	    return self.instance_map[inst_name]
	return None

    def _collect_statistic(self):
	metric={}
	created_instances=len(self.instance_list)
	running_instances=0
	existing_instances=0
	building_instances=0
	terminated_instances=0
	terminating_instances=0
	average=0.0
	dev_num=0
	metric["AVERAGE"] = -1
	for inst in self.instance_list:
	    if inst._is_building():
		building_instances = building_instances + 1
		existing_instances = existing_instances + 1
	    elif inst._is_running():
		running_instances = running_instances + 1
		existing_instances = existing_instances + 1
	    elif inst._is_deleting():
		terminating_instances = terminating_instances + 1
		existing_instances = existing_instances + 1
	    elif inst._is_deleted():
		terminated_instances = terminated_instances + 1

	    if inst.boot_time > 0:
		dev_num = dev_num + 1
		average= average + inst.boot_time


	metric["CREATED"] = created_instances
	metric["BUILD"] = building_instances
	metric["RUNNING"] = running_instances
	metric["DELETING"] = terminating_instances
	metric["DELETED"] = terminated_instances
	metric["EXISTING"] = existing_instances
	if dev_num != 0:
	    metric["AVERAGE"] = average/dev_num

	return metric

@singleton
class ProvisionClientPool(object):
    def __init__(self):
	self.client_list = []

    def _append_client(self, client):
	self.client_list.append(client)
	

class ProvisionInstanceData:
    def __init__(self, instance, opt_send_time, lifetime, name, provision_name = '', ip = None, append_func = None):
	self.provision_name = provision_name
	self.name = name
	self.ip = ip
	self.id = instance.id
	
	'''WARNING: The instance returned by novaclient has a ref of novamanage which is http connecting with keystone. 
	   The workload should not ref the any http connection with keystone 
	   in case the keystone exceeds the open-max-files because the un-release of the http connections!'''

	if not instance:
	    self.status = "ERROR"
	    self.host = "xxxxxx"
	else:
	    self.status = "BUILDING"
	    self.instance_info = instance._info

	self.opt_send_time = opt_send_time
	self.lifetime = lifetime

	self.ip_lease = 0

	self.start_time = -1
	self.booted_timestamp = -1
	self.boot_time = -1

	self.terminating_flag = False
	self.terminate_start = -1
	self.terminated_timestamp = -1
	self.terminate_time = -1
	self.terminated_flag = 0
#	self.terminate_reported = 0
	self.survivedtime = -1
	self.delete_request = False
	    
	self.append_func = append_func 
	self.append_into_metric = False

	self.error_flag = False
	self.error_type = None
	self.host=None

    def _delete(self, cloud = None):
	cloud.terminate_instance(self.id)
	self._set_instance_terminated(time.time())

    def _get_host_no_emergency(self):
	if time.time() - float(self.opt_send_time) > float(self.lifetime)/2 :
	    return self._get_instance_host()

    def _get_instance_host(self):
	return self.host

    def _is_running(self):
        return self.status == "RUNNING"

    def _is_building(self):
	return self.status == "BUILDING"

    def _is_deleting(self):
        return self.status == "DELETING"

    def _is_deleted(self):
        return self.status == "DELETED"

    def _is_error(self):
        return self.status == "ERROR"

    def _append_into_metric(self):
	if not self.append_into_metric:
	    self.append_func(self)
	    self.append_into_metric = False

    def _get_info(self):
	info={} 
	info["name"] = self.name
	info["provision_name"] = self.provision_name
        info["host"]= self.host
        info["boot_time"]= round(self.boot_time, 2)
	info["ip_lease"]= round(self.ip_lease, 2)
        info["lifetime"]= round(self.lifetime, 2)
        info["survivedtime"]= round(self.survivedtime, 2)
        info["terminate_time"]= round(self.terminate_time, 2)
        info["start_time"]= self.booted_timestamp
        info["opt_send_time"]= self.opt_send_time
	return info

    def _get_name(self):
	return self.name

    def _get_ip(self):
	return self.ip

    def _get_booted_timestamp(self):
	return str(self.booted_timestamp)

    def _set_instance_booted(self, arr_time, ip_lease = 0):
	self.status = "RUNNING"
	self.start_time = time.time()
	self.booted_timestamp = time.time()
	self.boot_time = float(arr_time) - self.opt_send_time - ProvisionProxyMonitorData().lease
	self.ip_lease = float(ip_lease)
	print "boot time:%f, ip time:%.2f" %(self.boot_time, self.ip_lease)

    def _set_instance_terminating(self, arr_time):
	self.status = "DELETING"
	self.terminate_start = arr_time

    def _set_instance_terminated(self, arr_time):
	self.status = "DELETED"
	self.terminated_timestamp = float(arr_time)
	self.survivedtime = self.terminated_timestamp - self.booted_timestamp
	self.terminate_time = arr_time - self.terminate_start

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

    def _should_be_discarded(self, deadline):
	return self._is_error() or ( self._is_build() and (time.time() - self.opt_send_time > deadline) )

    def _should_be_terminated(self):
        cur_time=time.time()
        return self._is_running() and (cur_time - self.booted_timestamp > self.lifetime)

@singleton
class InstancePatitioner:
    def __init__(self):
	conf = MetaConfigure().config
	self.cloud_api = Openstack_API(conf)

	self.boot_type = conf.boot_type
        self.flavor_ids=[]
        self.image_ids=[]
        self.volume_ids=[]
        self.nec_ids=[]

        if hasattr(conf, 'image_ids'):
            self.image_ids = conf.image_ids or []
	    print self.image_ids

        if hasattr(conf, 'net_ids'):
            self.instance_net_ids = []
            self.proxy_net_ids = []
	    for net_id in conf.net_ids:
                self.instance_net_ids.append({"net-id":net_id})
                self.proxy_net_ids.append({"net-id":net_id})
	    print self.instance_net_ids

        if hasattr(conf, 'meta'):
            self.meta_list = conf.meta or {}

        if hasattr(conf, 'flavor_ids'):
            self.flavor_ids = conf.flavor_ids or []
	    print self.flavor_ids

        if hasattr(conf, 'volume_ids'):
            self.volume_ids = conf.volume_ids or []

	if hasattr(conf,"image_names") and conf.image_names:
            for iname in conf.image_names:
                self.image_ids.append(self.cloud_api.get_imageid_by_name(iname))

        if hasattr(conf,"flavor_names") and conf.flavor_names:
            for fname in conf.flavor_names:
                self.flavor_ids.append(self.cloud_api.get_flavorid_by_name(fname))
	self.meta_list={}
	self.proxy_ip='0.0.0.0'
	self.proxy_port=str(conf.proxy_port)
	self.host_addr=conf.host_addr

	file_or_string=open('vm_rc.local')
	self.vm_rc = file_or_string.read()
	self.vm_rc.encode('base64')
	file_or_string.close()

	file_or_string=open('ProvisionVM.py')
	self.vm_prov = file_or_string.read()
	self.vm_prov.encode('base64')
	file_or_string.close()

	file_or_string=open('proxy_rc.local')
	self.proxy_rc = file_or_string.read()
	self.proxy_rc.encode('base64')
	file_or_string.close()

	file_or_string=open('ProvisionProxy.py.tar.gz')
	self.proxy_prov = file_or_string.read()
	self.proxy_prov.encode('base64')
	file_or_string.close()

	self.proxy_addr="0.0.0.0:1111"
	print "image:%s;net: %s; %s ; meta: %s; flavor: %s; volumes_ids:%s" % (self.image_ids, self.instance_net_ids, self.proxy_net_ids, self.meta_list, self.flavor_ids, self.volume_ids)

	'''random liftime for vm instance'''
	self.lifetime = int(conf.lifetime)
	self.random_lifetime = conf.random_lifetime
	self.min_lifetime = conf.min_lifetime
	self.max_lifetime = conf.max_lifetime

    def set_proxy_ip(self, ip):
	self.proxy_ip=str(ip)
	self.proxy_addr=self.proxy_ip + ":" + self.proxy_port

    def get_vm_lifetime(self):
	lifetime = self.lifetime

	if self.random_lifetime == "True":
	    lifetime = random.randint(self.min_lifetime, self.max_lifetime)

	return lifetime

    def get_instance_parameter(self, name):
	files={}
	files['/etc/rc.local'] = self.vm_rc
	files['/home/ProvisionVM.py']=self.vm_prov

	parram_args={}
	parram_args['name']=name
	parram_args['files']=files
	parram_args['image_ids']=self.image_ids
	parram_args['net_ids']=self.instance_net_ids
	#parram_args['meta']=self.meta_list
	parram_args['meta']={}
	parram_args['meta']['hostname']=name
	parram_args['meta']['proxy_addr']=self.proxy_addr
	parram_args['meta']['req_time']=str(time.time())

	parram_args['flavor_ids']=self.flavor_ids
	parram_args['volume_ids']=self.volume_ids
	parram_args['boot_type']=self.boot_type
	return parram_args, self.get_vm_lifetime()

    def get_proxy_parameter(self, name):
	files={}
	files['/etc/rc.local'] = self.proxy_rc

	files['/home/ProvisionProxy.py.tar.gz'] = self.proxy_prov
	parram_args={}
	parram_args['name']=name
	parram_args['files']=files
	parram_args['image_ids']=self.image_ids
	parram_args['net_ids']=self.proxy_net_ids
	#parram_args['meta']=self.meta_list
	parram_args['meta']={}
	parram_args['meta']['host_addr']=self.host_addr
	parram_args['meta']['proxy_port']='8821'
	parram_args['meta']['report_online']='True'
	parram_args['meta']['key']=str(time.time())
	print parram_args['meta']['key']
	
	parram_args['flavor_ids']=self.flavor_ids
	parram_args['volume_ids']=self.volume_ids
	parram_args['boot_type']=self.boot_type
	return parram_args

    def create(self, name, image, flavor, meta=None, files=None,
               reservation_id=None, min_count=None,
               max_count=None, security_groups=None, userdata=None,
               key_name=None, availability_zone=None,
               block_device_mapping=None, block_device_mapping_v2=None,
               nics=None, scheduler_hints=None,
               config_drive=None, disk_config=None, **kwargs):
    	pass
