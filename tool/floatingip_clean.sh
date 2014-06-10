#!/bin/bash

`neutron floatingip-list> floatingip.res`
cat floatingip.res
cat floatingip.res | grep -v 'id' | awk -F'|' '{print $2}'| while read line
do
    if [ ! -z $line ]; then
        neutron floatingip-delete $line
    fi
    #`neutron floatingip-delete $line`
    sleep 2
done

rm -rf floatingip.res
