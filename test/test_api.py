#!/usr/bin/python
import threading
import time
import api
from api import Openstack_API
import common
from common import ProvisionInstanceData
from common import ProvisionClientPool
from common import ProvisionInstanceMetric
from common import MetaConfigure
from common import InstancePatitioner
from common import ProvisionProxyMonitorData

class Test:
    def __init__(self):
	self.config=MetaConfigure().config
	self.info_list = []

    def get_cloud_api(self):
        if not (self.config.user_name and self.config.user_passwd and self.config.user_tenant and self.config.auth_url):
	    print 'Input Invalid, user-name, user-password, user-tenant and auth-url is necessary for OpenStack cloud.'
	    return
        return Openstack_API(self.config)

    def create_instance(self):
	cloud_api=self.get_cloud_api()
	cloud_api1=self.get_cloud_api()
	cloud_api2=self.get_cloud_api()
	cloud_api3=self.get_cloud_api()
	cloud_api4=self.get_cloud_api()
	cloud_api5=self.get_cloud_api()
	cloud_api6=self.get_cloud_api()
	args=InstancePatitioner().get_proxy_parameter('test_api')
        flavor_ids=args['flavor_ids']
        image_ids=args['image_ids']
        volume_ids=args['volume_ids']
        nec_ids=args['net_ids']
        meta_list=args['meta']
        files=args['files']
        name=args['name']
		
	start_time=time.time()
        if image_ids and len(image_ids) > 0 and flavor_ids and len(flavor_ids) > 0:
	    proxy_instance = cloud_api.run_instance(name, image_ids[0], flavor_ids[0], nec_ids, meta_list, files)
	    #self.info_list.append(proxy_instance._info)
	    #self.info_list.append(proxy_instance)
	    time.sleep(2)
	    print 'create new vm'
	    proxy_instance2 = cloud_api1.run_instance(name, image_ids[0], flavor_ids[0], nec_ids, meta_list, files)
	    time.sleep(2)
	    print 'create new vm'
	    proxy_instance3 = cloud_api2.run_instance(name, image_ids[0], flavor_ids[0], nec_ids, meta_list, files)
	    time.sleep(2)
	    print 'create new vm'
	    proxy_instance4 = cloud_api3.run_instance(name, image_ids[0], flavor_ids[0], nec_ids, meta_list, files)
	    time.sleep(2)
	    print 'create new vm'
	    proxy_instance5 = cloud_api4.run_instance(name, image_ids[0], flavor_ids[0], nec_ids, meta_list, files)
	    time.sleep(2)
	    print 'create new vm'
	    proxy_instance6 = cloud_api5.run_instance(name, image_ids[0], flavor_ids[0], nec_ids, meta_list, files)
	    time.sleep(2)
	    print 'create new vm'
	    proxy_instance7 = cloud_api6.run_instance(name, image_ids[0], flavor_ids[0], nec_ids, meta_list, files)
	    time.sleep(2)
	    print 'create new vm'
	    proxy_instance8 = cloud_api.run_instance(name, image_ids[0], flavor_ids[0], nec_ids, meta_list, files)
	    #proxy_instance1 = cloud_api1.run_instance(name, image_ids[0], flavor_ids[0], nec_ids, meta_list, files)
	    #proxy_instance2 = cloud_api2.run_instance(name, image_ids[0], flavor_ids[0], nec_ids, meta_list, files)
	    #proxy_instance3 = cloud_api3.run_instance(name, image_ids[0], flavor_ids[0], nec_ids, meta_list, files)
	    #proxy_instance4 = cloud_api4.run_instance(name, image_ids[0], flavor_ids[0], nec_ids, meta_list, files)
	print 'xxxxxxxxxxxxxx'
        print time.time()-start_time
	print 'xxxxxxxxxxxxxx'

	while not cloud_api.is_instance_running(proxy_instance.id):
	    time.sleep(5)
	    print 'building proxy instance: %f s' % (time.time() - start_time)

	build_time=time.time()-float(start_time)
	del cloud_api
	del cloud_api2
	del cloud_api3
	del cloud_api4
	del cloud_api5
	del cloud_api6
	del proxy_instance2
	del proxy_instance3
	del proxy_instance4
	del proxy_instance5
	del proxy_instance6
	del proxy_instance7
	return proxy_instance

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


class testThread(threading.Thread):
    def __init__(self):
	threading.Thread.__init__(self)

    def run(self):
	print 'hello world'
	time.sleep(50)
	print 'thread is finished'


def test_thread():
    testThread().start()
    testThread().start()
    testThread().start()
    testThread().start()
    testThread().start()


def test_connection():
    t=Test()
    t1=time.time()
    cloud_api=t.get_cloud_api()
    t.create_instance()
    t.create_instance()
    t.create_instance()
    t.create_instance()
    t.create_instance()
    t.create_instance()
    t.create_instance()
    t.create_instance()
    t.create_instance()
    t.create_instance()
    t.create_instance()
    t.create_instance()
    t.create_instance()
    t.create_instance()

    print 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
    time.sleep(100)
    inst=t.create_instance()
    print time.time() - t1
    inst.get()
    start=time.time()
    print inst.__dict__.keys()
    print inst._info['OS-EXT-SRV-ATTR:host']
    print inst._info['os-extended-volumes:volumes_attached']
    time.sleep(10)
    print 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
    inst.delete()
    time.sleep(10)
    print 'instance reffff'
    time.sleep(100)


if __name__ == '__main__':
    test_thread()
    sleep(10)
    test_thread()
    sleep(10)
    test_thread()
    sleep(10)
    test_thread()
    sleep(10)


