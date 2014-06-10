#!/bin/bash
echo "# The script is required to run on the network node #"
`ip netns > ns.file`
dhcp=`cat ns.file| grep router`

`nova list > nova.list`
cat nova.list |grep "ACTIVE" | while read line
do
    instance=`echo $line | awk -F"|" '{print $2}'` 
    name=`echo $line | awk -F"|" '{print $3}'` 

    ip_str=`echo $line | awk -F"|" '{print $7}' | awk -F"," '{print $1}'`
    ip=${ip_str:8}
    echo $ip
    ping_res=`ip netns exec $dhcp ping $ip -c 3`
    #ping_res=`ip netns exec $dhcp ping 122.122.12.12 -c 3`
    ok_num=`echo $ping_res | grep ttl | wc -c`
    echo `echo $ping_res | grep ttl | wc -c`
    if  [ $ok_num -eq 1 ]; then
	echo "$instance $name network unreachable"
    elif  [ $ok_num -eq 0 ]; then
	echo "$instance $name network unreachable"
    else
	echo "ping $instance $name :$ip ok"
    fi
    #nova reboot $instance
done

rm -rf ns.file
rm -rf nova.list
