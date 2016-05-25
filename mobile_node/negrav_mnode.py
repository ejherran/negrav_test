#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import random
import json
import socket
import time
import hashlib
import pool
import subprocess as sp
from threading import Thread

class Calendario(Thread):
    
    def __init__(self, node):
        
        super().__init__()
        
        self.node = node
        self.agend = []
        self.isRun = True
    
    def run(self):
        
        while(self.isRun):
            
            print(agend)
    
    def addTask(self, task):
        self.agend.append(task)
    
    def detener(self):
        self.isRun = False
            

class MNode(Thread):
    
    def __init__(self, nid, conf):
        
        super().__init__()
        
        self.state = 1
        self.kill = False
        self.nid = nid
        self.conf = conf
        self.server = None
        self.sIP = None
        
        self.gps = [float(self.conf['GPS'][0]), float(self.conf['GPS'][1]), float(self.conf['GPS'][2])]
        self.lps = self.gps[:]
        self.calendario = None
        
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
                    self.activar()
                elif self.state == 3:
                    self.reporte()
                elif self.state == 4:
                    self.esperar()
        
        res = sp.getstatusoutput("service network-manager start")
        print("\t\t> Reactivando Network-Manager!.", res[0])
        print("\t\t> Deteniendo el servicio!.")
        print("\n----------------------------------------------------------------\n")
    
    
    def preparar(self):
        isBase = True
        
        res = sp.getstatusoutput("service network-manager stop")
        print("\tDeteniendo Network-Manager!.", res[0])
        
        res = sp.getstatusoutput("ifconfig "+self.conf['DEV']+" up")
        print("\tHabilitando "+self.conf['DEV']+"!.", res[0])
        
        print("\n\tBuscando red de trabajo: NEGRAV-"+self.nid+"\n")
        
        for i in range(10):
            
            if(self.conf['TOOL'] == 'wt'):
            
                wifiList = sp.getstatusoutput("iwlist "+self.conf['DEV']+" scan | grep SSID")[1]
            
                if 'ESSID:"NEGRAV-'+self.nid+'"' in wifiList:
                    print("\t\tIntento "+str(i+1)+": Ok!")
                    isBase = False
                    break
                else:
                    print("\t\tIntento "+str(i+1)+": Fail!")
            
            else:
            
                wifiList = sp.getstatusoutput("iw dev "+self.conf['DEV']+" scan | grep SSID")[1]
                
                if 'SSID: NEGRAV-'+self.nid in wifiList:
                    print("\t\tIntento "+str(i+1)+": Ok!")
                    isBase = False
                    break
                else:
                    print("\t\tIntento "+str(i+1)+": Fail!")
        
        if isBase:
            print("\n\tRed de trabajo: NEGRAV-"+self.nid+" no encontrada!.\n")
            self.detener()
        else:
            self.state = 2
    
    def activar(self):
        
        print("\n\tGenarando Mobile Node Pool...")
        self.MN = pool.getPool(self.conf['MN_POOL'])
        print("\tGenarando Mobile Node Momentary Pool...")
        self.MNM = pool.getPool(self.conf['MNM_POOL'])
        
        print("\tSeleccionando IP momentanea...")
        self.sIp = pool.getRndIP(self.MNM)
        
        self.activarWifi(self.sIp)
        
        if(self.testBase()):
            self.addProcess()
            self.state = 3
        else:
            print("\n\tBase Station no encontrada!.\n")
            self.detener()
        
    def reporte(self):
        
        r = {}
        r['protocol'] = 'NEGRAV'
        r['version'] = 'v1.0'
        r['cmd'] = 'node_report'
        r['node_ip'] = self.sIp
        r['type'] = 'MN'
        r['GPS'] = self.conf['GPS']
        r['sensor'] = self.conf['sensor']
        
        print("\tEnviando ​node_report...")
        
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.conf['BS_IP'], self.conf['SERVER_PORT']))
        s.sendall(json.dumps(r).encode('utf8'))
        
        s.close()
        
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind( (self.sIp, self.conf['CLIENT_PORT']) )
        self.server.listen(8)
        
        self.calendario = Calendario(self)
        self.calendario.start()
        
        self.state = 4
    
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
    
    def esperar(self):
        
        print("\n\tEsperando solicitud")
        
        try:
            conn, addr = self.server.accept()
            data = conn.recv(4096)
            
            data = data.decode('utf8')
            print("\tMSG: "+data)
            
            try:
                data = json.loads(data)
                
                if('cmd' in list(data.keys())):
                    
                    if(data['cmd'] == 'get'):
                        
                        print("\tSolicitud de datos.")
                        
                        sensor = []
                        
                        for s in data['sensor']:
                            f = False
                            for s2 in self.conf['sensor']:
                                if s == s2['name']:
                                    
                                    reso = self.getNumPart(s2['resolution'])
                                    minv = self.getNumPart(s2['range'][0])
                                    maxv = self.getNumPart(s2['range'][1])
                                    
                                    sca = int((maxv-minv)/reso)
                                    rnd = random.randint(0, sca)
                                    
                                    sensor.append(str(round(minv+(rnd*reso), 2))+s2['units'][0])
                                    f = True
                                    break
                            
                            if(not f):
                                sensor.append("NONE")
                        
                        r = {}
                        r['protocol'] = 'NEGRAV'
                        r['version'] = 'v1.0'
                        r['cmd'] = 'get'
                        r['get_type'] = data['get_type']
                        r['sensor'] = sensor
                        
                        print("\tEnviando datos.")
                        conn.sendall(json.dumps(r).encode('utf8'))
                    
                    elif(data['cmd'] == 'move_request'):
                        
                        print("\tSolicitud de movimiento."))
                        
                        task = {}
                        task['type'] = 'move'
                        task['target'] = (float(data['target_location'][0]), float(data['target_location'][1]))
                        task['road'] = []
                        for p in data['road_map']:
                            task['road'].append((float(p[0]), float(p[1])))
                        task['road'] = (float(data['target_location'][0]), float(data['target_location'][1]))
                        task['period'] = 5
                        task['atime'] = time.time()+task['period']
                        
                        self.calendario.addTask(task)
                        
                else:
                    print("\tERROR: Comando no definido en la solicitud!.")
                
            except Exception as e:
                print("\tERROR: Formato de solicitud incorrecta!. "+str(e))
            
            conn.close()
            
        except Exception as e:
            pass
    
    def getNumPart(self, s):
        pos = '-.0123456789'
        res = ''
        for c in s:
            if c in pos:
                res += c
            else:
                break
        
        return float(res)
    
    def fijarIp(self, ip):
        res = sp.getstatusoutput("ifconfig "+self.conf['DEV']+" "+ip+" netmask "+self.conf['NETMASK'])
        return res
    
    def activarWifi(self, ip):
        
        res = self.fijarIp(ip)
        print("\tFijando IP "+ip+"!.", res[0])
        
        if(self.conf['TOOL'] == 'wt'):
            res = sp.getstatusoutput("iwconfig "+self.conf['DEV']+" essid \"NEGRAV-"+self.nid+"\"")
        else:
            res = sp.getstatusoutput("iw dev "+self.conf['DEV']+" connect \"NEGRAV-"+self.nid+"\"")
        
        print("\tConectado A La Red NEGRAV-"+self.nid+"!.", res[0])
        print("\tEstabilizando El Canal.\n\t\tEsperando 10s...")
        time.sleep(10)
    
    def testBase(self):
        
        print("\n\tBuscando Base Station...")
        
        try:
            r = {}
            r['cmd'] = 'test_bs'
            
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.conf['BS_IP'], self.conf['SERVER_PORT']))
            s.sendall(json.dumps(r).encode('utf8'))
            s.close()
            
            print("\t\tOk!.")
            return True
            
        except:
            print("\t\tFail!.")
            return False
    
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
                    
                    MNo = MNode(NID, CNF)
                    try:
                        MNo.start()
                        while not MNo.kill:
                            pass
                    except (KeyboardInterrupt, SystemExit):
                        MNo.detener()
                    
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
