#!/usr/bin/python
import threading
import argparse
import commands
import sys, signal
import time
import os
from eventlet import GreenPool
from eventlet.greenthread import sleep
import Queue


from api import Openstack_API
from neutron_provision import neutron_provision
import common
from common import ProvisionInstanceData
from common import ProvisionClientPool
from common import ProvisionInstanceMetric
from common import MetaConfigure
from common import InstancePatitioner
from common import ProvisionProxyMonitorData
from ProvisionMonitor import ProvisionMonitor


def get_cloud_api(config):
	'''get an aws connection or an openstack connection...'''
	if config.cloud == 'aws':
		print 'Creating an Aws-Ec2 connection.'
		if config.aws_access_key_id == None or config.aws_secret_access_key == None:
			print 'Input Invalid, aws-access-key-id and aws-secret-key-id is necessary for AWS cloud.'
			return
		return AWS_API(config) 
		 
	elif config.cloud == 'openstack':
		if not (config.user_name and config.user_passwd and config.user_tenant and config.auth_url):
			print 'Input Invalid, user-name, user-password, user-tenant and auth-url is necessary for OpenStack cloud.'
			return
		return Openstack_API(config)

class InstanceGC(threading.Thread):
	''' The class is a thread to monitor all the provisions '''
	def __init__(self, config):
		threading.Thread.__init__(self)
		self.config = config
		self.instanceMetric=ProvisionInstanceMetric()
		self.cloud = get_cloud_api(self.config)
		self.running=True
		self.waiting_for_all_expired = False

	def join(self):
	    self.waiting_for_all_expired = True
	    threading.Thread.join(self)

	def terminateGC(self):
		self.running=False
	        self.waiting_for_all_expired = True
		self.join()

	def run(self):
		while(self.running):
			if self.GC():
			    break
			sleep(1)
	
	def GC(self):
		exp, total = self.instanceMetric._instance_GC(self.cloud)
		print 'deleted %d instances from total %d instances' % (exp, total)
		if exp == total and self.waiting_for_all_expired:
			return True
		return False

class InstanceManager(threading.Thread):
	''' The class is a thread to monitor all the provisions '''
	def __init__(self, config):
		threading.Thread.__init__(self)
		self.config = config
		self.instanceMetric=ProvisionInstanceMetric()
		self.cloud = get_cloud_api(self.config)
		self.running=True
		self.instance_queue = Queue.Queue()
		self.instances_last_update_time = time.time()
		self.instances_next_update_time = time.time()
		self.instances_update_flag = True
		#self.get_host = not self.config.disable_host

	def get_instance_queue(self):
		return self.instance_queue

	def terminateIM(self):
		self.running=False
		self.join()

	def run(self):
		while(self.running):
		    self.collect_instance()
		    if not self.config.disable_host:
	    	        self._update_instances_info()
		    sleep(1)
		self.collect_instance()
		self._wait_for_all_instances_get_host()
	
	def collect_instance(self):
	    while not self.instance_queue.empty():
		instance = self.instance_queue.get()
		self.instanceMetric._append_instance(instance)	

	def _wait_for_all_instances_get_host(self):
	    timeout = 120
	    while not self.instanceMetric._wait_for_all_instances_get_host(self.cloud) and timeout > 0:
		time.sleep(20)
		timeout = timeout - 20

	def _update_instances_info(self):
	    if self.instances_update_flag and (time.time() - self.instances_next_update_time > 0):
	        if self.instanceMetric._update_instances_info(self.cloud):
		    self.instances_next_update_time = time.time() + 2*self.config.min_lifetime/3
		    self.instances_last_update_time = time.time()
		elif time.time() - self.instances_last_update_time > 5*self.config.client_interval:
		    self.instances_update_flag = False
		    

class ClientGC(threading.Thread):
	''' The class is a thread to monitor all the provisions '''
	def __init__(self, config):
		threading.Thread.__init__(self)
		self.threadQueue = Queue.Queue()
		self.running=False
		self.config=config

	def get_client_queue(self):
		return self.threadQueue

	def startGC(self):
		self.running=True
		self.start()

	def joinGC(self):
		self.running=False
		#self.clean_all()
		self.join()

	def run(self):
	    while(self.running):
		self.gc()
		sleep(10)
	    self.gc()

        def gc(self):
                while not self.threadQueue.empty():
		    th = self.threadQueue.get()
                    if th.thread_status == "FINISHED" and not th.has_joined:
                        th.has_joined = True
                        th.join()
			del th
		    else:
			self.threadQueue.put(th)

