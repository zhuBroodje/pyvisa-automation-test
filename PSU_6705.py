#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import serial
import struct
import time

#special written for hightech 6705 dc power supply
class PSU_6705:
    def __init__(self, port):
        self.ser = serial.Serial(port, 9600)
        self.Ch1_status=0
        self.Ch2_status=0
        self.ch1_out_voltage=0
        self.ch1_out_current=0
        self.ch2_out_voltage=0
        self.ch2_out_current=0
        self.ch1_setting_voltage=0
        self.ch1_setting_current=0
        self.ch2_setting_voltage=0
        self.ch2_setting_current=0
  
        if self.ser.isOpen():
            print(f"DC Power Supply 6705 at serial {port} is open")

    def close(self):
        self.ser.close()
        print("Serial close.")
    
    def write(self):
        self.ser.write()
    
    def status_inquire(self):
        self.ser.flushInput()
        query_command='0xF702030409E2ABFD'
        query_command = bytes.fromhex(query_command[2:])
        self.ser.write(query_command)
        data_list=[]
        for _ in range(26):            
            byte_data = self.ser.read(1)  
            data_list.append(byte_data)
        #print(data_list)
        self.Ch1_status=data_list[5]
        self.Ch2_status=data_list[6]
        #CH1 outputting voltage data
        self.ch1_out_voltage =self.bytes_to_oct(data_list[7],data_list[8],100 )
        #Ch1 Current outputting current data
        self.ch1_out_current=self.bytes_to_oct(data_list[9],data_list[10] ,1000 )
        #CH2 outputting voltage data
        self.ch2_out_voltage=self.bytes_to_oct(data_list[11],data_list[12] ,100 )
        #Ch2 Current outputting current data
        self.ch2_out_current=self.bytes_to_oct(data_list[13],data_list[14],1000)
        #CH1 setting voltage data
        self.ch1_setting_voltage =self.bytes_to_oct(data_list[15],data_list[16] ,100 )
        #Ch1 Current setting current data
        self.ch1_setting_current=self.bytes_to_oct(data_list[17],data_list[18],1000  )
        #CH2 setting voltage data
        self.ch2_setting_voltage=self.bytes_to_oct(data_list[19],data_list[20],100  )
        #Ch2 Current setting current data
        self.ch2_setting_current=self.bytes_to_oct(data_list[21],data_list[22],1000)
        #print("Unit V A")
        #for attr_name in self.__dict__:
        #    print(attr_name, ":", getattr(self, attr_name))
        return self.__dict__
        
    def dec_to_hex(self,dec,mul):
        dec=dec*mul
        bytes_result = struct.pack('>H', int(dec))
        #print(bytes_result.hex())
        return bytes_result 
    
    def bytes_to_oct(self,byte_integer,byte_decimal,deg):
        int_integer = int.from_bytes(byte_integer, byteorder='big')
        int_decimal = int.from_bytes(byte_decimal, byteorder='big')
        value = int_integer * 256 + int_decimal
        value = value / deg
        return value
        
    def set_value(self,channel,type,value):
        start_command='0xF7020a'
        c=''
        input_check=True
        if(channel==1):
            if(type=='v'or type=='V'):
                c='0901'+self.dec_to_hex(value,100).hex()+'2f55'
            elif(type=='c'or type=='C'):
                c='0a01'+self.dec_to_hex(value,1000).hex()+'8a56'
            else:
                print("wrong input")
                input_check=False

        elif(channel==2):
            if(type=='v'or type=='V'):
                c='0b01'+self.dec_to_hex(value,100).hex()+'0155'
            elif(type=='c'or type=='C'):
                c='0c01'+self.dec_to_hex(value,1000).hex()+'c855'
            else:
                input_check=False
        else:
            input_check=False
        if input_check==True:
            hex_command=start_command+c+'fd'
            byte_command = bytes.fromhex(hex_command[2:])
            self.ser.write(byte_command)
            #print(hex_command)
            time.sleep(0.1)
        else:
            print("Set failed, wrong input")
    
    def switch_output(self,v):
        start_command='0xF7020a1e01000'
        on_command='0xF7020a1e0100010492fd'
        off_command='0xF7020a1e0100000492fd'
        c=''
        if v==0:
            print("Turn off output")
            c='0'

        else:
            print("Turn on output")
            c='1'
        hex_command=start_command+c+'0492fd'
        byte_command = bytes.fromhex(hex_command[2:])
        self.ser.write(byte_command)
        #print(self.ser.read(10).hex())
    
    def on(self):
        command="0xF7020a1e0100010492fd"
        byte_command = bytes.fromhex(command[2:])
        self.ser.write(byte_command)
    def off(self):
        command="0xF7020a1e0100000492fd"
        byte_command = bytes.fromhex(command[2:])
        self.ser.write(byte_command)       

    def set_connection(self):
        print("sorry I didn't write")
        set_series_command='0xF7020A1F010001F893FD'
        set_parall_command='0xF7020A1F010002f9d3FD'
        series_parallel_cancel_command='0xF7020A1F0100003852FD'

    def get_IDN(self):
        return "PeakTech DC POWER SUPPLY 6075"

