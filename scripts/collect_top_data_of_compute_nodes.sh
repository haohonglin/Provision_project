#/bin/bash
[ ! -x top_data ] && mkdir top_data
for i in `seq 1 16`
do
	if [ $i -lt 10 ]; then
	    i=`echo 0$i`
	fi
	ssh root@a-compute$i "cd /home; sh kill_top.sh"
	scp root@a-compute$i:/home/top.txt "top_data/compute$i.txt"
done

