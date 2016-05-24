#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import json
import socket
import time
import hashlib
import pool
import subprocess as sp
from threading import Thread

class SNode(Thread):
    
    def __init__(self, nid, conf):
        
        super().__init__()
        
        self.state = 1
        self.kill = False
        self.nid = nid
        self.conf = conf
        self.server = None
        self.sIP = None
        
        self.SN = []
        self.SNM = []
    
    def run(self):
        
        print("\n----------------------------------------------------------------\n")
        
        while(self.state > 0):
            
            if self.kill:
                self.state = 0            
            else:
                if self.state == 1:
                    self.preparar()
                elif self.state == 2:
                    self.activar()
                elif self.state == 3:
                    self.reporte()
                    self.detener()
        
        print("\t\t> Deteniendo el servicio!.")
        print("\n----------------------------------------------------------------\n")
    
    
    def preparar(self):
        isBase = True
        
        res = sp.getstatusoutput("service network-manager stop")
        print("\tDeteniendo Network-Manager!.", res[0])
        
        res = sp.getstatusoutput("ifconfig "+self.conf['DEV']+" up")
        print("\tHabilitando "+self.conf['DEV']+"!.", res[0])
        
        print("\n\tBuscando red de trabajo: NEGRAV-"+self.nid+"\n")
        
        for i in range(5):
            
            wifiList = sp.getstatusoutput("iwlist "+self.conf['DEV']+" scan | grep SSID")[1]
            
            if 'ESSID:"NEGRAV-'+self.nid+'"' in wifiList:
                print("\t\tIntento básico "+str(i+1)+": Ok!")
                isBase = False
                break
            else:
                print("\t\tIntento básico "+str(i+1)+": Fail!")
        
        print("")
        
        if isBase:
            
            for i in range(5):
            
                wifiList = sp.getstatusoutput("iw dev "+self.conf['DEV']+" scan | grep SSID")[1]
                
                if 'SSID: NEGRAV-'+self.nid in wifiList:
                    print("\t\tIntento avanzado "+str(i+1)+": Ok!")
                    isBase = False
                    break
                else:
                    print("\t\tIntento avanzado "+str(i+1)+": Fail!")
        
        if isBase:
            print("\n\tRed de trabajo: NEGRAV-"+self.nid+" no encontrada!.\n")
            self.detener()
        else:
            print("\n\tActivando Nodo Estacionario!")
            self.state = 2
    
    def activar(self):
        
        print("\tGenarando Sationary Node Pool...")
        self.SN = pool.getPool(self.conf['SN_POOL'])
        print("\tGenarando Stationary Node Momentary Pool...")
        self.SNM = pool.getPool(self.conf['SNM_POOL'])
        
        print("\tSeleccionando IP momentanea...")
        self.sIp = pool.getRndIP(self.SNM)
        
        self.activarWifi(self.sIp)
        
        self.addProcess()
        
        self.state = 3
    
    def reporte(self):
        
        r = {}
        r['protocol'] = 'NEGRAV'
        r['version'] = 'v1.0'
        r['cmd'] = 'node_report'
        r['node_ip'] = self.sIp
        r['type'] = 'SN'
        r['GPS'] = self.conf['GPS']
        r['sensor'] = self.conf['sensor']
        
        print("\tEnviando ​node_report...")
        
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.conf['BS_IP'], self.conf['SERVER_PORT']))
        s.sendall(json.dumps(r).encode('utf8'))
        
        s.close()
    
    def addProcess(self):
        
        r = {}
        r['protocol'] = 'NEGRAV'
        r['version'] = 'v1.0'
        r['cmd'] = 'add_request'
        r['source_ip'] = self.sIp
        
        print("\tEnviando ​add_request...")
        
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.conf['BS_IP'], self.conf['SERVER_PORT']))
        s.sendall(json.dumps(r).encode('utf8'))
        
        print("\tEsperando ​add_response...")
        
        data = s.recv(4096)
        data = data.decode('utf8')
        data = json.loads(data)
        
        self.sIp = data['assign_ip']
        res = self.fijarIp(self.sIp)
        print("\tFijando IP "+self.sIp+"!.", res[0])
        
        s.close()
    
    def fijarIp(self, ip):
        res = sp.getstatusoutput("ifconfig "+self.conf['DEV']+" "+ip+" netmask "+self.conf['NETMASK'])
        return res
    
    def activarWifi(self, ip):
        
        res = sp.getstatusoutput("ifconfig "+self.conf['DEV']+" down")
        print("\tPreparando "+self.conf['DEV']+"!.", res[0])
        
        res = sp.getstatusoutput("iwconfig "+self.conf['DEV']+" mode ad-hoc essid \"NEGRAV-"+self.nid+"\"")
        print("\tCreando red Ad-Hoc NEGRAV-"+self.nid+"!.", res[0])
        
        res = self.fijarIp(ip)
        print("\tFijando IP "+ip+"!.", res[0])
    
    def detener(self):
        
        try:
            self.kill = True
            if self.server:
                print("\t\t> Cerrando socket")
                self.server.shutdown(socket.SHUT_RDWR)
        except:
            pass


def main(args):
    
    try:
        if(len(args) == 2):
            NID = int(args[1])
            if NID >= 0 and NID <= 15:
                NID = hex(NID).split('x')[1].upper()
                
                try:
                    
                    data = open("config.json", "r")
                    CNF = json.load(data)
                    data.close()
                    
                    sno = SNode(NID, CNF)
                    try:
                        sno.start()
                        while not sno.kill:
                            pass
                    except (KeyboardInterrupt, SystemExit):
                        sno.detener()
                    
                except:
                    print("Error de configuración: Corregir config.json.")
                
            else:
                print("Debe indicar un NID entre 0 y 15.")
        else:
            print("Use: python3 negrav_station.py NID.")
    except:
        print("Parámetros erróneos: NID debe ser un entero.")
    
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
