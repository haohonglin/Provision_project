#!/usr/bin/python
import threading
import argparse
import commands
import sys
import time
from random import randint
import os
from eventlet import GreenPool
from eventlet.greenthread import sleep

import prettytable
from api import Openstack_API



class Metrics(object):
	def __init__(self):
		self.client_dict = []
		self.instance_counter = 0

	def printout(self):
		print
		print "Total Launched Instances", self.instance_counter
		mtable = prettytable.PrettyTable(["Client","Instance","BootTime","Lifetime","SurvivedTime","TerminateTime","StartTime","OPT Send Time"])
		for client in self.client_dict:
			if isinstance(client,dict):
				for key in client:
					if isinstance(client[key], dict):
						rowarray=[key]
						for instancekey in client[key]:
							rowarray.append(instancekey)
							rowarray.append(client[key][instancekey].get("boot_time"))
							rowarray.append(client[key][instancekey].get("lifetime"))
							rowarray.append(client[key][instancekey].get("survivedtime"))
							rowarray.append(client[key][instancekey].get("terminate_time"))
							rowarray.append(client[key][instancekey].get("start_time"))
							rowarray.append(client[key][instancekey].get("opt_send_time"))

							mtable.add_row(rowarray)
		print mtable


class ThreadGC(threading.Thread):
	''' The class is a thread to monitor all the provisions '''
	def __init__(self, config, client_list):
		threading.Thread.__init__(self)
		self.threadPool=client_list
		self.running=False
		self.config=config

	def startGC(self):
		self.running=True
		self.start()

	def joinGC(self):
		self.running=False
		self.clean_all()
		self.join()

	def run(self):
		while(self.running):
			self.gc()
			sleep(10)

	def gc(self):
		for th in self.threadPool:
			if th.thread_status == "FINISHED" and not th.has_joined:
				th.has_joined = True
				th.join()
				print "GC one thread"

	def clean_all(self):
		for th in self.threadPool:
				th.has_joined = True
				th.join()
				th._Thread__delete()

class ProvisionReporter(threading.Thread):
	''' The class is a thread to monitor all the provisions '''
	def __init__(self, config, client_list):
		threading.Thread.__init__(self)
		self.config = config
		self.client_list = client_list
		self.timeout = self.config.timeout
		self.is_reporting = False
		self.report_interval = self.config.report_interval
	
	def run(self):
		self.collect_statistic()

	def start_reporter(self):
		self.start()

	def terminate_reporter(self):
		self.join_reporter()

	def join_reporter(self):
		self.is_reporting=False
		self.join()

	def collect_statistic(self):
		timeout = self.timeout
		start_time=time.time()
		self.is_reporting=True
		#while(timeout > 0):
		while(self.is_reporting):
			sleep(self.report_interval)
			boot_counter, running_counter, terminate_counter = 0, 0, 0
			for client in self.client_list:
				boot_counter += client.has_boot
				running_counter += client.running_instances
				terminate_counter += client.has_terminated_instances
			cur_time=time.time() - start_time
			print
			print "%d: created instance %d"%(cur_time,boot_counter)
			print "%d: running instance %d"%(cur_time,running_counter)
			print "%d: existing instance %d"%(cur_time,boot_counter - terminate_counter)
			print "%d: building instance %d"%(cur_time,boot_counter - terminate_counter - running_counter)
			print "%d: terminate instance %d"%( cur_time, terminate_counter)
			print
			timeout -= self.report_interval
		
