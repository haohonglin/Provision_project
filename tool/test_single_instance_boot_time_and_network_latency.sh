#!/bin/bash
echo "the script is to boot a vm and keep pinging to the VM until it is accessible of network"
vm_name="test_ping_to_active_instance"
clean_vm=true

if [ $# -eq 1 ]; then
    [ "$1" == "--no-clean" ] && clean_vm=false
    [ "$1" != "--no-clean" ] && vm_name=$1 && clean_vm=true
else
    [ "$1" == "--no-clean" ] && vm_name=$2 && clean_vm=false 
    [ "$2" == "--no-clean" ] && vm_name=$1 && clean_vm=false
fi

echo "info: vm_name: $vm_name, clean test VM($vm_name): $clean_vm"
echo "start test ... " && sleep 2

dhcp=`ip netns | grep dhcp`
echo "dhcp: $dhcp"

instances=`nova list | grep -c -E "ACTIVE|BUILD|ERROR" `
echo "there are $instances instances in cloud"

nova flavor-list > flavor.list
flavor_id=`cat flavor.list | grep "tiny" | awk -F"|" '{print $2}'`
echo "falvor id:" $flavor_id

nova image-list > image.list
image_id=`cat image.list | grep "ubuntu" | awk -F"|" '{print $2}'`
echo "iamge id: " $image_id

neutron net-list > net.list
net_id=`cat net.list | grep "istack" | awk -F"|" '{print $2}'`
net_id=`echo $net_id`
echo "net id: " $net_id

build_time=0
start=$(date +%s)
echo "nova boot $vm_name --flavor m1.tiny --image $image_id --nic net-id=\"$net_id\""
nova boot "$vm_name" --flavor m1.tiny --image $image_id --nic net-id="$net_id" > $vm_name.file

vm_id=`cat  $vm_name.file | grep "id" | grep -v "_id" | awk -F"|" '{print $3}'`
echo "instance id: " $vm_id

ip=""
while true
do
    end=$(date +%s)
    echo "check instance active...($end)"
    nova show $vm_id > $vm_name.file
    end1=$(date +%s)
    echo "nova show ...($end1)"
    status=`cat $vm_name.file| grep -c -E "ACTIVE|ERROR"`
    if [ $status -gt 0 ]; then
	st=`cat $vm_name.file| grep -c -E "ACTIVE"`
	if [ $st -gt 0 ] ; then
	    ip=`cat $vm_name.file |grep network | awk -F"|" '{print $3}'` 
	    ip=`echo $ip`
	    build_time=$(( $end - $start ))
	    echo "instance $vm_name($vm_id) is active, private ip: $ip, spend time:$build_time"
	else
	    echo "instance $vm_name($vm_id) is ERROR, ERROR INFO:"
	    cat $vm_name.file
	fi
        break
    fi
done

if [ $ip != "" ] ; then
    ip netns exec $dhcp ping -i 1 $ip > $vm_name$ip.ping&
    ping_pid=$!
    echo "ip netns exec $dhcp ping -i 1 $ip > $vm_name$ip.ping&;; pid=$ping_pid"
    count=1
    while true
    do
	ret=`cat $vm_name$ip.ping | grep -c "ttl"`
	echo "$count:cat $vm_name$ip.ping | grep -c ttl ;; return $ret"
	count=$(($count + 1))
	if [ $ret -gt 0 ]; then
	    first_ttl=`cat $vm_name$ip.ping | grep "ttl"| head -n 1`
	    echo $first_ttl
	    expr_time=`echo $first_ttl | awk -F"=" '{print $2}'| awk '{print $1}'`
	    echo "cloud: total $instances instances in cloud;  $vm_name($vm_id) ping time:  spends $expr_time s"
	    echo "instance $vm_name($vm_id) is active, private ip: $ip, build time:$build_time s, ping time: $expr_time s"
	    kill $ping_pid
            break
	fi
	sleep 1
    done
fi

echo "clean temp file ...."
rm -rf flavor.list
rm -rf nova.list
rm -rf image.list
rm -rf net.list
rm -rf $vm_name.file
rm -rf $vm_name$ip.ping
echo "delete instance  $vm_name($vm_id): nova delete $vm_id ..."
$clean_vm && nova delete $vm_id
#nova boot