class ProvisionReporter(threading.Thread):
	''' The class is a thread to report the state of provision '''
	def __init__(self, config):
		threading.Thread.__init__(self)
		self.config = config
		self.timeout = self.config.timeout
		self.is_reporting = False
		self.report_interval = self.config.report_interval
		self.instanceMetric=ProvisionInstanceMetric()
	
	def run(self):
		self.collect_statistic()

	def start_reporter(self):
		self.start()

	def terminate_reporter(self):
		self.is_reporting=False
		self.join()

	def collect_statistic(self):
		timeout = self.timeout
		start_time=time.time()
		self.is_reporting=True
		#while(timeout > 0):
		while(self.is_reporting):
			sleep(self.report_interval)
			print self.instanceMetric._collect_statistic()
		
class ProvisionWorkload(object):
	def __init__(self, config):
		self.config=config
		self.client_number = self.config.client_number
		self.timeout = self.config.timeout
		self.report_interval = self.config.report_interval
		self.instance_number = 0
		self.metrics = None
		self.is_reporting=False
		self.client_list = ProvisionClientPool()

	def _prepare_monitor_proxy(self):
		monitor_thread = ProvisionMonitor()
		monitor_thread.start()

		cloud_api=get_cloud_api(self.config)
		args=InstancePatitioner().get_proxy_parameter('provision_proxy')
                flavor_ids=args['flavor_ids']
                image_ids=args['image_ids']
                volume_ids=args['volume_ids']
                nec_ids=args['net_ids']
                meta_list=args['meta']
                files=args['files']
                name=args['name']
		
		ProvisionProxyMonitorData()._set_key(args['meta']['key'])	
		start_time=time.time()
                if image_ids and len(image_ids) > 0 and flavor_ids and len(flavor_ids) > 0:
		    proxy_instance = cloud_api.run_instance(name, image_ids[0], flavor_ids[0], nec_ids, meta_list, files)

		if not proxy_instance:
		    monitor_thread.terminate_monitor()
		    return None, None
		while not cloud_api.is_instance_running(proxy_instance.id):
		    time.sleep(5)
		    print 'building proxy instance: %f s' % (time.time() - start_time)

		build_time=time.time()-float(start_time)

		network=neutron_provision(self.config)
		ip_info=network.associate_proxy_ip(proxy_instance.id)
		print "proxy self.proxy_instance.id-- public ip: %s, private ip: %s" % (ip_info['floatingip']['fixed_ip_address'], ip_info['floatingip']['floating_ip_address'])
		InstancePatitioner().set_proxy_ip(ip_info['floatingip']['fixed_ip_address'])
		ProvisionProxyMonitorData()._set_pub_priv_ip(ip_info['floatingip']['floating_ip_address'], ip_info['floatingip']['fixed_ip_address'])
		while not ProvisionProxyMonitorData().connected_with_proxy:
		    print '%f waiting for proxy http connect'% (time.time() - start_time)
		    sleep(5)
		print "proxy VM build time %f s, boot time:%f s" % (build_time, (time.time() - start_time))
		print  ProvisionProxyMonitorData()._get_info()
		return monitor_thread,proxy_instance
		

	def start_workload(self):
		''' a serial of concurrency client behaviors
		'''
    		monitor, proxy_instance = self._prepare_monitor_proxy()
		if not proxy_instance:
		    print 'error while creating proxy instance...please check it'
		    return

		reporter = ProvisionReporter(self.config)
		reporter.start_reporter()

		instanceGC = InstanceGC(self.config)
		instanceGC.start()

		clientGC = ClientGC(self.config)
		clientGC.startGC()
		client_queue = clientGC.get_client_queue()

		instanceManager = InstanceManager(self.config)
		instanceManager.start()
		instance_queue = instanceManager.get_instance_queue()

		begin_time=time.time()
		if self.config.client_generate == "fixed":
			#for i in range(self.config.client_number):
			#	pth = self.new_provision(client_iter, timeout)
			#	pth.start()
			#	thread_list.append(gth)
			print 'not implement yet'
			pass
		else:
			timeout = self.timeout
			client_iter = 0
			while (timeout > 0 and client_iter < self.config.client_number):
				pth = self.new_provision(client_iter, timeout, instance_queue)
				pth.start()
				client_queue.put(pth)
				#thread_list.append(pth)
				client_iter += 1
				sleep(self.config.client_interval)
				timeout -= self.config.client_interval	
		
		clientGC.joinGC()
		print "provision threads have terminated"		

		instanceManager.terminateIM()
		print "instance mannage thread has terminate"
		
		instanceGC.join()
		print "instance GC thread has terminate"

		reporter.terminate_reporter()
		print "reporter thread has terminated"
		monitor.terminate_monitor()
		print "monitor thread has terminated"

		total_time = time.time() - begin_time
		print "total time: %d" % total_time

		mtable=ProvisionInstanceMetric()._pretty_metric()
		print mtable

		filename='seq'+str(self.config.client_interval)+'_num'+str(self.config.client_number)+'_life'+str(self.config.min_lifetime)+':'+str(self.config.max_lifetime)+'_provision.res'
		with open(filename, 'w') as f:
		    f.write(str(mtable))
		    f.close()

		ip = ProvisionProxyMonitorData()._get_info()['pub']
		proxy_instance.remove_floating_ip(ip)
		proxy_instance.delete()

			
	def new_provision(self, iteration, timeout, instance_queue):
		''' single client behavior, including multiple operations...
		'''

		if common.DEBUG:
			print "create a client ", "client_"+str(iteration)
			sleep(timeout)
			print "client_"+str(iteration)+" ends"
			return "client_"+str(iteration), (0, {})

		client = self._create_client("client_"+str(iteration), instance_queue, timeout)
		try:
			return client
		except Exception as e:
			print "Error: %s."%str(e)
			if self.config.clean == "True":
				client.clean_instances()
	
	def _create_client(self, name, instance_queue, timeout):	
		''' create  a client to do provision...'''
		client = ProvisionClient(self.config, timeout, instance_queue, name)
		#client = ProvisionClient(self.cloud_api, self.config, timeout,name )
		return client

