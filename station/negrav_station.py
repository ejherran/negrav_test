#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import json
import socket
import time
import pool
import subprocess as sp
from threading import Thread

class Console(Thread):
    
    def __init__(self, station):
        self.station = station
        super().__init__()
        
    def run(self):
        print("\n\tInciando consola...")
        while(True):
            inp = input("\n\t\tCMD # ")
            
            if(inp.lower() == 'exit'):
                print("\t\t> Termiando Procesos!.")
                break
            else:
                print("\t\t> "+inp)
        
        self.station.detener()


class Station(Thread):
    
    def __init__(self, nid, conf):
        
        super().__init__()
        
        self.state = 1
        self.kill = False
        self.nid = nid
        self.conf = conf
        self.server = None
        self.sIP = None
        self.BBS = []
        self.BSM = []
        self.SN = []
        self.SNM = []
        self.MN = []
        self.MNM = []
    
    def run(self):
        
        print("\n----------------------------------------------------------------\n")
        
        while(self.state > 0):
            
            if self.kill:
                self.state = 0            
            else:
                if self.state == 1:
                    self.preparar()
                elif self.state == 2:
                    self.baseStation()
                    self.console = Console(self)
                    self.console.start()
                elif self.state == 3:
                    self.bakup()
                    self.detener()
                elif self.state == 4:
                    self.esperar()
        
        print("\t\t> Deteniendo el servicio!.")
        print("\n----------------------------------------------------------------\n")
    
    def log(self, msg):
        f = open("station.log", "a")
        f.write("["+time.strftime("%Y-%m-%d %H:%M:%S")+"] "+msg+"\n")
        f.close()
    
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
            self.state = 2
            print("\n\tEntrando en modo Base Station!")
        else:
            print("\n\tEntrando en modo Backup Base Station!")
            self.state = 3
    
    def baseStation(self):
        
        print("\n\tGenarando Bakup Base Station Pool...")
        self.BBS = pool.getPool(self.conf['BBS_POOL'])
        print("\tGenarando Base Station Momentary Pool...")
        self.BSM = pool.getPool(self.conf['BSM_POOL'])
        print("\tGenarando Sationary Node Pool...")
        self.SN = pool.getPool(self.conf['SN_POOL'])
        print("\tGenarando Stationary Node Momentary Pool...")
        self.SNM = pool.getPool(self.conf['SNM_POOL'])
        print("\tGenarando Mobile Node Pool...")
        self.MN = pool.getPool(self.conf['MN_POOL'])
        print("\tGenarando Mobile Node Momentary Pool...\n")
        self.MNM = pool.getPool(self.conf['MNM_POOL'])
        
        self.activarWifi(self.conf['BS_IP'])
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind( (self.conf['BS_IP'], self.conf['SERVER_PORT']) )
        self.server.listen(8)
        self.state = 4
    
    def bakup(self):
        print("\n\tGenarando Bakup Base Station Pool...")
        self.BBS = pool.getPool(self.conf['BBS_POOL'])
        print("\tGenarando Base Station Momentary Pool...")
        self.BSM = pool.getPool(self.conf['BSM_POOL'])
        print("\tSeleccionando IP momentanea...")
        self.sIp = pool.getRndIP(self.BSM)
        
        self.activarWifi(self.sIp)
        
        self.addProcess()
    
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
        
        res = self.fijarIp(data['assign_ip'])
        print("\tFijando IP "+data['assign_ip']+"!.", res[0])
        
        s.close()
    
    def fijarIp(self, ip):
        res = sp.getstatusoutput("ifconfig "+self.conf['DEV']+" "+ip+" netmask "+self.conf['NETMASK'])
        return res
        
    def activarWifi(self, ip):
        
        res = sp.getstatusoutput("ifconfig "+self.conf['DEV']+" down")
        print("\tPreparando "+self.conf['DEV']+"!.", res[0])
        
        res = sp.getstatusoutput("iwconfig "+self.conf['DEV']+" mode ad-hoc essid \"NEGRAV-"+self.nid+"\" channel "+str(self.conf['CHANNEL']))
        print("\tCreando red Ad-Hoc NEGRAV-"+self.nid+"!.", res[0])
        
        res = self.fijarIp(ip)
        print("\tFijando IP "+ip+"!.", res[0])
    
    def esperar(self):
        
        self.log("Esperando solicitud")
        
        try:
            conn, addr = self.server.accept()
            data = conn.recv(4096)
            self.log("MSG: "+data.decode('utf8'))
        except:
            pass
    
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
                    
                    sta = Station(NID, CNF)
                    try:
                        sta.start()
                        while not sta.kill:
                            pass
                    except (KeyboardInterrupt, SystemExit):
                        sta.detener()
                    
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
