#!/usr/bin/python

import socket, httplib, os, string
import urlparse, time, threading, sys, signal
import argparse
import fcntl
import struct


class Utils:
    @staticmethod
    def get_ip_address(ifname):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	ip_flag=False
	start=time.time()
	while not ip_flag:
	    try:
		print '%f' %(time.time() - start)
        	ip=socket.inet_ntoa(fcntl.ioctl(
                    s.fileno(),
                    0x8915,  # SIOCGIFADDR 
                    struct.pack('256s', ifname[:15])
                    )[20:24])
		ip_flag=True
		print '%f' %(time.time() - start)
		return ip, (time.time() - start)
	    except Exception, e:
		print e
		print '%f' %(time.time() - start)
		time.sleep(1)
ifname=sys.argv[1:][0]
print ifname
print Utils.get_ip_address(ifname)	
print Utils.get_ip_address(ifname)[0]	