class ProvisionClient(threading.Thread):
	''' The class to do provision...'''
	def __init__(self, config, timeout, instance_queue, name=""):
		#print "Provision Client init."
		threading.Thread.__init__(self)
		self.name = name
		self.instance_queue = instance_queue
		#self.cloudapi = cloudapi
		self.config = config
		self.boot_type = config.boot_type
		self.instance_list = []
		self.max_instance_number=self.config.max_instances
		self.timeout = timeout
		self.counter = 0
		self.inst_metrics_dict = {}
		self.running_instances = 0
		self.is_terminating_instances=0
		self.has_terminated_instances = 0
		self.thread_status = "READY"
		self.has_joined=False ##used for thread GC
	
	def print_client_instances(self):
		print "Client Name: %s has launched %d instances."%(self.name, len(self.instance_list))
		for inst in self.instance_list:
			print "Instance %s : launch time: %s lifetime:%s survived time:%s"%(inst.name, str(inst.boot_time), str(inst.lifetime), str(inst.survivedtime))	
		
	def get_client_metrics(self):
		metrics_dict={}
		for inst in self.instance_list:
			metrics_dict[inst.name]=inst._get_info()
		return metrics_dict
	
	def run(self):
		self.thread_status = "RUNNING"
		self.produce_operations(self.max_instance_number)
			
	def produce_operations(self, instance_number):
		'''
		main method to emulate the behavior of a client: 
			create instances one by one
			& delete overtime instances...
		'''
		print "client producing workload timeout %s"%self.timeout
		timeout = float(self.timeout)
		cloud_api = get_cloud_api(self.config)
		while timeout > 0 and self.counter < self.max_instance_number:
			has_created_new_instance = False
			starttime = time.time()

			if self.counter < instance_number and self.running_instances < self.config.max_running_instances:
				inst_name = self.name+"_instance_"+str(self.counter)
				instance, opt_time, lifetime = self._boot_instances(cloud_api, inst_name)
				
				'''remove the code to calcuate the error rate of an instance'''
				#if not instance:
				#	break

				instance_data = ProvisionInstanceData(instance, opt_time, lifetime, inst_name, self.name)
				self.instance_list.append(instance_data)
				self.instance_queue.put(instance_data)
				self.counter += 1

			#self.ping_instances()
			#self.terminate_expired_instance()
			sleep(self.config.iter_time)
			timeout = timeout - (time.time()-starttime)	
		self.thread_status = "FINISHED"
		print "one provision has finished the job"
		return self.counter, self.get_client_metrics()

	def clean_instances(self):
		instance_ids = [instance.id for instance in self.instance_list if not instance.delete_request ]
		self._delete_instances(instance_ids)
		
	def _delete_instances(self,cloud_api, instance_ids):
		for inst_id in instance_ids:
			if (self.cloud_api.is_instance_need_delete(inst_id)):
				self._terminate_instance(inst_id)
	
	def _boot_instances(self, cloud_api, name_prefix):
		args, lifetime = InstancePatitioner().get_instance_parameter(name_prefix)
		flavor_ids=args['flavor_ids']
		image_ids=args['image_ids']
		volume_ids=args['volume_ids']
		nec_ids=args['net_ids']
		meta_list=args['meta']
		meta_list['hostname']=name_prefix
		files=args['files']
		name=args['name']

		if self.boot_type == 'single-image' and image_ids and len(image_ids) > 0 \
			and flavor_ids and len(flavor_ids) > 0:
			instance, opt_time = self._boot_from_single_image(cloud_api, name, image_ids[0], flavor_ids[0], nec_ids, meta_list, files)
			return instance, opt_time, lifetime
		elif self.boot_type == 'multi-image' and image_ids and len(image_ids) > 1 \
			and flavor_ids and len(flavor_ids) > 0: 
			instance, opt_time = self._boot_from_multi_image(cloud_api, name, image_ids, flavor_ids, nec_ids)
			return instance, opt_time, lifetime
		elif self.boot_type == 'volume' and volume_ids and len(volume_ids) > 0 \
			and flavor_ids and len(flavor_ids) > 0:  
			instance, opt_time = self._boot_from_volume(cloud_api, name, volume_ids, flavor_ids, nec_ids)
			return instance, opt_time, lifetime
		else:
			print "wrong parameter..."
			return None, None, None

	def _update_instance_status(self, ret):
		if (self.thread_status == "FINISHED") and (self.counter == self.has_terminated_instances) :
			return True

		for instance in self.instance_list:
			if instance.status == "BUILD" :
				query="cat " + ret + " | grep " + str(instance.instance.id) + " | awk -F\"|\" '{print $4}'"
				status, output = commands.getstatusoutput(query)
				isActive= output.strip()
				if( isActive == "ACTIVE"):
					instance.boot_time=time.time()-instance.opt_send_time 
					instance.status="ACTIVE"
					instance.start_time=time.time()
					self.running_instances += 1
					print "%s: the instance(%s) is active, boot_time:%d" % (self.name, instance.instance.id, instance.boot_time)
			elif instance.status == "DELETING": # and (not self.cloudapi.is_instance_exist(instance.instance.id)):
				query="cat " + ret + " | grep " + str(instance.instance.id) + " | awk -F\"|\" '{print $4}'"
				status, output = commands.getstatusoutput(query)
				isActive=output.strip()
				if( isActive != "ACTIVE"):
					instance.terminate_time=time.time() - instance.terminate_start
					instance.status = "DELETED"
					instance.delete_request = True
					self.running_instances -= 1
					self.is_terminating_instances -= 1
					self.has_terminated_instances += 1
			elif instance.status == "DELETE_ERROR": # and (not self.cloudapi.is_instance_exist(instance.instance.id)):
				instance.status = "DELETED"
				instance.delete_request = True
				self.running_instances -= 1
				self.has_terminated_instances += 1
		return False	
	
	def _boot_from_single_image(self, cloud_api, name, image_id, flavor_id, nec_ids, meta_list, files):	
		opt_time = time.time()
		instance = cloud_api.run_instance(name, image_id, flavor_id, nec_ids, meta_list, files) 
		if not instance:
			return None, opt_time
		return instance, opt_time

	def _boot_from_multi_image(self,cloud_api, image_ids, flavor_ids, nec_ids):
		print "Not Implemented!" 

	def _boot_from_volume(self, cloud_api, volume_ids, flavor_ids, nec_ids):
		print "Not Implemented!"  

	'''not used in workload'''
	def _terminate_instance_by_id(self, cloud_api, instance_id):
		for instance in self.instance_list:		
			if (instance.id == instance_id) and (not instance.delete_request):
				break
		
		if instance._is_running():
			if cloud_api.terminate_instance(instance_id):
				ProvisionInstanceMetric()._update_instance(instance, "DELETING", time.time())
				self.is_terminating_instances +=1
			else:
				ProvisionInstanceMetric()._update_instance(instance, "DELETED", time.time())
				self.is_terminating_instances +=1
			print "#######one instance is deleting#########"
		return True

	def _terminate_instance(self, cloud_api, instance):
		if instance._is_running():
			if cloud_api.terminate_instance(instance.id):
				ProvisionInstanceMetric()._update_instance(instance, "DELETING", time.time())
				self.is_terminating_instances +=1
			else:
				ProvisionInstanceMetric()._update_instance(instance, "DELETED", time.time())
				self.is_terminating_instances +=1
			print "#######one instance is deleting#########"
		return True

	def terminate_expired_instance(self, cloud_api):
		currenttime = time.time()
		for instance in self.instance_list:
		    if instance._should_be_terminated():
			if not self._terminate_instance(cloud_api, instance):
			    print "instance.id cannot delete normally."
		

#config=parser.parse_args(sys.argv[1:])
if __name__ == '__main__':
    MetaConfigure()._dump_configure()
    thread_pool = []

    workload = ProvisionWorkload(MetaConfigure().config)
    workload.start_workload()

#    def signal_handler(signal, frame):
#        for th in thread_pool:
#            th.terminate()
#        sys.exit(0)

#    signal.signal(signal.SIGINT, signal_handler)
#    signal.pause()


