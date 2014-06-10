#!/bin/bash
echo "you can input prefix of the VMs you want to delete, client is default"
echo $1
`nova list > nova.list`
if [ "$1" == "" ]; then 
     echo "default parameter: client"
     cat nova.list | grep -E "client" | while read line
     do
    	inst_id=`echo $line | awk -F"|" '{print $2}'`
    	echo "instance id: $inst_id"
    	nova delete $inst_id
	sleep 2
     done
else
     echo "$1"
     cat nova.list | grep -E "$1" | while read line
     do
          inst_id=`echo $line | awk -F"|" '{print $2}'`
          echo "instance id: $inst_id"
          nova delete $inst_id
	  sleep 2
     done
fi
rm -rf nova.list

