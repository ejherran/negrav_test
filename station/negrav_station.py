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
            elif(inp.lower() == 'list'):
                
                print("\t\t> BACKUPS")
                for k in list(self.station.aBBS.keys()):
                    print("\t\t\t"+k+": "+self.station.aBBS[k]['ip'])
                
                print("")
                
                print("\t\t> NODOS ESTACIONARIOS")
                for k in list(self.station.aSN.keys()):
                    print("\t\t\t"+k+": "+self.station.aSN[k]['ip'])
                
                print("")
                
                print("\t\t> NODOS MÓVILES")
                for k in list(self.station.aMN.keys()):
                    print("\t\t\t"+k+": "+self.station.aMN[k]['ip'])
            
            elif(inp.lower() == 'list bk'):
                
                print("\t\t> BACKUPS")
                for k in list(self.station.aBBS.keys()):
                    print("\t\t\t"+k+": "+self.station.aBBS[k]['ip'])
            
            elif(inp.lower() == 'list sn'):
                
                print("\t\t> NODOS ESTACIONARIOS")
                for k in list(self.station.aSN.keys()):
                    print("\t\t\t"+k+": "+self.station.aSN[k]['ip'])
                    
            elif(inp.lower() == 'list mn'):
                
                print("\t\t> NODOS MÓVILES")
                for k in list(self.station.aMN.keys()):
                    print("\t\t\t"+k+": "+self.station.aMN[k]['ip'])
            
            elif(inp.lower().split(" ")[0] == 'desc'):
                
                tag = inp.lower().split(" ")[1]
                
                obj = None
                
                if(tag in list(self.station.aSN.keys())):
                    obj = self.station.aSN[tag]
                elif(tag in list(self.station.aMN.keys())):
                    obj = self.station.aMN[tag]
                else:
                    print("\t\t> Descipción no disponible")
                
                if obj != None:
                    print("\t\t\tIP: "+obj['ip'])
                    print("\t\t\tGPS: Latitud ("+obj['GPS'][0]+")  Longitud("+obj['GPS'][1]+") Altitud("+obj['GPS'][2]+")")
                    print("\t\t\tSENSORES: ")
                    for s in obj['sensor']:
                        print("\t\t\t\tNombre: "+s['name'])
                        print("\t\t\t\tUnidades: "+', '.join(s['units']))
                        print("\t\t\t\tResolución: "+s['resolution'])
                        print("\t\t\t\tRango: "+' a '.join(s['range']))
            
            elif(inp.lower().split(" ")[0] == 'get'):
                par = inp.lower().split(" ")
                tag = inp.lower().split(" ")[1]
                
                obj = None
                
                if(tag in list(self.station.aSN.keys())):
                    obj = self.station.aSN[tag]
                elif(tag in list(self.station.aMN.keys())):
                    obj = self.station.aMN[tag]
                else:
                    print("\t\t> Consulta no disponible")
                
                if obj != None:
                    
                    r = {}
                    r['protocol'] = 'NEGRAV'
                    r['version'] = 'v1.0'
                    r['cmd'] = 'get'
                    
                    if(par[2] == 'all'):
                        r['get_type'] = 'all'
                        ls = []
                        for s in obj['sensor']:
                            ls.append(s['name'])
                    else:
                        r['get_type'] = 'array'
                        ls = par[2:]
                    
                    r['sensor'] = ls
                    
                    try:
                    
                        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        s.connect((obj['ip'], self.station.conf['CLIENT_PORT']))
                        s.sendall(json.dumps(r).encode('utf8'))
                        
                        data = s.recv(4096)
                        data = data.decode('utf8')
                        data = json.loads(data)
                        
                        for i in range(len(r['sensor'])):
                            print("\t\t\t"+r['sensor'][i]+": "+data['sensor'][i])
                    
                    except Exception as e:
                        
                        print("\t\t> Nodo no disponible", e)
                        
                    s.close()
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
        self.aBBS = {}
        self.aSN = {}
        self.aMN = {}
        self.nVer = 0
        self.hVer = ''
        self.lastBK = 0
        self.raiseBk = False
    
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
                    self.backup()
                elif self.state == 4:
                    self.esperar()
                elif self.state == 5:
                    
                    if ((time.time() - self.lastBK) >= self.conf['INTERVAL_BK']):
                        self.bkProcess()
        
        res = sp.getstatusoutput("service network-manager start")
        print("\t\t> Reactivando Network-Manager!.", res[0])
        print("\t\t> Deteniendo el servicio!.")
        print("\n----------------------------------------------------------------\n")
    
    def nextVersion(self):
        self.nVer += 1
        m = hashlib.sha1()
        m.update(str(self.nVer).encode('utf8'))
        self.hVer = m.hexdigest().upper()
    
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
            self.preStation()
    
    def preStation(self):
        
        print("\n\tGenarando Backup Base Station Pool...")
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
        
        self.sIp = pool.getRndIP(self.BSM)
        
        self.activarWifi(self.sIp)
        
        if (not self.testBase()):
            self.state = 2
        else:
            self.state = 3
    
    def baseStation(self):
        
        print("\n\tEntrando En Modo Base Station!.")
        print("\tFijando IP ["+self.conf['BS_IP']+"].")
        self.fijarIp(self.conf['BS_IP'])
        
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind( (self.conf['BS_IP'], self.conf['SERVER_PORT']) )
        self.server.listen(8)
        self.state = 4
    
    def backup(self):
        print("\n\tEntrando En Modo Backup Base Station!.")
        
        self.addProcess()
        
        self.state = 5
    
    def bkProcess(self):
        
        try:
            r = {}
            r['protocol'] = 'NEGRAV'
            r['version'] = 'v1.0'
            r['cmd'] = 'backup_up2date'
            r['bkup_ip'] = self.sIp
            
            print("\tEnviando ​backup_up2date...")
            
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(15)
            s.connect((self.conf['BS_IP'], self.conf['SERVER_PORT']))
            s.sendall(json.dumps(r).encode('utf8'))
            
            print("\tEsperando ​backup_up2date response...")
            
            data = s.recv(4096)
            data = data.decode('utf8')
            data = json.loads(data)
            
            tmpVer = data['bkup_version']
            
            print("\tData Version Recibida: "+tmpVer)
            
            if(tmpVer != self.hVer):
                self.updateBk()
            else:
                print("\tData Version Sin Cambios: "+tmpVer)
            
        except Exception as e:
            print("\n\tBase Station Perdida.", e)
            
            lbk = []
            for k in list(self.aBBS.keys()):
                lbk.append( self.aBBS[k]['ip'] )
            
            lbk.sort()
            
            if(self.sIp == lbk[0]):
                
                lbk = lbk[1:]
                self.aBBS = {}
        
                for bip in lbk:
                    tag = 'bk'+str(len(self.aBBS)+1)
                    self.aBBS[tag] = {'ip': bip}
                
                self.nextVersion()
                
                print("\n\tEntrando en modo Base Station.")
                self.raiseBk = True
                self.state = 2
            else:
                print("\n\tEsperando nueva Base Station.")
        
        s.close()
        self.lastBK = time.time()
    
    def updateBk(self):
        
        r = {}
        r['protocol'] = 'NEGRAV'
        r['version'] = 'v1.0'
        r['cmd'] = 'backup_update'
        r['bkup_ip'] = self.sIp
        
        print("\tEnviando ​backup_update...")
        
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(15)
        s.connect((self.conf['BS_IP'], self.conf['SERVER_PORT']))
        s.sendall(json.dumps(r).encode('utf8'))
        
        print("\tEsperando ​backup_update response...")
        
        data = s.recv(4096)
        data = data.decode('utf8')
        data = json.loads(data)
        
        self.aBBS = {}
        self.aSN = {}
        self.aMN = {}
        
        for bip in data['bkup_list']:
            
            try:
                idx = self.BBS.index(bip)
                del(self.BBS[idx])
            except:
                pass
            
            tag = 'bk'+str(len(self.aBBS)+1)
            self.aBBS[tag] = {'ip': bip}
        
        for node in data['nodes']:
            if(node['type'] == 'SN'):
                try:
                    idx = self.SN.index(node['node_ip'])
                    del(self.SN[idx])
                except:
                    pass
                tag = 'sn'+str(len(self.aSN)+1)
                self.aSN[tag] = {'ip': node['node_ip']}
                self.aSN[tag]['type'] = node['type']
                self.aSN[tag]['GPS'] = node['GPS']
                self.aSN[tag]['sensor'] = node['sensor']
            else:
                try:
                    idx = self.MN.index(node['node_ip'])
                    del(self.MN[idx])
                except:
                    pass
                tag = 'mn'+str(len(self.aMN)+1)
                self.aMN[tag] = {'ip': node['node_ip']}
                self.aMN[tag]['type'] = node['type']
                self.aMN[tag]['GPS'] = node['GPS']
                self.aMN[tag]['sensor'] = node['sensor']
        
        self.nVer = int(time.time()+1)
        self.hVer = data['bkup_version']
        
        print("\tBackup Data Version Actualizada!.")
        
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
        
        res = self.fijarIp(ip)
        print("\tFijando IP "+ip+"!.", res[0])
        
        if(self.conf['TOOL'] == 'wt'):
            chn = pool.searchChannel(self.conf['DEV'], "NEGRAV-"+self.nid)
            res = sp.getstatusoutput("iwconfig "+self.conf['DEV']+" essid \"NEGRAV-"+self.nid+"\" channel "+chn)
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
    
    def esperar(self):
        
        self.log("Esperando solicitud")
        
        try:
            conn, addr = self.server.accept()
            data = conn.recv(4096)
            
            data = data.decode('utf8')
            self.log("MSG: "+data)
            
            try:
                data = json.loads(data)
                
                if('cmd' in list(data.keys())):
                    
                    if(data['cmd'] == 'add_request'):
                        sip = data['source_ip']
                        
                        if(sip in self.BSM):
                            self.log("Detectada Backup Base Station.")
                            sip = self.BBS[0]
                            self.BBS = self.BBS[1:]
                            tag = 'bk'+str(len(self.aBBS)+1)
                            self.log("Registrando Backup Base Station: "+tag+" IP: "+sip)
                            self.aBBS[tag] = {'ip': sip}
                        elif(sip in self.SNM):
                            self.log("Detectado Nodo Estacionario.")
                            sip = self.SN[0]
                            self.SN = self.SN[1:]
                            tag = 'sn'+str(len(self.aSN)+1)
                            self.log("Registrando Nodo Estacionario: "+tag+" IP: "+sip)
                            self.aSN[tag] = {'ip': sip}
                        elif(sip in self.MNM):
                            self.log("Detectado Nodo Móvil.")
                            sip = self.MN[0]
                            self.MN = self.MN[1:]
                            tag = 'sn'+str(len(self.aMN)+1)
                            self.log("Registrando Nodo Móvil: "+tag+" IP: "+sip)
                            self.aMN[tag] = {'ip': sip}
                        
                        r = {}
                        r['protocol'] = 'NEGRAV'
                        r['version'] = 'v1.0'
                        r['cmd'] = 'add_response'
                        r['assign_ip'] = sip
                        
                        self.log("Enviando add_response!.")
                        
                        conn.sendall(json.dumps(r).encode('utf8'))
                        
                        self.nextVersion()
                        self.log("Actualizando Data Version: "+self.hVer)
                    
                    elif(data['cmd'] == 'node_report'):
                        tag = self.getTag(data['node_ip'])
                        self.log("Reporte De Nodo ["+tag+":"+data['node_ip']+"]")
                        if(data['type'] == 'SN'):
                            self.aSN[tag]['type'] = data['type']
                            self.aSN[tag]['GPS'] = data['GPS']
                            self.aSN[tag]['sensor'] = data['sensor']
                        else:
                            self.aMN[tag]['type'] = data['type']
                            self.aMN[tag]['GPS'] = data['GPS']
                            self.aMN[tag]['sensor'] = data['sensor']
                        
                    
                    elif(data['cmd'] == 'backup_up2date'):
                        
                        self.log("Solicitud de actualización de backup.")
                        r = {}
                        r['protocol'] = 'NEGRAV'
                        r['version'] = 'v1.0'
                        r['cmd'] = 'backup_up2date'
                        r['bkup_version'] = self.hVer
                        
                        self.log("Enviando version de la backup actual ["+self.hVer+"].")
                        
                        conn.sendall(json.dumps(r).encode('utf8'))
                    
                    elif(data['cmd'] == 'backup_update'):
                        
                        self.log("Solicitud de actualización de datos en backup.")
                        r = {}
                        r['protocol'] = 'NEGRAV'
                        r['version'] = 'v1.0'
                        r['cmd'] = 'backup_update'
                        r['bkup_version'] = self.hVer
                        
                        r['bkup_list'] = []
                        
                        for k in list(self.aBBS.keys()):
                            r['bkup_list'].append( self.aBBS[k]['ip'] )
                        
                        r['nodes'] = []
                        
                        for k in list(self.aSN.keys()):
                            node = {}
                            node['node_ip'] = self.aSN[k]['ip']
                            node['type'] = self.aSN[k]['type']
                            node['GPS'] = self.aSN[k]['GPS']
                            node['sensor'] = self.aSN[k]['sensor']
                            
                            r['nodes'].append(node)
                        
                        for k in list(self.aMN.keys()):
                            node = {}
                            node['node_ip'] = self.aMN[k]['ip']
                            node['type'] = self.aMN[k]['type']
                            node['GPS'] = self.aMN[k]['GPS']
                            node['sensor'] = self.aMN[k]['sensor']
                            
                            r['nodes'].append(node)
                        
                        self.log("Enviando datos de la backup actual ["+self.hVer+"].")
                        
                        conn.sendall(json.dumps(r).encode('utf8'))
                        
                else:
                    self.log("ERROR: Comando no definido en la solicitud!.")
                
            except Exception as e:
                self.log("ERROR: Formato de solicitud incorrecta!. "+str(e))
            
            conn.close()
            
        except Exception as e:
            self.log("ERROR: Problemas de red!. "+str(e))
    
    def detener(self):
        
        try:
            self.kill = True
            if self.server:
                print("\t\t> Cerrando socket")
                self.server.shutdown(socket.SHUT_RDWR)
        except:
            pass
    
    def getTag(self, ip):
        tag = ''
        
        for k in list(self.aSN.keys()):
            if(self.aSN[k]['ip'] == ip):
                tag = k
                break
        
        if(tag == ''):
            for k in list(self.aMN.keys()):
                if(self.aMN[k]['ip'] == ip):
                    tag = k
                    break
        
        return k


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
