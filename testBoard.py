#!/usr/bin/env python
# coding: utf-8

# In[2]:

#BY Sijia Lin 
import serial
import time


class testBoard:
    def __init__(self, port):
        self.ser = serial.Serial(port, 9600)
        if self.ser.isOpen():
            print("test board" + port + " is open")
    def set_channel(self,channel):
        self.ser.write(f'{channel}\n'.encode())    

    def close(self):
        channel=-1
        self.ser.write(f'{channel}\n'.encode())    
        self.ser.close()




