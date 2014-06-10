#!/bin/bash
pid=`ps -ef | grep "neutron-openvswitch-agent" | grep -v "grep" | awk '{print $2}'`
pid=`echo $pid`
top -b -p"$pid" > "/home/top.txt" &
echo $! > pid
