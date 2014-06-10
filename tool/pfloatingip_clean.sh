#!/bin/bash

neutron floatingip-list > floatingip.file

cat floatingip.file | grep -E "1|2|3|4|5|6|7|8|9|0" |  awk -F"|" '{print $2}' | while read line
do
    echo $line
    neutron floatingip-delete $line
done

rm -rf floatingip.file
