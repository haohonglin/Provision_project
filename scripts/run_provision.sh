#!/bin/sh
iptables -I INPUT 1 -p tcp --dport 8675 -j ACCEPT
echo "tar proxy file ..."
tar -zcvf ProvisionProxy.py.tar.gz ProvisionProxy.py
sleep 1
echo "prepare some shell for compute node to get top data"
sh prepare_to_get_compute_top_data.sh
sleep 1
echo "run workload ..."
sleep 3

python ProvisionWorkload.py --cloud openstack --version Havana --user-name admin --user-passwd 123456 --user-tenant admin --auth-url http://192.168.12.11:5000/v2.0/ --client-generate increasing  --client-interval 5 --boot-type single-image --image-ids 58c47f1b-02ed-4de1-a081-1ecf8afc54fd --net-ids f50553f0-1fa8-4b4d-81e2-6cdca4767680  --host-addr 167.168.133.3:8675   --net-proxy 5f75099e-4357-4cd3-8018-b44147be3f22  --flavor-names m1.tiny --runtime 60000 --random-lifetime True --client-number 200 --max-instances 1 --max-lifetime 300 --min-lifetime 100

echo
echo
echo "collect top data from compute node"
sh collect_top_data_of_compute_nodes.sh
#python ProvisionWorkload.py --cloud openstack --version Havana --user-name admin --user-passwd 123456 --user-tenant admin --auth-url http://192.168.12.11:5000/v2.0/ --client-generate increasing  --client-interval 20 --boot-type single-image --image-ids 58c47f1b-02ed-4de1-a081-1ecf8afc54fd --net-ids ef63a1df-d6aa-4c7d-9aa0-b71a59a43d3a --host-addr 167.12.1.221:8675   --net-proxy 5f75099e-4357-4cd3-8018-b44147be3f22  --flavor-names m1.tiny --runtime 60000 --random-lifetime True --client-number 200 --max-instances 1 --max-lifetime 300 --min-lifetime 100
