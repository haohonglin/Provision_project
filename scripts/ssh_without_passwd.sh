#!/bin/bash
for i in `seq 1 16`
do
	if [ $i -lt 10 ]; then
	    i=`echo 0$i`
	    echo $i
	fi
	scp ~/.ssh/id_rsa.pub root@a-compute$i:.ssh/id_rsa.pub
	echo $i
	ssh root@a-compute$i "cat /root/.ssh/id_rsa.pub >> /root/.ssh/authorized_keys"
done
