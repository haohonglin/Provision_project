#!/usr/bin/python
from neutronclient.v2_0 import client

class neutron_provision:
    def __init__(self, conf): 
	self.neutron = client.Client(username=conf.user_name, password=conf.user_passwd, auth_url=conf.auth_url, tenant_name=conf.user_tenant)

    def get_public_ip_port(self, instance_id):
        port_list = self.neutron.list_ports(device_id=instance_id)["ports"]
        if len(port_list) > 0:
            return port_list[0].get("id")
        return None

    def associate_public_ip(self, publicip_id, instance_id):
        port_id = self.get_public_ip_port(instance_id)
        if port_id == None:
            print "port of %s not available"%instance_id
            return None

        return self.neutron.update_floatingip(publicip_id, body={"floatingip":{"port_id":port_id}}) 

    def associate_proxy_ip(self, instance_id):
        nets = self.neutron.list_networks()
	for net in nets['networks']:
	    if net['router:external']:
		self.public_id = net['id']
	body={}
	body['floatingip']={}
	body['floatingip']['floating_network_id']=self.public_id
	floatingip_id=self.neutron.create_floatingip(body).get("floatingip")['id']
	return self.associate_public_ip(floatingip_id,instance_id)