class ProvisionFactory(object):
	def __init__(self, config):
		self.config=config
		self.client_number = self.config.client_number
		self.timeout = self.config.timeout
		self.report_interval = self.config.report_interval
		self.instance_number = 0
		self.metrics = None
		self.is_reporting=False
		self.client_list = []

	def get_cloud_api(self):
		'''get an aws connection or an openstack connection...'''
		if self.config.cloud == 'aws':
			print 'Creating an Aws-Ec2 connection.'
			if self.config.aws_access_key_id == None or self.config.aws_secret_access_key == None:
				print 'Input Invalid, aws-access-key-id and aws-secret-key-id is necessary for AWS cloud.'
				return
			return AWS_API(self.config) 
			 
		elif self.config.cloud == 'openstack':
			if not (self.config.user_name and self.config.user_passwd and self.config.user_tenant and self.config.auth_url):
				print 'Input Invalid, user-name, user-password, user-tenant and auth-url is necessary for OpenStack cloud.'
				return
			return Openstack_API(self.config)
	
	def run_provision_conc(self):
		''' a serial of concurrency client behaviors
		'''
		reporter = ProvisionReporter(self.config, self.client_list)
		reporter.start_reporter()

		threadGC = ThreadGC(self.config, self.client_list)
		threadGC.startGC()

		monitor_thread = ProvisionMonitor(self.get_cloud_api(),self.client_list)
		monitor_thread.start_monitor()
		thread_list=[]
		begin_time=time.time()
		if self.config.client_generate == "fixed":
			for i in range(self.config.client_number):
				pth = self.run_provision(client_iter, timeout)
				pth.start()
				thread_list.append(gth)

		else:
			timeout = self.timeout
			client_iter = 0
			while (timeout > 0 and len(self.client_list) < self.config.client_number):
				pth = self.run_provision(client_iter, timeout)
				pth.start()
				thread_list.append(pth)

				client_iter += 1
				sleep(self.config.client_interval)
				timeout -= self.config.client_interval	

		
		metrics = Metrics()
		
		threadGC.joinGC()
		for pth in thread_list:
			pth.join()
		print "provision threads have terminated"		

		monitor_thread.join_monitor()
		print "monitor threads has terminated" 

		reporter.join_reporter()
		print "collecting thread has terminated"

		total_time = time.time() - begin_time
		print "total time: %d" % total_time
		for provision in self.client_list:
			name = provision.name
			re = provision.get_client_metrics()
			metrics.instance_counter += provision.counter
			metrics.client_dict.append({name: re})
		metrics.printout()
			
	def run_provision(self, iteration, timeout):
		''' single client behavior, including multiple operations...
		'''

		if DEBUG:
			print "create a client ", "client_"+str(iteration)
			sleep(timeout)
			print "client_"+str(iteration)+" ends"
			return "client_"+str(iteration), (0, {})

		client = self._create_client("client_"+str(iteration), timeout)
		try:
			#return client.name, client.produce_operations(self.config.max_instances)
			client.set_run_parameter(self.config.max_instances)
			return client
		except Exception as e:
			print "Error: %s."%str(e)
			if self.config.clean == "True":
				client.clean_instances()
		#client._test_cloudapi()
		#client._delete_all_instance()
	
	def _create_client(self, name, timeout):	
		''' create  a client to do provision...'''
		client = ProvisionClient(self.get_cloud_api(), self.config, timeout,name )
		self.client_list.append(client)
		return client

class ClientInstance(object):
	''' The class for an instance created by a client...'''
	def __init__(self, instance, opt_send_time, lifetime, name):
		self.id = instance.id
		self.name = name
		self.instance = instance
		self.opt_send_time = opt_send_time
		self.lifetime = lifetime
		self.start_time = -1
		self.status="BUILD"
		self.boot_time = -1
		self.terminate_start=-1
		self.terminate_time = -1
		self.survivedtime = -1
		self.delete_request = False
		self.ping_success = False

class ProvisionMonitor(threading.Thread):
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
		print "#######################"
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
	def _list_instance(self):
		formatters={}
		field_titles=[]
		id_col = 'ID'
		servers=self.cloud_api.list_instance()
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
#			self._list_instance()
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
		
