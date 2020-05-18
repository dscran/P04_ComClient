#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu May 14 14:39:56 2020

@author: Michael Schneider <mschneid@mbi-berlin.de>, Max Born Institut Berlin
"""


import socket
from threading import Lock, Thread
from time import time

from tango import AttrQuality, AttrWriteType, DispLevel, DevState
from tango.server import Device, attribute, command
from tango.server import class_property, device_property


class P04_beamline(Device):
    
    energy = attribute(
        label="photon energy", dtype=float, access=AttrWriteType.READ_WRITE,
        unit="eV", format="%6.2f", min_value=240, max_value=2000)
    
    mono = attribute(
        label="monochromator", dtype=float, access=AttrWriteType.READ,
        unit="eV", format="%6.2f")
    
    exitslit = attribute(
        label="exit slit", dtype=float, access=AttrWriteType.READ_WRITE,
        unit="um", format="%4.0f")
    
    undugap = attribute(
        label="undulator gap", dtype=float, access=AttrWriteType.READ,
        unit="mm", format="%4.0f")

    # host = device_property(dtype=str)
    # port = device_property(dtype=int, default_value=3001)
    
    def init_device(self):
        Device.init_device(self)
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect(('127.0.1.1', 3001))
        self.s.setblocking(True)
        self.lock = Lock()
        self.set_state(DevState.ON)
    
    def query(self, msg):
        '''Send a query and wait for its reply.'''
        if self.lock.acquire(timeout=0.1):
            msg += ' eoc'
            self.debug_stream('sent: ' + msg)
            self.s.sendall(msg.encode())
            ans = self.s.recv(1024).decode()
            self.debug_stream('received: ' + ans)
            assert ans.endswith('eoa')
            self.lock.release()
            return ans[:-4]
        else:
            self.debug_stream(f"can't send '{msg}': socket is busy")
            return 'busy'
    
    def is_movable(self):
        '''Check whether undulator and monochromator are in position.'''
        ans = self.query('check photonenergy')
        ans = True if ans == '1' else False
        self.set_state(DevState.ON if ans else DevState.MOVING)
        return ans
    
    @command(dtype_in=str)
    def cmd_async(self, msg, test):
        '''Send a command without waiting for it to finish.
        
        The socket will still be blocked!
        '''
        t = Thread(target=self.query, args=(msg,))
        t.daemon = True
        t.start()
    
    @command
    def closeconnection(self):
        ans = self.query('closeconnection')
        if 'bye!' in ans:
            self.set_state(DevState.OFF)
    
    def read_attr(self, attr):
        '''Queries the position of given attribute name.
        
        Returns
        -------
        val : float
        tstamp : time stamp
        quality : AttrQuality instance (ATTR_VALID, ATTR_CHANGING, ...)
        '''
        state = self.is_movable()
        ans = self.query(f'read {attr}')
        if 'current position' in ans:
            val = float(ans.split(':')[1])
            return val, time(), state
        elif 'busy' in ans:
            return None, time(), AttrQuality.ATTR_CHANGING
        else:
            self.error_stream('unexpected or incomplete answer')
            return None, time(), AttrQuality.ATTR_WARNING

    def read_undugap(self):
        value, tstamp, state = self.read_attr('undugap')
        q = AttrQuality.ATTR_VALID if state else AttrQuality.ATTR_CHANGING
        return value, tstamp, q
    
    def read_energy(self):
        value, tstamp, state = self.read_attr('photonenergy')
        q = AttrQuality.ATTR_VALID if state else AttrQuality.ATTR_CHANGING
        return value, tstamp, q
    
    def read_mono(self):
        value, tstamp, state = self.read_attr('mono')
        q = AttrQuality.ATTR_VALID if state else AttrQuality.ATTR_CHANGING
        return value, tstamp, q
    
    def read_exitslit(self):
        value, tstamp, state = self.read_attr('mono')
        return value, tstamp, AttrQuality.ATTR_VALID
    
    def write_exitslit(self, value):
        ans = self.query(f'set exitslit {value}')
        if ans == 'done':
            self.debug_stream(f'moved exit slit to {value}')
        else:
            self.debug_stream('failed setting exit slit')
        return
    
    def write_energy(self, energy):
        if self.is_movable():
            ans = self.query(f'send mono {energy:.2f}')
            if ans == 'started':
                self.set_state(DevState.MOVING)
                self.debug_stream(f'Energy moving to {energy:.2f}')
            else:
                self.debug_stream(f'could not send Energy to {energy:.2f}')



if __name__ == "__main__":
    P04_beamline.run_server()
