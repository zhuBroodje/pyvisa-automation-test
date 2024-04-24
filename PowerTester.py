#!/usr/bin/env python
# coding: utf-8

# In[2]:


import time
import matplotlib.pyplot as plt
import numpy as np
import pyvisa as visa
import yaml

from Oscilloscope import *
from PSU_6705 import *
from ElectronicLoad import *

from docx import Document
from docx.shared import Inches
from datetime import datetime

class PowerTester:
    def __init__(self, config_file):
        self.oscilloscope = 0
        self.load = 0
        self.powersupply = 0
        self.config=0
        self.doc=Document()

        with open(config_file, 'r') as file:
            config = yaml.safe_load(file)
            self.config = config
        
        #Generating document
        test_name=self.config['test_content']['test_name']
        current_date=datetime.now()
        test_date=current_date.strftime("%Y-%m-%d-%H%M")
        dut=self.config['DUT']['name']
        self.doc.save(f'{dut} {test_name} {test_date}.docx')
        self.doc.add_heading(f'{test_name}',level=1)
        self.doc.add_paragraph(f'Time: {test_date}\nDUT: {dut}')
        self.doc_path=f'{dut} {test_name} {test_date}.docx'
        self.doc.save(self.doc_path)

        #Configure connection
        self.instrument_connection()
        #TODO: record instrument information
        self.instrument_init_config()

    def power_test(self):
        #TODO
        self.set_dc_test_mode()
        self.efficiency_current()
        self.load_regulation()
        #TODO
        #FIXME: channel selection
        self.set_ac_test_mode(3)
        self.swtich_frequency()
        self.ripple()
        self.power_sequence()

    def efficiency_current(self):
        self.doc.add_heading(f'Effiency vs load current',level=2)

        sample_points= self.generate_sample_points('efficiency')
        sample_points=np.round(sample_points,4) # Notes: should get precision from instruments, 4 is only for this load
        vo_list, co_list, vi_list, ci_list = [], [], [], []
        #Note: Maybe logging?
        for i in range (len(sample_points)):
            self.load.set_mode('C',sample_points[i])
            #self.load.write(f":CURRent {rounded_number[i]}A" )
            time.sleep(2) #wait for value stablized
            # TODO: how to scale?
            # FIXME: how to get the value?
            output_v=self.oscilloscope.get_measurement(2)
            #output_v=self.load.get_current_voltage()
            output_c=self.load.get_current_current()
            #Note : for debug
            print(f"output {output_v} {output_c}")
            vo_list.append(output_v)
            co_list.append(output_c)
            
            input_status=self.powersupply.status_inquire()
            #input_v=input_status.get('ch1_out_voltage')
            # TODO: how to scale?
            # FIXME: how to get the value?
            input_v=self.oscilloscope.get_measurement(1)
            input_c=input_status.get('ch1_out_current')
            # Note: for debug
            print(f"input {input_v} {input_c}")
            vi_list.append(input_v)
            ci_list.append(input_c)

        vo_array, co_array, vi_array, ci_array = np.array(vo_list), np.array(co_list), np.array(vi_list), np.array(ci_list)
        po_array, pi_array = vo_array * co_array, vi_array * ci_array
        efficiency=po_array/pi_array *100
         # Note: for debug
        print(po_array,pi_array,efficiency)

        plt.figure(figsize=(10, 5))
        plt.plot(co_list, efficiency)
        plt.xscale('log')
        plt.grid(True)
        plt.title(f'Efficiency vs Load current (Vin={self.config['DUT']['input']}V,Vout={self.config['DUT']['ouput']}V)')
        plt.ylabel('Efficiency(%)')
        plt.xlabel('I_LOAD (A)')
        plt.savefig('Efficiency vs Load current.png')
        self.doc.add_picture('Efficiency vs Load current.png', width=Inches(4))
        self.doc.save(self.doc_path)

    def generate_points(self,start,end,num,scale):
        if scale == 'log':
            return np.logspace(np.log10(start), np.log10(end), num)  
        elif scale=='linear' :
            return np.linspace(start, end, num)
    
    def generate_sample_points(self,update_config=''):
        test_configuration = self.config['test_configuration']
        settings=test_configuration['default']
        if update_config in test_configuration:
            settings.update(test_configuration[update_config])
        min_load, max_load, sample_num,scale = [settings.get(key) for key in ['min_load', 'max_load', 'sample_num','scale']]
        sample_points=self.generate_points(min_load,max_load,sample_num,scale)
        return sample_points    
        
    def load_regulation(self):
        self.doc.add_heading(f'Load regulation',level=2)
        v_list,c_list=[],[]
        sample_points=self.generate_points('load_regulation')
        #FIXME rounded should be blabla from load
        sample_points=np.round(sample_points,4)
        for i in range (len(sample_points)):
            self.load.set_mode('C', sample_points[i] )
            time.sleep(2)
            v_list.append(self.load.get_current_voltage())
            c_list.append(self.oad.get_current_current())
        # Debug
        print(v_list,c_list)
        plt.figure(figsize=(10, 5))
        plt.plot(c_list, v_list)
        plt.grid(True)
        plt.title(f'Load regulation(Vin={self.config['DUT']['input']}V,Vout={self.config['DUT']['ouput']}V)')
        plt.ylabel('Vout (V)')
        plt.xlabel('I_LOAD (A)')
        plt.savefig('Load regulation.png')
        self.doc.add_picture('Load regulation.png', width=Inches(4))
        self.doc.save(self.doc_path)

    #TODO
    def set_ac_test_mode(self,channel):
        self.oscilloscope.write(f"SELECT:CH{channel} ON")
        self.oscilloscope.write(f"TRIGGER:A:EDGE:SOURCE CH{channel}")
        #FIXME: use filter?
        #self.oscilloscope.write("TRIGGER:A:EDGE:COUPLING HFREJ")#{DC|HFRej|LFRej|NOISErej}
        self.oscilloscope.set_coupling(channel,"AC")
        #FIXME: use filter?
        #self.oscilloscope.write(f"CH{channel}:BANDWIDTH TWENTY")#{TWEnty|TWOfifty|FULl|<NR3>}


    def swtich_frequency(self):
        #FIXME ONLY VALID FOR FIXED FREQUENCY
        self.doc.add_heading(f'Switch Frequency vs load current',level=2)
        sample_points=self.generate_sample_points('switch frequency')
        #FIXME how to get precision
        sample_points=np.round(sample_points,4)
        fo_list,co_list=[],[]
        self.load.on()
        for i in range(len(sample_points)):
            self.load.set_mode('c',sample_points[i])
            time.sleep(2)
            #FIXME how to scale
            self.oscilloscope.auto_scale(3,False)
            #FIXME how to get value
            #output_f=oscilloscope.get_measurement(5)
            #FIXME channel?
            output_f=self.oscilloscope.get_frequency(3)
            output_c=self.load.get_current_current()
            #Debug
            print(f"output {output_f}Hz {output_c}A")
            fo_list.append(float(output_f))
            co_list.append(float(output_c))

        plt.figure(figsize=(10, 5))
        plt.plot(co_list, fo_list)
        plt.grid(True)
        #FIXME scale?
        plt.yscale('log')
        x_tick_values = np.linspace(0, max(co_list), 5)
        plt.xticks(x_tick_values, ['{:.2f}'.format(value) for value in x_tick_values])
        plt.title(f'Switch frequency vs Load current (Vin={self.config['DUT']['input']}V,Vout={self.config['DUT']['ouput']}V)')
        plt.ylabel('Freuquency(Hz)')
        plt.xlabel('I_LOAD (A)')
        plt.savefig('Switch frequency vs Load current.png')
        self.doc.add_picture('Switch frequency vs Load current.png', width=Inches(4))
        self.doc.save(self.doc_path)
            

    def ripple(self):
        #FIXME 
        self.oscilloscope.write("ACQUIRE:MODE SAMPLE")
        sample_points=self.generate_sample_points('ripple')
        #FIXME how to get precision
        sample_points=np.round(sample_points,4)
        vo_list,co_list,p_list=[],[],[]
        for i in range (len(sample_points)):
            self.load.set_mode('A',sample_points[i])
            time.sleep(2)
            #FIXME aaaaa
            self.oscilloscope.auto_scale(3,False)
            output_c=self.load.get_current_current()
            #FIXME how to get? wrong ripple measuremen!
            output_v=self.oscilloscope.measure_ripple(3)
            print(f"output {output_v} {output_c}")
            vo_list.append(output_v)
            co_list.append(output_c)
            #FIXME
            w,t=self.oscilloscope.get_waveform_data(3)
            data = np.vstack((w, t)).T
            name=f"waveform-current {output_c}A.txt"
            np.savetxt(name, data)
            #TODO show figures我好懒
            #md 烦了
        vo=self.config['DUT']['output']
        p_list=vo_list/vo*100 #ripple/output DC value
        #debug
        print(vo_list,co_list,p_list)

    def power_sequence(self):
        #POWER ON
        #FIXME channel?
        self.oscilloscope.channel_off(3)
        self.oscilloscope.set_offset(1,0)
        self.oscilloscope.write('CH1:POSITION 0') 

        self.oscilloscope.write("TRIGGER:A:EDGE:SOURCE CH1")
        self.oscilloscope.write("TRIGGER:A:EDGE:SLOPE RISE")

        self.oscilloscope.set_offset(2,0)
        self.oscilloscope.set_t_scale(0.02)
        #self.oscilloscope.auto_y_scale(1)
        #self.oscilloscope.auto_y_scale(2)
        self.psu.off()
        self.load.off()

        #POWER OFF
        pass


    def instrument_connection(self):
        self.oscilloscope = Oscilloscope(self.config['test_devices']['oscilloscope']['path'])
        self.powersupply = PSU_6705(self.config['test_devices']['power_supply']['path'])
        self.load = ElectronicLoad(self.config['test_devices']['load']['path'])
       
    def instrument_init_config(self):
        self.load_init_config()
        self.osc_init_config()
        self.dcps_init_config()

    def load_init_config(self):
        #print("load_init_config")
        load_settings = self.config['test_devices']['load']['settings']
        self.load.off()
        self.load.set_mode(load_settings.get("function"),load_settings.get("value"))
        
    def osc_init_config(self):
        #print("osc_init_config")
        #initializing channels
        channel_settings = self.config['test_devices']['oscilloscope']['channel_settings']
        for channel, settings in channel_settings.items():
            self.oscilloscope.channel_on(channel)
            if 'coupling' in settings:
                self.oscilloscope.set_coupling(channel, settings['coupling'])
            else:
                self.oscilloscope.set_coupling(channel, 'DC')
            if 'bandwidth' in settings:
                self.oscilloscope.set_bandwidth(channel,settings['bandwidth'])
            else:
                self.oscilloscope.set_bandwidth(channel,'FULL')
        # adding measurements
        measurement_settings = self.config['test_devices']['oscilloscope']['measurement_settings']
        for measurement, settings in measurement_settings.items():
            self.oscilloscope.add_measurement(measurement,settings['channel'], settings['type'])
       
    def dcps_init_config(self):
        settings=self.config['test_devices']['power_supply']['settings']
        self.powersupply.off()
        self.powersupply.set_value(1,'v',settings['input_voltage'])
        self.powersupply.set_value(1,'c',settings['input_current'])
        self.powersupply.set_value(2,'v',settings['testbord_supply'])

    def end_test(self):
        self.load.load.close()
        self.oscilloscope.scope.close()
        self.powersupply.close()
        print("Test ended")
        
        



# In[ ]:
