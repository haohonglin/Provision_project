#!/bin/bash
echo "##To get the handle number opened by provision program!!!##"
pid=`ps -ef | grep ProvisionWork | grep -v "grep" | awk '{print $2}'`
echo $pid

if [ -n "$pid" ] ; then

while true ;
do
lsof -n | grep -c "$pid"
sleep 2
done

fi
