#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu May 14 14:39:56 2020

@author: mbi
"""


import socket
from threading import Lock, Thread
from time import time

from tango import AttrQuality, AttrWriteType, DispLevel, DevState
from tango.server import Device, attribute, command
from tango.server import class_property, device_property


class P04_beamline(Device):

    energy = attribute(label="Energy", dtype=float,
                        display_level=DispLevel.OPERATOR,
                        access=AttrWriteType.READ_WRITE,
                        unit="eV", format="%6.2f",
                        min_value=240, max_value=2000,
                        doc="beamline photon energy (mono and undulator)")

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
        if self.lock.acquire(timeout=0.5):
            msg += ' eoc'
            self.debug_stream('send: ' + msg)
            self.s.sendall(msg.encode())
            ans = self.s.recv(1024).decode()
            assert ans.endswith('eoa')
            self.lock.release()
            self.set_state(DevState.ON)
            return ans[:-4]
        else:
            return 'busy'
    
    @command(dtype_in=str)
    def cmd_async(self, msg):
        '''Send a command without waiting for it to finish.'''
        self.set_state(DevState.MOVING)
        t = Thread(target=self.query, args=(msg,))
        t.daemon = True
        t.start()
    
    def read_energy(self):
        ans = self.query('read mono')
        if 'current position' in ans:
            self._energy = float(ans.split(':')[1])
            return self._energy, time(), AttrQuality.ATTR_VALID
        elif 'busy' in ans:
            self._energy, time(), AttrQuality.ATTR_CHANGING
        else:
            self.error_stream('unexpected or incomplete answer')
            return self._energy, time(), AttrQuality.ATTR_WARNING

    def write_energy(self, energy):
        if self.get_state() == DevState.ON:
            self.set_state(DevState.MOVING)
            self.cmd_async(f'set mono {energy:.2f}')
            self.info_stream(f'Energy set to {energy:.2f}')



if __name__ == "__main__":
    P04_beamline.run_server()