#class ProvisionClient(object):
class ProvisionClient(threading.Thread):
	''' The class to do provision...'''
	def __init__(self, cloudapi, conf, timeout,name=""):
		#print "Provision Client init."
		threading.Thread.__init__(self)
		self.name = name
		self.cloudapi = cloudapi
		self.conf = conf
		self.boot_type = conf.boot_type
		self.instance_list = []
		self.max_instance_number=1
		self.timeout = timeout
		self.counter = 0
		self.inst_metrics_dict = {}
		self.running_instances = 0
		self.has_boot = 0
		self.is_terminating_instances=0
		self.has_terminated_instances = 0
		self.thread_status = "READY"
		self.has_joined=False ##used for thread GC
		
		if hasattr(conf, 'image_ids'):
			self.image_ids = conf.image_ids
		else:
			self.image_ids = None
		if hasattr(conf, 'flavor_ids'):
			self.flavor_ids = conf.flavor_ids
		else:
			self.flavor_ids = None
		if hasattr(conf, 'volumes_ids'):
			self.volume_ids = conf.volumes_ids
		else:
			self.volume_ids = None
	
	def print_client_instances(self):
		print "Client Name: %s has launched %d instances."%(self.name, len(self.instance_list))
		for inst in self.instance_list:
			print "Instance %s : launch time: %s lifetime:%s survived time:%s"%(inst.name, str(inst.boot_time), str(inst.lifetime), str(inst.survivedtime))	
		
	def get_client_metrics(self):
		metrics_dict={}
		for inst in self.instance_list:
			metrics_dict[inst.name]={}
			metrics_dict[inst.name]["boot_time"]= round(inst.boot_time, 2)
			metrics_dict[inst.name]["lifetime"]= round(inst.lifetime, 2)
			metrics_dict[inst.name]["survivedtime"]= round(inst.survivedtime, 2)
			metrics_dict[inst.name]["terminate_time"]= round(inst.terminate_time, 2)
			metrics_dict[inst.name]["start_time"]= inst.start_time
			metrics_dict[inst.name]["opt_send_time"]= inst.opt_send_time
		return metrics_dict
	
	def set_run_parameter(self, instance_number):
		self.max_instance_number=instance_number

	def run(self):
		self.thread_status = "RUNNING"
		self.produce_operations(self.max_instance_number)
			
	def produce_operations(self, instance_number):
		'''
		main method to emulate the behavior of a client: 
			create instances one by one
			& delete overtime instances...
		'''
		#return self.fake_produce_operations()
		
		print "client producing workload timeout %s"%self.timeout
		timeout = float(self.timeout)
		lifetime = int(self.conf.lifetime)
		has_created_new_instance = True
		while (has_created_new_instance and timeout > 0) or (self.has_terminated_instances + self.is_terminating_instances < self.counter):
		#while timeout > 0 or (self.has_terminated_instances + self.is_terminating_instances < self.counter):
			has_created_new_instance = False
			starttime = time.time()

			if self.counter < instance_number and self.running_instances < self.conf.max_running_instances:
				inst_name = self.name+"_instance_"+str(self.counter)
				instance, opt_time = self._boot_instances(inst_name)
				if not instance:
					break
				if self.conf.random_lifetime == "True":
					lifetime = randint(self.conf.min_lifetime, self.conf.max_lifetime)
				self.instance_list.append(ClientInstance(instance,opt_time, lifetime, inst_name))
				self.counter += 1
				has_created_new_instance = True

			self.ping_instances()
			self.terminate_expired_instance()
			sleep(self.conf.iter_time)
			timeout = timeout - (time.time()-starttime)	
		self.thread_status = "FINISHED"
		print "one provision has finished the job"
		return self.counter, self.get_client_metrics()
	
	def ping_instances(self):	
		for instance in self.instance_list:
			if instance.status == "ACTIVE" and not instance.ping_success:
				'''starting pinging'''

	def clean_instances(self):
		#print 'clean instances...remaining %d instances.'%len(self.instance_list)
		instance_ids = [instance.id for instance in self.instance_list if not instance.delete_request ]
		self._delete_instances(instance_ids)
		
	def _delete_instances(self,instance_ids):
		#print 'deleting instances', instance_ids
		for inst_id in instance_ids:
			if (self.cloudapi.is_instance_need_delete(inst_id)):
				#print 'deleting instance %s'%inst_id
				self._terminate_instance(inst_id)
	
	def _boot_instances(self, name_prefix):
		flavor_ids=[]
		image_ids=[]
		volume_ids=[]
		if hasattr(self.conf,"image_ids") and self.conf.image_ids:
			image_ids=self.conf.image_ids
		if hasattr(self.conf,"flavor_ids") and self.conf.flavor_ids:
			flavor_ids=self.conf.flavor_ids
		if hasattr(self.conf,"volume_ids") and self.conf.volume_ids:
			volume_ids=self.conf.volume_ids
		if hasattr(self.conf,"image_names") and self.conf.image_names:
			for iname in self.conf.image_names:
				image_ids.append(self.cloudapi.get_imageid_by_name(iname))
		if hasattr(self.conf,"flavor_names") and self.conf.flavor_names:
			for fname in self.conf.flavor_names:
				flavor_ids.append(self.cloudapi.get_flavorid_by_name(fname))		
		
		if self.boot_type == 'single-image' and image_ids and len(image_ids) > 0 \
			and flavor_ids and len(flavor_ids) > 0:
			return self._boot_from_single_image(name_prefix, image_ids[0], flavor_ids[0])
		elif self.boot_type == 'multi-image' and image_ids and len(image_ids) > 1 \
			and flavor_ids and len(flavor_ids) > 0: 
			return self._boot_from_multi_image(name_prefix, image_ids, flavor_ids)
		elif self.boot_type == 'volume' and volume_ids and len(volume_ids) > 0 \
			and flavor_ids and len(flavor_ids) > 0:  
			return self._boot_from_volume(name_prefix, volume_ids, flavor_ids)
		else:
			print "wrong parameter..."

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
	
	def _boot_from_single_image(self, name, image_id, flavor_id):	
		start_time = time.time()
		instance = self.cloudapi.run_instance(name, image_id, flavor_id) 
		self.has_boot += 1
		if not instance:
			return None, None
		return instance, start_time

	def _terminate_instance(self, instance_id):
		currenttime = time.time()
		for instance in self.instance_list:		
			if (instance.id == instance_id) and (not instance.delete_request):
				instance.survivedtime =  currenttime - instance.start_time
				break
		
		if instance.status == "ACTIVE":
			if self.cloudapi.terminate_instance(instance_id):
				instance.status="DELETING"
				instance.terminate_start=time.time()
				self.is_terminating_instances +=1
			else:
				instance.status="DELETE_ERROR"
				print "*****delete error****"
			print "#######one instance is deleting#########"

		return True

	def _boot_from_multi_image(self, image_ids, flavor_ids):
		print "Not Implemented!" 

	def _boot_from_volume(self, volume_ids, flavor_ids):
		print "Not Implemented!"  

	def terminate_expired_instance(self):
		currenttime = time.time()
		for instance in self.instance_list:
			if currenttime - instance.start_time < instance.lifetime or instance.delete_request:
				pass#print "instance %s survives %d - %d, lifetime %d"%(instance.name, currenttime, instance.start_time, instance.lifetime)				
			else:
				if not self._terminate_instance(instance.id):
					print "instance.id cannot delete normally."
		

config=parser.parse_args(sys.argv[1:])

pc = ProvisionFactory(config)
pc.run_provision_conc()

