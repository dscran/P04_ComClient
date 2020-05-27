# -*- coding: utf-8 -*-
"""
@author: gregorhartmann
"""
#/sbin/ifconfig
#ps -fA | grep python


import socket
import time
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

while True:
    currentIP = socket.gethostbyname(socket.gethostname())

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)		
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_address = (currentIP, 3001)
    print('server on:', str(currentIP))
    sock.bind(server_address)				
    sock.listen(1)
    
    print('waiting for connection on port 3001')
    connection, clientaddress = sock.accept()
    
    print('connection established to', str(clientaddress))
    
    ds = DummyServer()
    running = True
    try:    
        while running:
            cmd = connection.recv(1024).decode()
            print('command:', cmd)
            connection.sendall(ds.parse(cmd).encode())
            if 'closeconnection' in cmd:
                print('connection closed')
                running = False
                break   
    finally: connection.close()
