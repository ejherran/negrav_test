#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random
import subprocess as sp

def toListInt(l):
    res = []
    for e in l:
        res.append(int(e))
    return res

def toStrIntList(l, sep):
    res = []
    for e in l:
        res.append(str(e))
    return sep.join(res)


def getPool(cnf):
    cnf = cnf.split('-')
    bot = toListInt(cnf[0].split('.'))
    top = toListInt(cnf[1].split('.'))
    
    ips = []
    
    while(True):
        
        ip = toStrIntList(bot, '.')
        ips.append(ip)
        
        if(bot[3] < top[3]):
            bot[3] += 1
        else:
            
            if(bot[2] < top[2]):
                bot[2] += 1
                bot[3] = 0
            else:
                
                if(bot[1] < top[1]):
                    bot[1] += 1
                    bot[2] = 0
                else:
                    if(bot[0] < top[0]):
                        bot[0] += 1
                        bot[1] = 0
                    else:
                        break
    
    return ips

def getRndIP(pool):
    idx = random.randint(0, len(pool)-1)
    return pool[idx]

def searchChannel(dev, ssid):
    l = sp.getstatusoutput("iwlist "+dev+" scan | grep -E \"ESSID|Frequency\"")[1]
    l = l.split("\n")
    nl = []
    lim = len(l)
    
    i = 0
    while(i < (lim-1)):
        nl.append(l[i]+l[i+1])
        i += 2
    
    tar = ''
    for e in nl:
        if('ESSID:"'+ssid+'"' in e):
            tar = e
            break
    tar = tar.replace("(", "|||")
    tar = tar.replace(")", "|||")
    tar = tar.split("|||")
    
    tar2 = ''
    for e in tar:
        if 'Channel' in e:
            tar2 = e
            break
            
    return tar2.split(" ")[1]
