#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu May 14 14:39:56 2020

@author: Michael Schneider <mschneid@mbi-berlin.de>, Max Born Institut Berlin
"""


import socket
from threading import Lock, Thread
from time import time

import tango
from tango import AttrQuality, DevState
from tango.server import Device, attribute, command
from tango.server import device_property
from tango import READ, READ_WRITE


class P04_beamline(Device):

    DYN_ATTRS = [
        dict(name='photonenergy', label='photon energy', dtype=tango.DevFloat,
             access=READ_WRITE, unit='eV', format='%6.2f', min_value=240,
             max_value=2000),
        dict(name='exitslit', label="exit slit", dtype=tango.DevFloat,
             access=READ_WRITE, unit="um", format="%4.0f"),
        dict(name='helicity', label='helicity', dtype=tango.DevLong,
             access=READ_WRITE, min_value=-1, max_value=1),
        dict(name='mono', label="monochromator", dtype=tango.DevFloat,
             access=READ, unit="eV", format="%6.2f"),
        dict(name='undugap', label='undulator gap', dtype=tango.DevFloat,
             access=READ, unit='mm'),
        dict(name='undufactor', label='undulator scale factor',
             access=READ_WRITE, format='%3.2f', dtype=tango.DevFloat),
        dict(name='undushift', label='undulator shift', dtype=tango.DevFloat,
             access=READ, unit='mm'),
        dict(name='ringcurrent', label='ring current', dtype=tango.DevFloat,
             access=READ, unit='mA'),
        dict(name='keithley1', label='beamline keithley', dtype=tango.DevFloat,
             access=READ),
        dict(name='keithley2', label='user keithley', dtype=tango.DevFloat,
             access=READ),
        dict(name='slt2hleft', label='slit hor left', dtype=tango.DevFloat,
             access=READ),
        dict(name='slt2hright', label='slit hor right', dtype=tango.DevFloat,
             access=READ),
        dict(name='slt2vgap', label='slit ver gap', dtype=tango.DevFloat,
             access=READ),
        dict(name='slt2voffset', label='slit ver offset', dtype=tango.DevFloat,
             access=READ),
        dict(name='exsu2bpm', label='exsu2bpm', dtype=tango.DevFloat,
             access=READ),
        dict(name='exsu2baffle', label='exsu2baffle', dtype=tango.DevFloat,
             access=READ),
        dict(name='pressure', label='experiment pressure', access=READ,
             dtype=tango.DevFloat, unit='mbar', format='%.2E'),
        dict(name='screen', label='beamline screen', dtype=tango.DevLong,
             access=READ_WRITE, min_value=0, max_value=2,
             enum_labels=['closed', 'mesh', 'open'])
        ]

    ready_to_move = attribute(
        name='ready_to_move', label='in position', access=READ,
        dtype=tango.DevBoolean, polling_period=1000, fread="is_movable")

    host = device_property(dtype=str, mandatory=True, update_db=True)
    port = device_property(dtype=int, default_value=3001)

    def init_device(self):
        Device.init_device(self)
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((self.host, self.port))
        self.s.setblocking(True)
        self.lock = Lock()
        self.set_state(DevState.ON)

    def initialize_dynamic_attributes(self):
        # TODO: setup polling and event filter
        for d in self.DYN_ATTRS:
            new_attr = attribute(fget=self.read_general,
                                 fset=self.write_general, **d)
            self.add_attribute(new_attr)

    def query(self, msg):
        '''Send a query and wait for its reply.'''
        if self.lock.acquire(timeout=0.1):
            if not msg.endswith(' eoc'):
                msg += ' eoc'
            print('sent:', msg, file=self.log_debug)
            self.s.sendall(msg.encode())
            ans = self.s.recv(1024).decode()
            print('received:', ans, file=self.log_debug)
            assert ans.endswith('eoa')
            self.lock.release()
            return ans[:-4]
        else:
            print(f"can't send '{msg}': socket is locked", file=self.log_error)
            return 'busy'

    def read_general(self, attr):
        key = attr.get_name()
        print('reading', key, file=self.log_debug)
        val, time, quality = self.read_attr(key)
        attr.set_value(val)

    def write_general(self, attr):
        key = attr.get_name()
        val = attr.get_write_value()
        send_attrs = ['photonenergy', 'exitslit', 'helicity', 'screen']
        cmd = 'send' if key in send_attrs else 'set'
        ans = self.query(f'{cmd} {key} {val}')
        if ans == 'started':
            self.set_state(DevState.MOVING)
            print(f'[key] moving to {val}', file=self.log_debug)
        else:
            print(f'could not send {key} to {val}', file=self.log_error)

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
        ans = self.query(f'read {attr}')
        if 'current position' in ans:
            val = float(ans.split(':')[1])
            return val, time(), AttrQuality.ATTR_VALID
        else:
            self.error_stream('Socket busy or unexpected/incomplete answer')
            return None, time(), AttrQuality.ATTR_INVALID



if __name__ == "__main__":
    P04_beamline.run_server()
