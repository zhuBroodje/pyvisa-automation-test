#!/usr/bin/env python
# coding: utf-8

# In[2]:

#Based on Tenma 72 13210 electronic load
import pyvisa as visa

class ElectronicLoad:
    def __init__(self, electronic_load_path):
        self.load = visa.ResourceManager().open_resource(electronic_load_path)
        #self.load.encoding = 'latin_1'
        self.load.read_termination = '\n'
        #self.load.write_termination = None
        print(f"{self.get_IDN()} connected")

    def query(self, command):
        return self.load.query(command)

    def write(self, command):
        self.load.write(command)
        
    def read(self, command):
        return self.load.read(command)
    
    def get_IDN(self):
        return self.load.query("*IDN?")
    
    def set_mode(self, mode,value):
        check=True
        command=''
        if mode.upper()=="C":
            command = f":CURR {value}A"
        elif mode.upper()=="V":
            command = f":VOLT {value}V"
        elif mode.upper()=="P":
            command = f":POW {value}W"
        elif mode.upper()=="R":
            command = f":RES {value}HM"
        else:
            check=False
        if check:
            self.load.write(command)
    def set_function(self,function):
        check=True
        command=''
        if function.upper()=="C":
            command = f":FUNCTION CURR"
        elif function.upper()=="V":
            command = f":FUNCTION VOLT"
        elif function.upper()=="P":
            command = f":FUNCTION POW"
        elif function.upper()=="R":
            command = f":FUNCTION RES"
        else:
            check=False
            #FIXME
            print('Wrong input')
            command = f":FUNCTION CURR"
        if check:
            self.load.write(command)        

    def get_current_voltage(self):
        return float((self.query(":MEAS:VOLT?")).rstrip('V'))
    def get_current_current(self):
        return float((self.query(":MEAS:CURR?")).rstrip('A'))

    def switch(self,v):
        if v==0:
            #print("Turn off load output")     
            self.off()
        else:
            #print("Turn on load output")
            self.on()

    def on(self):
        self.load.write(":INPut ON")
    def off(self):
        self.load.write(":INPut OFF")

    def get_precision(self):
        return 4
# In[ ]:




