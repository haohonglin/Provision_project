#!/bin/bash
echo "##To parse the log of provision proxy and get the boot time of VM##"
cat proxy.log | grep " time" |while read line
do
total=`echo $line | awk -F"time:" '{print $2}'`
read line
net=`echo $line | awk -F"time:" '{print $2}'`

booting=`echo "$total-$net"|bc`
echo $booting $net

done
