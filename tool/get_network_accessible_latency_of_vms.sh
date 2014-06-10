#!/bin/bash
cat $1  | grep client | awk -F"|" '{print $5}'
