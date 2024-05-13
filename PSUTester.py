#!/usr/bin/env python
# coding: utf-8

# In[2]:

#BY Sijia Lin 
import time
import matplotlib.pyplot as plt
import numpy as np
import yaml
import csv
import os

from Oscilloscope import *
from PSU_6705 import *
from ElectronicLoad import *
from datetime import datetime

class PSUTester:
    def __init__(self, config_file):
        self.oscilloscope = 0
        self.load = 0
        self.power_supply = 0
        self.config=0  
        self.folder_path=0

        self.file_config(config_file) 
        #Configure connection
        self.instrument_connection()
        self.instrument_init_config()

    def file_config(self,config_file):
        print("File Configuration")
        with open(config_file, 'r') as file:
            config = yaml.safe_load(file)
            self.config = config
        current_date=datetime.now()
        test_date=current_date.strftime("%Y-%m-%d-%H%M")
        dut=self.config['DUT']['device_name']
        self.folder_path = f'{dut} Power Test {test_date}'
        os.makedirs(self.folder_path)  


    def instrument_connection(self):
        print("Instrument Connection")
        #Oscilloscope connection
        self.oscilloscope = Oscilloscope(self.config['test_instrument']['oscilloscope']['path'])
        #Power Supply connection    
        self.power_supply = PSU_6705(self.config['test_instrument']['power_supply']['path'])
        #Load connection
        self.load = ElectronicLoad(self.config['test_instrument']['load']['path'])
        #File for recording test instrument information
        data=[]
        data.append(['Oscilloscope',self.oscilloscope.get_IDN()])
        data.append(['Electronic Load',self.load.get_IDN()])
        data.append(['DC Power Supply',self.power_supply.get_IDN()])
        csv_file_path = f'{self.folder_path}/test_instrument.csv'
        with open(csv_file_path, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(data)



    def instrument_init_config(self):
        print("Instrument Initializing")
        self.load_init_config()
        self.osc_init_config()
        self.dcps_init_config()

    def load_init_config(self):
        self.load.off()
        self.load.set_function('c')

    def osc_init_config(self):
        self.oscilloscope.add_measurement(1,1, 'MEAN') 
        self.oscilloscope.add_measurement(2,1, 'MEAN') 
        self.oscilloscope.add_measurement(3,1, 'PK2PK')    

    def dcps_init_config(self):
        settings=self.config['testboard']
        self.power_supply.off()
        self.power_supply.set_value(2,'v',settings['voltage_supply'])
        self.power_supply.set_value(2,'c',settings['current_supply'])
    
    def test_flow(self):
        print("Test flow start")
        #input configuration
        settings=self.config['DUT']
        print("Input configuration")
        self.input_configuration(settings['input'])
        sequence_checks=[]
        
        for i,settings in settings['output'].items():
            self.run_unit_test(settings)
            input("manual change channel")
            if settings['sequence_check']==True:
                sequence_checks.append(settings['channel'])
 
        if len(sequence_checks)!=0:
            print ("TO check power sequance ")
            print(sequence_checks)
            #TODO
            #self.power_sequence_check(sequence_checks)
        self.end_test()


    def input_configuration(self,input_settings):
        self.power_supply.set_value(1,'v',input_settings['voltage'])
        self.power_supply.set_value(1,'c',input_settings['current'])
        self.oscilloscope.channel_on(input_settings['channel'])
        self.oscilloscope.set_measurement_source(1,input_settings['channel'])

    def run_unit_test(self,settings):
        print(f"\nStart unit test on channel {settings['channel']}")
        #config
        self.oscilloscope.channel_on(settings['channel'])
        self.power_supply.on()
        self.set_dc_test_mode(settings['channel'])
 
        #test
        '''
        DC WAVEFORM WITH NO LOAD
        '''
        plot_title=f'output DC waveform of signal {settings["signal"]} No load'
        w_dc,t_dc,dc_waveform_plot=self.oscilloscope.get_waveform(settings['channel'],plot_title)
        dc_waveform_plot_path=f"{self.folder_path}/dc_waveform_plot(Vin={self.config['DUT']['input']['voltage']}V,Vout={settings['voltage']}V).png"
        dc_waveform_plot.savefig(dc_waveform_plot_path)
        dc_waveform_data_path=f"{self.folder_path}/dc_waveform_data(Vin={self.config['DUT']['input']['voltage']}V,Vout={settings['voltage']}V).csv"
        data = zip(t_dc, w_dc)
        with open(dc_waveform_data_path, 'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(['Timestamp(s)', 'Voltage(V)'],data)
            csv_writer.writerows(data)

        #FIXME necessary?
        #1.2 on/off load rise/fall time
        #print("1.2 on/off load rise/fall time")

        #generating sample points
        sample_points,scale= self.generate_sample_points(settings['max_load'])
        sample_points=np.round(sample_points,self.load.get_precision())
        vo_list, co_list, vi_list, ci_list,vpp_list = [], [], [], [],[]
        self.load.on()
        self.set_ac_test_mode(settings)
        ripple_folder_path=f"{self.folder_path}/Ripple(Vin={self.config['DUT']['input']['voltage']}V,Vout={settings['voltage']}V)"
        os.makedirs(ripple_folder_path)

        print("sampling")
        for i in range (len(sample_points)):
            #Changing load
            self.load.set_mode('C',sample_points[i])
            time.sleep(2) #wait for value stablized

            #TODO rewrite auto range
            #Auto scale oscilloscope range
            #FIXME test if this work
            #self.oscilloscope.auto_range_vertical(settings['channel'],'PK2PK')
            new_v_scale=self.oscilloscope.nearest_v_scale(self.oscilloscope.get_measurement(3)/2)
            current_v_scale=self.oscilloscope.get_y_scale(settings['channel'])
            while (current_v_scale!=new_v_scale):
                self.oscilloscope.set_y_scale(settings['channel'],new_v_scale)
                time.sleep(0.1)
                current_v_scale=new_v_scale
                new_v_scale=self.oscilloscope.nearest_v_scale(self.oscilloscope.get_measurement(3)/2) 
            #FIXME test if this work
            #self.oscilloscope.auto_range_horizontal(settings['channel'])
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
            input_status=self.power_supply.status_inquire()
            #input_v=input_status.get('ch1_out_voltage')
            input_v=self.oscilloscope.get_measurement(1)
            input_c=input_status.get('ch1_out_current')

            '''
            ripple waveform
            '''
            plot_title=f"ripple waveform under output {output_c}A,Vpp={vpp}V "
            w_ac,t_ac,wave_ac=self.oscilloscope.get_waveform(settings['channel'],plot_title)
            ripple_waveform_plot_path=f"{ripple_folder_path}/ripple_waveform_plot(load={output_c}A).png"
            wave_ac.savefig(ripple_waveform_plot_path)
            ripple_waveform_data_path=f"{ripple_folder_path}/ripple_waveform_data(load={output_c}A).csv"
            data = zip(t_ac, w_ac)
            with open(ripple_waveform_data_path, 'w', newline='') as csvfile:
                csv_writer = csv.writer(csvfile)
                csv_writer.writerow(['Timestamp(s)', 'Voltage(V)'])
                csv_writer.writerows(data)
    
            vo_list.append(output_v)
            co_list.append(output_c)
            vpp_list.append(vpp)
            vi_list.append(input_v)
            ci_list.append(input_c)
            # Note: for debug
            print(f"input {input_v}V {input_c}A  output {output_v}V {output_c}A {vpp}VPP")
        
        '''
        efficiency vs load current
        '''
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
        efficiency_plot_path=f"{self.folder_path}/efficiency_plot(Vin={self.config['DUT']['input']['voltage']}V,Vout={settings['voltage']}V).png"
        plt.savefig(efficiency_plot_path)
        efficiency_data_path = f"{self.folder_path}/efficiency_data(Vin={self.config['DUT']['input']['voltage']}V,Vout={settings['voltage']}V).csv"
        data = zip(co_list, efficiency)
        with open(efficiency_data_path, 'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(['Load Current(A)', 'efficiency(%)'])
            csv_writer.writerows(data)

        '''
        load regulation
        '''
        plt.figure(figsize=(10, 5))
        plt.plot(co_list, vo_list)
        plt.grid(True)
        plt.xscale(scale)
        title=f"Load regulation(Vin={self.config['DUT']['input']['voltage']}V,Vout={settings['voltage']}V)"
        plt.title(title)
        plt.ylabel('Vout (V)')
        plt.xlabel('I_LOAD (A)')
        load_regulation_plot_path=f"{self.folder_path}/load_regulation_plot(Vin={self.config['DUT']['input']['voltage']}V,Vout={settings['voltage']}V).png"
        plt.savefig(load_regulation_plot_path)
        load_rugulation_data_path = f"{self.folder_path}/load_regulation_data(Vin={self.config['DUT']['input']['voltage']}V,Vout={settings['voltage']}V).csv"
        data = zip(co_list, vo_list)
        with open(load_rugulation_data_path, 'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(['Load Current(A)', 'Vout(V)'])
            csv_writer.writerows(data)

        '''
        Ripple PKPK
        '''
        plt.figure(figsize=(10, 5))
        plt.plot(co_list, vpp_list)
        plt.grid(True)
        plt.xscale(scale)
        title=f"Ripple PKPK(Vin={self.config['DUT']['input']['voltage']}V,Vout={settings['voltage']}V)"
        plt.title(title)
        plt.ylabel('Vout (V)')
        plt.xlabel('I_LOAD (A)')
        ripple_pkpk_plot_path=f"{self.folder_path}/ripple_pkpk_plot(Vin={self.config['DUT']['input']['voltage']}V,Vout={settings['voltage']}V).png"
        plt.savefig(ripple_pkpk_plot_path)
        ripple_pkpk_data_path = f"{self.folder_path}/ripple_pkpk_data(Vin={self.config['DUT']['input']['voltage']}V,Vout={settings['voltage']}V).csv"
        data = zip(co_list, vo_list)
        with open(ripple_pkpk_data_path, 'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(['Load Current(A)', 'Vpp(V)'])
            csv_writer.writerows(data)

        '''
        All data
        '''
        all_data_path=f"{self.folder_path}/all_data(Vin={self.config['DUT']['input']['voltage']}V,Vout={settings['voltage']}V).csv"
        data = zip(ci_list,vi_list,co_list, vo_list,vpp_list)
        with open(all_data_path, 'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(['Input Current(A)', 'Input Voltage(V)','Load Current(A)', 'Output Voltage(V)','Vpp(V)'])
            csv_writer.writerows(data)

        #finish
        self.oscilloscope.channel_off(settings['channel'])

        ''''ALL FILE SAVED'''
        #EFFICIENCY: efficiency_plot(png), efficiency_data_path(csv)
        #LOAD REGULATION: load_regulation_plot(png),load_rugulation_data_path(csv)
        #RIPPLE PKPK: ripple_pkpk_plot(png),ripple_pkpk_data_path(csv)
        #all(ci,vi,co,vo,vout_pkpk):all_data_path(csv)
        #DC waveform: dc_waveform_plot(png), dc_waveform_data_path(CSV)
        #AC(RIPPLE) waveform:  FOLDER-> PLOTS,CSVS
        
        #FIXME return?
    
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
        self.power_supply.off()
        self.power_supply.close()
        self.load.off()
        self.load.load.close()
        self.oscilloscope.scope.close()
        print("Test ended")
        
# In[ ]:
