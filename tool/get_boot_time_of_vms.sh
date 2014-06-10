#!/bin/bash
if [ $# -ne 1 ] ; then
echo "please input the file"
exit 0
fi
cat $1  | grep client | awk -F"|" '{print $4}'
