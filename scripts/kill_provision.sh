#!/bin/bash
pid=`ps -ef | grep Provision | grep python | awk '{print $2}'`
if [ -n "$pid"  ] ; then
    echo "kill provision process $pid ..."
    kill -9 $pid
else
    echo "none of provision process is running!!!"
fi
