# -*- coding: utf-8 -*-
"""
@author: gregorhartmann
"""
#/sbin/ifconfig
#ps -fA | grep python


import socket
import sys
import time
import os
import random
import numpy as np


class DummyDevice(object):
    def __init__(self, val=0, speed=10):
        self.start_value = val
        self.target_value = val
        self.speed = speed
        self.t_start = time.time()
    
    def get_value(self):
        v0, v1 = self.start_value, self.target_value
        dv = v1 - v0
        t = min(time.time() - self.t_start, np.abs(dv / self.speed))
        return v0 + np.sign(dv) * t * self.speed
    
    def set_value(self, val):
        self.start_value = self.get_value()
        self.target_value = val
        self.t_start = time.time()
        
        
# %%
class DummyServer(object):
    def __init__(self):
        devlist = [
            'photonenergy', 'exitslit', 'helicity','mono', 'undugap',
            'undufactor', 'undushift', 'ringcurrent', 'keithley1', 'keithley2',
            'slt2hleft', 'slt2hright', 'slt2vgap', 'slt2voffset', 'exsu2bpm',
            'exsu2baffle', 'pressure', 'screen'
            ]
        self.devices = {d: DummyDevice() for d in devlist}
        self.writable = ['photonenergy', 'exitslit', 'undufactor', 'screen']
    
    def parse(self, cmd):
        cmd = cmd.split()
        valid = (
            (cmd[-1] == 'eoc')
            & (cmd[0] in ['set', 'read', 'send', 'check', 'closeconnection'])
            )
        if not valid:
            raise ValueError
        if cmd[0] == 'read':
            try:
                val = self.devices[cmd[1]].get_value()
                return f'current position: {val} eoa'
            except KeyError:
                print('trying to read unknown alias', cmd[1])
        if cmd[0] in ['set', 'send']:
            try:
                self.devices[cmd[1]].set_value(float(cmd[2]))
                return 'done eoa'
            except KeyError:
                print('trying to set alias', cmd[1], cmd[2])
            except IndexError:
                print('trying to set alias without value', cmd[1])
        if cmd[0] == 'check':
            dev = self.devices[cmd[1]]
            in_position = 1 if dev.get_value() == dev.target_value else 0
            return f'{in_position} eoa'
        if cmd[0] == 'closeconnection':
            return 'bye! eoa'
    
    
    # %%

class DDevice:
    def __init__(self,kind):
        self.kind=kind
        
        if self.kind=='mono':
            self.a1=260
            self.a2=2300
            self.energy = 780
        
    def Position(self):
        self.give = self.energy + random.random() - 0.5
        return self.give
        
        
atP04=False


Dev_mono=DDevice('mono')
    
class givemeparser:
    def __init__(self,s):
        self.s=s
        self.lll=len(self.s)
        if self.s[0:4]=='set ':
            self.command='set'
            self.curpos=4
        elif self.s[0:5]=='read ':
            self.command='read'
            self.curpos=5
        elif self.s[0:7]=='status ':
            self.command='status'
            self.curpos=7
        elif self.s[0:15]=='closeconnection':
            print('closing')
            self.command='closeconnection'
            self.curpos=15
        elif self.s[0:4]=='OTF ':
            self.command='OTF'
            self.curpos=4
        
        else: self.command='unknown'
        self.alias=''
        for i in self.s[self.curpos:self.lll]:
            self.curpos+=1        
            if i==' ': break
            self.alias+=i    
        self.value='' 
        for i in self.s[self.curpos:self.lll]:
            self.curpos+=1        
            if i==' ': break
            self.value+=i    
        self.parsers=[]
        self.parsernr=self.s[self.curpos:self.lll].count('-')
        #print parsernr
        for nr in range(self.parsernr):
            self.pars=''
            for i in self.s[self.curpos:self.lll]:
                self.curpos+=1        
                if i==' ' or self.curpos==self.lll: 
                    self.parsers.append(self.pars)            
                    break
                self.pars+=i
        if self.command=='read' or self.command=='closeconnection':
            self.value=0
            self.parsers=[]
            
                
        
            
    def __call__(self):
        return [self.command,self.alias,self.value,self.parsers]

class executecommand:
    def __init__(self,commando):
        self.command=commando[0]
        self.alias=commando[1]
        self.value=float(commando[2])
        self.parsers=commando[3]
        self.tango = True
        
        if self.alias=='mono':
            if atP04:
                self.pause=0.1
            #...
            else:
                self.motor=Dev_mono
                self.tango=True
                self.minvalue=260
                self.maxvalue=2300
                
        
       
            
                
            
    def __call__(self):
        
        if self.command=='read':
            self.position=self.motor.Position()
            print 'current position: ' + str(self.position)
            connection.sendall('current position: '+str(self.position)+' eoa')
            
        elif self.command in ['set', 'send']:
            if self.tango:
                if True: #self.alias=='mono':
                    if self.minvalue<=float(self.value)<=self.maxvalue:
                        time.sleep(random.random())
                        # print 'moving for 10 seconds'
                        # time.sleep(10)
                        self.motor.energy = self.value
                        # print 'moving stopped, sending answer'
                        connection.sendall('done eoa')
                    else:
                        connection.sendall('out-of-range eoa')
                        

        else:
            connection.sendall('unknown command eoa')
            
                    
                
        
    
###MAIN###


while True:
    currentIP=socket.gethostbyname(socket.gethostname())

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)		
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_address = (currentIP,3001)
    print 'server on:'+str(currentIP)
    sock.bind(server_address)						
    sock.listen(1)
    
    print 'waiting for connection on port 3001'
    connection, clientaddress = sock.accept()	
    
    print 'connection established to'+str(clientaddress)
    
    
    counter=0
    runner=True
    try:    
        while runner:
            char=connection.recv(3)
            while True:
                curchar = connection.recv(1);
                char+=curchar
                if char[-4:]==' eoc':
                    break
            print 'command:'+char
            commander=givemeparser(char)
            command=commander()
            print 'commander:'
            print command
            executer=executecommand(command)
            executer()
            if 'closeconnection' in char:
                print 'connection closed'
                connection.sendall('bye! eoa')
                runner=False
                break   
            
             
            
    finally: connection.close()
