#!/usr/bin/python
import os
import prettytable
tablerow={'a':'b', 'c':'d'}
mtable = prettytable.PrettyTable(["Client","Instance"])
rowarray=['client_test', 'instance_test']
mtable.add_row(rowarray)
print mtable

num=20
life1=100
life2=300
seq=2
filename='seq'+str(seq)+'_num'+str(num)+'_life'+str(life1)+':'+str(life2)+'_provision.res'
print filename
metric={}
metric['hello']='hello'
metric['world']='world'

with open(filename, 'w') as f:
    f.write(str(metric))
    f.write(str(mtable))
    f.close()
