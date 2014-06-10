#!/usr/bin/python
from novaclient import utils
from novaclient import client
from novaclient.v1_1.servers import ServerManager
from novaclient.v1_1.flavors import FlavorManager
from novaclient.v1_1.images import ImageManager

class Cloud_API(object):
	def __init__(self, conf):
		print "Not Implemented!"

	def run_instance(self, name, imageid, flavorid, nics_list, meta_list, files):
		print "Not Implemented!"
		
	def terminate_instance(self, instance_id):
		print "Not Implemented!"
		
	def get_instance(self, instance_id):
		print "Not Implemented!"
	
	def get_connection(self, conf):
		print "Not Implemented!"
	
	def list_instance(self):
		print "Not Implemented!"
	
	def is_instance_running(self, instance_id):	
		print "Not Implemented!"

	def is_instance_exist(self, instance_id):
		print "Not Implemented!"
		
	def is_instance_need_delete(self, instance_id):
		print "Not Implemented!"
		
class Openstack_API(Cloud_API):
	def __init__(self, conf):
		self.get_connection(conf)
		#self.flavors = self.flavor_manager.list()

	def run_instance(self, name, imageid, flavorid, nics_list, meta_list, files):
		try:
			return self.server_manager.create(name=name,image=imageid, flavor=flavorid, nics=nics_list, meta=meta_list, files=files)
			#return self.server_manager.create(name=name,image=imageid, flavor=flavorid, nics=[{"net-id":'e3fffbcf-7e75-4187-b5e9-daa1a5e3bd74'}])
		except Exception as e:
			print "cannot create instance: %s."%str(e)	
		
	def terminate_instance(self, instance_id):
		try:
			self.server_manager.delete(instance_id)
		except Exception as e:
			print "cannot delete instance: %s."%str(e)		
		
	def get_instance(self, instance_id ):
		try:
			return self.server_manager.get(instance_id)
		except Exception as e:
			#print e
			return None

	def get_all_instance_host(self):
		try:
		        search_opts = {
            		    'host': None,
            		    'status': None,
            		    'instance_name': None}
		        servers = self.server_manager.list(search_opts)

		        hostmap={}
        		for inst in servers:
            			server={}
            			server['id']=inst._info['id']
            			server['host']=inst._info['OS-EXT-SRV-ATTR:host']
            			server['name']=inst._info['name']
            			server['status']=inst._info['OS-EXT-STS:vm_state']
            			hostmap[server['id']] = server
        		return hostmap
		except Exception as e:
			print e
			return {}
		
	def list_instances(self):
		try:
		        search_opts = {
           	   	    'all_tenants': None,
            		    'reservation_id': None,
            		    'ip': None,
            		    'ip6': None,
            		    'name': None,
            		    'image': None,
            		    'flavor': None,
            		    'status': None,
            		    'tenant_id': None,
            		    'host': None,
            		    'instance_name': None}
		        return self.server_manager.list(search_opts)
		except Exception as e:
			print e
			return []

	def is_instance_exist(self, instance_id):
		instance = self.get_instance(instance_id)
		if instance == None:
			return False
		return True
	
	def is_instance_need_delete(self, instance_id):
		instance = self.get_instance(instance_id)
		if not instance:
			#print 'is_instance_need_delete %s not exist.'%instance_id
			return False
		if instance and instance.status == "DELETEING":
			return False
		if instance and instance.status == "DELETED":
			return False
		return True
	
	def is_instance_running(self, instance_id):
		instance = self.get_instance(instance_id)
		if instance and instance.status == "ACTIVE":
			return True
		return False
		
	def get_connection(self, conf):
		try:
			self.nova_client = client.Client('1.1', conf.user_name, conf.user_passwd, conf.user_tenant, conf.auth_url, no_cache=True)

			#self.server_manager = ServerManager(self.nova_client)
			#self.flavor_manager = FlavorManager(self.nova_client)
			#self.image_manager = ImageManager(self.nova_client)
			self.server_manager = self.nova_client.servers 
			self.flavor_manager = self.nova_client.flavors 
			self.image_manager = self.nova_client.images 
		except Exception as e:
			print e
			exit(0)
			
		
	def get_flavorid_by_name(self,name):
		flavor_list = self.list_flavors()
		#flavor_list = self.flavors
		for flavor in flavor_list:
			if flavor.name == name:
				return flavor.id
		return ''
		
	def get_imageid_by_name(self,name):
		image_list = self.list_images()
		for img in image_list:
			if img.name == name:
				return img.id
		return ''
		
	def list_flavors(self):
		try:
			return self.flavor_manager.list()
		except Exception as e:
			print e 
		
	def list_images(self):
		try:
			return self.image_manager.list()
		except Exception as e:
			print e 
		
class AWS_API(Cloud_API):
	def __init__(self, conf):
		self.get_connection(conf)
		sleep(2)

	def run_instance(self, conf):
		print "AWS run instance!"
		sleep(2)	
		return 'i-12345678'
		
	def terminate_instance(self, instance_id):
		print "AWS terminate instance!"
		
	def get_instance(self, instance_id):
		print "AWS get instance!"
		sleep(2)	
		
	def is_instance_running(self, instance_id):
		status = self.get_instance(instance_id)
		if instance.status == "running":
			return True
		return False
	
	def get_connection(self, conf):
		print "AWS get connection!"
