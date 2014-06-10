#!/bin/bash
[ -x $1 ] && file="proxy.log"
[ ! -x $1 ] && file="$1"
tt=0.0
cnt=0
cat $file | grep "boot time" | awk -F"boot time:" '{print $2}'| while read line
do
set -a
tt=`echo "$tt+$line"|bc`
cnt=`expr $cnt + 1`
echo $tt > tt
echo $cnt > cnt

done
tt=`cat tt`
cnt=`cat cnt`
echo "average boot time:"  
echo "$tt/$cnt" | bc 

tt=0.0
cnt=0
cat $file| grep network | awk -F"time:" '{print $2}'|while read line
do
tt=`echo "$tt+$line"|bc`
cnt=`expr $cnt + 1`

echo $tt > tt
echo $cnt > cnt
done

tt=`cat tt`
cnt=`cat cnt`
echo "average network time:"  
echo "$tt/$cnt" | bc 

 rm -rf tt cnt
