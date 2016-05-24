#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random

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
