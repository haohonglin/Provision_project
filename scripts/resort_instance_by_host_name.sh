#!/bin/bash
if [ -ne 1 ]; then
echo "please input the file name"
exit
fi

file=$1

nova service-list | grep "nova-compute" | grep "up" | awk -F"|" '{print $3}' | while read line; do grep "$line" "$file"; done
