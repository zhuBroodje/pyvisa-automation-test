#!/usr/bin/env python
# coding: utf-8

# In[2]:


import time
import matplotlib.pyplot as plt
import numpy as np
import yaml

from Oscilloscope import *
from PSU_6705 import *
from ElectronicLoad import *

from docx import Document
from docx.shared import Inches
from datetime import datetime
import os

class PSUTester:
    def __init__(self, config_file):
        self.oscilloscope = 0
        self.load = 0
        self.power_supply = 0
        self.config=0
        self.doc=Document()
        self.folder_path=0
        self.doc_path=0

        self.generate_record_file(config_file) 
        #Configure connection
        self.instrument_connection()
        self.instrument_init_config()

    def generate_record_file(self,config_file):
        with open(config_file, 'r') as file:
            config = yaml.safe_load(file)
            self.config = config
        test_name=self.config['test_configuration']['test_name']
        current_date=datetime.now()
        test_date=current_date.strftime("%Y-%m-%d-%H%M")
        dut=self.config['DUT']['device_name']
        self.folder_path = f'{dut} {test_name} {test_date}'
        os.makedirs(self.folder_path)  
        self.doc_path=f'{self.folder_path}/{dut} {test_name} {test_date}.docx'
        self.doc.save(self.doc_path)

    def instrument_connection(self):
        print("******Instrument Connection******")
        #Oscilloscope connection
        self.oscilloscope = Oscilloscope(self.config['test_instrument']['oscilloscope']['path'])
        #Power Supply connection    
        self.power_supply = PSU_6705(self.config['test_instrument']['power_supply']['path'])
        #Load connection
        self.load = ElectronicLoad(self.config['test_instrument']['load']['path'])

    def instrument_init_config(self):
        print("******Instrument Initializing******")
        self.load_init_config()
        self.osc_init_config()
        self.dcps_init_config()

    def load_init_config(self):
        self.load.off()
        self.load.set_function('c')

    def osc_init_config(self):
        #FIXME simplify
        self.oscilloscope.add_measurement(1,1, 'MEAN') 
        self.oscilloscope.add_measurement(2,1, 'MEAN') 
        self.oscilloscope.add_measurement(3,1, 'PK2PK')    

    def dcps_init_config(self):
        settings=self.config['testboard']
        self.power_supply.off()
        self.power_supply.set_value(2,'v',settings['voltage_supply'])
        self.power_supply.set_value(2,'c',settings['current_supply'])
    
    def test_flow(self):
        print("******Test flow start******")
        #input configuration
        settings=self.config['DUT']
        print("******Input configuration******")
        self.input_configuration(settings['input'])
        sequence_checks=[]
        print("******Start PSUs test******")
        for i,settings in settings['output'].items():
            self.run_unit_test(settings)
            input("manual change channel")
            if settings['sequence_check']==True:
                sequence_checks.append(settings['channel'])
        if len(sequence_checks)!=0:
            #self.power_sequence_check(sequence_checks)
            pass
        self.end_test()


    def input_configuration(self,input_settings):
        self.power_supply.set_value(1,'v',input_settings['voltage'])
        self.power_supply.set_value(1,'c',input_settings['current'])
        self.oscilloscope.channel_on(input_settings['channel'])
        self.oscilloscope.set_measurement_source(1,input_settings['channel'])

    def run_unit_test(self,settings):
        print(f"******Start unit test on channel {settings['channel']}******")
        #config
        self.oscilloscope.channel_on(settings['channel'])
        self.power_supply.on()
        self.set_dc_test_mode(settings['channel'])
 
        #test

        plot_title=f'output DC waveform of signal {settings["signal"]} '
        w_dc,t_dc,dc_waveform_plot=self.oscilloscope.get_waveform(settings['channel'],plot_title)
        #FIXME necessary?
        #1.2 on/off load rise/fall time
        #print("1.2 on/off load rise/fall time")

        #generating sample points
        sample_points,scale= self.generate_sample_points(settings['max_load'])
        sample_points=np.round(sample_points,self.load.get_precision())
        vo_list, co_list, vi_list, ci_list,vpp_list = [], [], [], [],[]
        self.load.on()
        self.set_ac_test_mode(settings)
        print("sampling")
        for i in range (len(sample_points)):
            self.load.set_mode('C',sample_points[i])
            time.sleep(2) #wait for value stablized

            new_v_scale=self.oscilloscope.nearest_v_scale(self.oscilloscope.get_measurement(3)/2)
            current_v_scale=self.oscilloscope.get_y_scale(settings['channel'])
            while (current_v_scale!=new_v_scale):
                self.oscilloscope.set_y_scale(settings['channel'],new_v_scale)
                time.sleep(0.1)
                current_v_scale=new_v_scale
                new_v_scale=self.oscilloscope.nearest_v_scale(self.oscilloscope.get_measurement(3)/2)
            
            new_t_scale=self.oscilloscope.nearest_t_scale(1/self.oscilloscope.get_frequency(settings['channel']))
            current_t_scale=self.oscilloscope.get_t_scale()
            while (current_t_scale!=new_t_scale):
                self.oscilloscope.set_t_scale(new_t_scale)
                time.sleep(0.1)
                current_t_scale=new_t_scale
                new_t_scale=self.oscilloscope.nearest_t_scale(1/self.oscilloscope.get_frequency(settings['channel']))

            #output_v=self.oscilloscope.get_measurement(2)
            output_v=self.load.get_current_voltage()
            output_c=self.load.get_current_current()
            vpp=self.oscilloscope.get_measurement(3)
            plot_title=f"ripple waveform under output {output_c }A "
            w_ac,t_ac,wave_ac=self.oscilloscope.get_waveform(settings['channel'],plot_title)
            #Note : for debug
            print(f"output {output_v} {output_c}")
            vo_list.append(output_v)
            co_list.append(output_c)
            vpp_list.append(vpp)
            input_status=self.power_supply.status_inquire()
            #input_v=input_status.get('ch1_out_voltage')
            # TODO: how to scale?
            # FIXME: how to get the value?
            input_v=self.oscilloscope.get_measurement(1)
            input_c=input_status.get('ch1_out_current')

            # Note: for debug
            print(f"input {input_v} {input_c}")
            vi_list.append(input_v)
            ci_list.append(input_c)
        
        #efficiency vs load current
        vo_array, co_array, vi_array, ci_array = np.array(vo_list), np.array(co_list), np.array(vi_list), np.array(ci_list)
        po_array, pi_array = vo_array * co_array, vi_array * ci_array
        efficiency=po_array/pi_array *100
        plt.figure(figsize=(10, 5))
        plt.plot(co_list, efficiency)
        plt.xscale(scale)     
        plt.grid(True)
        plt.title(f"Efficiency vs Load current (Vin={self.config['DUT']['input']['voltage']}V,Vout={settings['voltage']}V)")
        plt.ylabel('Efficiency(%)')
        plt.xlabel('I_LOAD (A)')
        efficiency_plot=plt.gcf()
        #load regulation
        plt.figure(figsize=(10, 5))
        plt.plot(co_list, vo_list)
        plt.grid(True)
        plt.xscale(scale)
        title=f"Load regulation(Vin={self.config['DUT']['input']['voltage']}V,Vout={settings['voltage']}V)"
        plt.title(title)
        plt.ylabel('Vout (V)')
        plt.xlabel('I_LOAD (A)')
        load_regulation_plot=plt.gcf()
        #finish
        self.oscilloscope.channel_off(settings['channel'])
        return [w_dc,t_dc,dc_waveform_plot,efficiency,efficiency_plot,load_regulation_plot]
    
    def power_sequence_check(self,sequence_checks):
        self.power_supply.off()
        self.load.off()

        #Switch on channels
        channel_in=self.config['DUT']['input']['channel']
        in_scale=self.oscilloscope.nearest_v_scale(self.config['DUT']['input']['voltage'])
        self.oscilloscope.channel_on(channel_in)
        self.oscilloscope.set_y_scale(channel_in,in_scale)
        for i in sequence_checks:
            self.oscilloscope.channel_on(i)
            self.oscilloscope.set_y_scale(i,in_scale)
        self.oscilloscope.set_t_scale(0.01)
        self.oscilloscope.write("HORIZONTAL:MAIN:DELAY:TIME 2e-2") 
        #Config oscilloscope to single mode rise trigger
        self.oscilloscope.write(f"TRIGGER:A:EDGE:SOURCE CH{channel_in}")
        self.oscilloscope.write(f"TRIGGER:A:LEVel {self.config['DUT']['input']['voltage']*0.1}")
        self.oscilloscope.write("TRIGGER:A:EDGE:SLOPE RISE") 
        self.oscilloscope.write("ACQuire:STOPAfter SEQUENCE")
        self.oscilloscope.write("ACQuire:STATE RUN")
        time.sleep(2)
        #Power on sequence
        self.power_supply.on()
        self.oscilloscope.get_waveform_all()
        #Config oscilloscope to single mode fall trigger
        self.oscilloscope.write("TRIGGER:A:EDGE:SLOPE FALL") 
        self.oscilloscope.write(f"TRIGGER:A:LEVel {self.config['DUT']['input']['voltage']*0.5}")
        self.oscilloscope.write("ACQuire:STOPAfter SEQUENCE")
        self.oscilloscope.write("ACQuire:STATE RUN")
        time.sleep(2)
        self.power_supply.off()
        self.oscilloscope.get_waveform_all()
        self.oscilloscope.write("ACQuire:STATE RUN")
        self.oscilloscope.write("ACQuire:STOPAfter RUNSTOP")


    def generate_sample_points(self,load_limit):       
        test_configuration = self.config['test_configuration'].copy()
        settings=test_configuration['default']
        min, max, sample_num,scale = [settings.get(key) for key in ['min_load', 'max_load', 'sample_num','sample_scale']]
        min_load=min*load_limit
        max_load=max*load_limit
        #print(f"min_load {min_load}, max_load {max_load} , sample_num {sample_num},scale {scale}")
        sample_points=self.generate_points(min_load,max_load,sample_num,scale)
        return sample_points,scale    
    def generate_points(self,start,end,num,scale):
        if scale == 'log':
            return np.logspace(np.log10(start), np.log10(end), num)  
        elif scale=='linear' :
            return np.linspace(start, end, num)
        else:
            return np.linspace(start, end, num)


    def set_dc_test_mode(self,channel):
        print(f"******Set DC test mode for channel {channel}******")
        self.oscilloscope.set_acquire_mode('SAMple')
        self.oscilloscope.set_t_scale(0.002)
        self.oscilloscope.set_measurement_source(2,channel)
        for i in range(self.oscilloscope.get_channel_number()):
            s=self.oscilloscope.query(f"select:ch{i+1}?")
            if s=='1':
                self.oscilloscope.auto_y_scale(i+1)
                self.oscilloscope.set_coupling(i+1,'DC')
                self.oscilloscope.set_bandwidth(i+1,'FULl')
    def set_ac_test_mode(self,settings):
        print(f"setting ac mode for ch{settings['channel']}")
        self.oscilloscope.set_measurement_source(3,settings['channel'])
        self.oscilloscope.set_coupling(settings['channel'],"AC")
        max_ripple=settings['voltage']*0.2
        init_scale=self.oscilloscope.nearest_v_scale(max_ripple/2)
        self.oscilloscope.set_y_scale(settings['channel'],init_scale)
        self.oscilloscope.set_bandwidth(settings['channel'],'TWEnty')

    def end_test(self):
        self.load.off()
        self.load.load.close()
        self.oscilloscope.scope.close()
        self.power_supply.off()
        self.power_supply.close()
        print("Test ended")
# In[ ]:
