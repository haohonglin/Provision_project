#!/bin/bash

for i in `seq 1 16`
do
	if [ $i -lt 10 ]; then
	    i=`echo 0$i`
	fi
	scp top_file.sh kill_top.sh root@a-compute$i:/home/
	ssh root@a-compute$i "cd /home; sh top_file.sh&" &
done


