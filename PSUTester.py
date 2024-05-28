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
from datetime import datetime

from Oscilloscope import *
from PSU_6705 import *
from ElectronicLoad import *
from TestBoard import *


class PSUTester:
    def __init__(self, config_file):
        self.oscilloscope = 0
        self.load = 0
        self.power_supply = 0
        self.config=0  
        self.folder_path=0
        self.tb=0

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
        #test board connection
        self.tb = TestBoard(self.config['testboard']['port'])
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
 

    def tb_init_config(self):
        self.power_supply.set_value(2,'v',self.config['testboard']['voltage_supply'])
        self.power_supply.set_value(2,'c',self.config['testboard']['current_supply'])

    def load_init_config(self):
        self.load.off()
        self.load.set_function('c')

    def osc_init_config(self):
        self.oscilloscope.write("*RST")
        self.oscilloscope.set_y_scale(1,10)
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
        sequence_checks.append([settings['input']['channel'],settings['input']['voltage'],settings['input']['signal']])
        for i,settings in settings['output'].items():
            self.run_unit_test(settings)
            
            if settings['sequence_check']==True:
                sequence_checks.append([settings['channel'],settings['voltage'],settings['signal']])
        if len(sequence_checks)!=0:
            print(sequence_checks)    
            self.power_sequence_check(sequence_checks)
        self.end_test()

    def input_configuration(self,input_settings):
        self.power_supply.set_value(1,'v',input_settings['voltage'])
        self.power_supply.set_value(1,'c',input_settings['current'])
        self.oscilloscope.channel_on(input_settings['channel'])
        self.oscilloscope.set_measurement_source(1,input_settings['channel'])

    def run_unit_test(self,settings):
        unit_folder_path= f"{self.folder_path}/{settings['signal']}"
        os.makedirs(unit_folder_path)
        print(f"\nStart unit test on channel {settings['channel']}")
        #config
        self.oscilloscope.channel_on(settings['channel'])
        self.load.on()
        self.power_supply.on()
        self.tb.set_channel(settings['channel'])
        print(f"set channel to {settings['channel']}")
        time.sleep(1)
        self.set_dc_test_mode(settings['channel']) 

        #generating sample points
        sample_points,scale= self.generate_sample_points(settings['max_load'])
        sample_points=np.round(sample_points,self.load.get_precision())
        
        '''
        DC WAVEFORM WITH NO LOAD
        '''
        plot_title=f'output DC waveform of signal {settings["signal"]} No load'
        w_dc,t_dc,dc_waveform_plot=self.oscilloscope.get_waveform(settings['channel'],plot_title)
        dc_waveform_plot_path=f"{unit_folder_path}/dc_waveform_plot(Vin={self.config['DUT']['input']['voltage']}V,Vout={settings['voltage']}V).png"
        dc_waveform_plot.savefig(dc_waveform_plot_path)
        dc_waveform_data_path=f"{unit_folder_path}/dc_waveform_data(Vin={self.config['DUT']['input']['voltage']}V,Vout={settings['voltage']}V).csv"
        data = zip(t_dc, w_dc)
        with open(dc_waveform_data_path, 'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(['Timestamp(s)', 'Voltage(V)'])
            csv_writer.writerows(data)

        vo_list, co_list, vi_list, ci_list,vpp_list = [], [], [], [],[]

        #DC tests
        print("sampling DC")
        for i in range (len(sample_points)):
            #Changing load
            self.load.set_mode('C',sample_points[i])
            time.sleep(2) #wait for value stablized    
            output_v=self.oscilloscope.get_measurement(2)
            #output_v=self.load.get_current_voltage()
            output_c=self.load.get_current_current()
            vpp=self.oscilloscope.get_measurement(3)
            input_status=self.power_supply.status_inquire()
            #input_v=input_status.get('ch1_out_voltage')
            input_v=self.oscilloscope.get_measurement(1)
            input_c=input_status.get('ch1_out_current')

            if(output_v<1000 and input_v<1000 and input_c!=0):
                vo_list.append(output_v)
                co_list.append(output_c)
                vi_list.append(input_v)
                ci_list.append(input_c)
            # Note: for debug
            print(f"input {input_v}V {input_c}A  output {output_v}V {output_c}A")
 
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
        efficiency_plot_path=f"{unit_folder_path}/efficiency_plot(Vin={self.config['DUT']['input']['voltage']}V,Vout={settings['voltage']}V).png"
        plt.savefig(efficiency_plot_path)
        efficiency_data_path = f"{unit_folder_path}/efficiency_data(Vin={self.config['DUT']['input']['voltage']}V,Vout={settings['voltage']}V).csv"
        data = zip(co_list, efficiency)
        with open(efficiency_data_path, 'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(['Load Current(A)', 'efficiency(%)'])
            csv_writer.writerows(data)

        #load regulation
        plt.figure(figsize=(10, 5))
        plt.plot(co_list, vo_list)
        plt.grid(True)
        title=f"Load regulation(Vin={self.config['DUT']['input']['voltage']}V,Vout={settings['voltage']}V)"
        plt.title(title)
        plt.ylim(settings['voltage']*0.95,settings['voltage']*1.05)
        plt.ylabel('Vout (V)')
        plt.xlabel('I_LOAD (A)')
        load_regulation_plot_path=f"{unit_folder_path}/load_regulation_plot(Vin={self.config['DUT']['input']['voltage']}V,Vout={settings['voltage']}V).png"
        plt.savefig(load_regulation_plot_path)
        load_rugulation_data_path = f"{unit_folder_path}/load_regulation_data(Vin={self.config['DUT']['input']['voltage']}V,Vout={settings['voltage']}V).csv"
        data = zip(co_list, vo_list)
        with open(load_rugulation_data_path, 'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(['Load Current(A)', 'Vout(V)'])
            csv_writer.writerows(data)


        #AC tests
        self.set_ac_test_mode(settings)
        ripple_folder_path=f"{unit_folder_path}/Ripple(Vin={self.config['DUT']['input']['voltage']}V,Vout={settings['voltage']}V)"
        os.makedirs(ripple_folder_path)
        
        load_list=[]
        print("sampling AC")
        for i in range (len(sample_points)):
            #Changing load
            self.load.set_mode('C',sample_points[i])
            time.sleep(2) #wait for value stablized
            #self.oscilloscope.auto_range_vertical(settings['channel'],'PK2PK')
            new_v_scale=self.oscilloscope.nearest_v_scale(self.oscilloscope.get_measurement(3)/2)
            current_v_scale=self.oscilloscope.get_y_scale(settings['channel'])
            while (current_v_scale!=new_v_scale):
                self.oscilloscope.set_y_scale(settings['channel'],new_v_scale)
                time.sleep(0.1)
                current_v_scale=new_v_scale
                new_v_scale=self.oscilloscope.nearest_v_scale(self.oscilloscope.get_measurement(3)/2)       
            #self.oscilloscope.auto_range_horizontal(settings['channel'])
            new_t_scale=self.oscilloscope.nearest_t_scale(1/self.oscilloscope.get_frequency(settings['channel']))
            current_t_scale=self.oscilloscope.get_t_scale()
            while (current_t_scale!=new_t_scale):
                self.oscilloscope.set_t_scale(new_t_scale)
                time.sleep(0.1)
                current_t_scale=new_t_scale
                new_t_scale=self.oscilloscope.nearest_t_scale(1/self.oscilloscope.get_frequency(settings['channel']))

            #output_v=self.oscilloscope.get_measurement(2)
            output_c=self.load.get_current_current()
            vpp=self.oscilloscope.get_measurement(3)      
            vpp_list.append(vpp)
            load_list.append(output_c)
            
            #ripple waveform
           
            plot_title=f"ripple waveform under output {output_c}A,Vpp={vpp}V from {settings['signal']} "
            w_ac,t_ac,wave_ac=self.oscilloscope.get_waveform(settings['channel'],plot_title)
            ripple_waveform_plot_path=f"{ripple_folder_path}/ripple_waveform_plot(load={output_c}A).png"
            wave_ac.savefig(ripple_waveform_plot_path)
            ripple_waveform_data_path=f"{ripple_folder_path}/ripple_waveform_data(load={output_c}A).csv"
            data = zip(t_ac, w_ac)
            with open(ripple_waveform_data_path, 'w', newline='') as csvfile:
                csv_writer = csv.writer(csvfile)
                csv_writer.writerow(['Timestamp(s)', 'Voltage(V)'])
                csv_writer.writerows(data)

            # Note: for debug
            print(f" {output_c}A {vpp}VPP")
        

        
        #Ripple PKPK
        plt.figure(figsize=(10, 5))
        plt.plot(co_list, vpp_list)
        plt.grid(True)
        plt.xscale(scale)
        title=f"Ripple PKPK(Vin={self.config['DUT']['input']['voltage']}V,Vout={settings['voltage']}V)"
        plt.title(title)
        plt.ylabel('Vout (V)')
        plt.xlabel('I_LOAD (A)')
        ripple_pkpk_plot_path=f"{unit_folder_path}/ripple_pkpk_plot(Vin={self.config['DUT']['input']['voltage']}V,Vout={settings['voltage']}V).png"
        plt.savefig(ripple_pkpk_plot_path)
        ripple_pkpk_data_path = f"{unit_folder_path}/ripple_pkpk_data(Vin={self.config['DUT']['input']['voltage']}V,Vout={settings['voltage']}V).csv"
        data = zip(load_list, vpp_list)
        with open(ripple_pkpk_data_path, 'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(['Load Current(A)', 'Vpp(V)'])
            csv_writer.writerows(data)
        
        '''
        All data
        '''
        all_data_path=f"{unit_folder_path}/all_data(Vin={self.config['DUT']['input']['voltage']}V,Vout={settings['voltage']}V).csv"
        data = zip(ci_list,vi_list,co_list, vo_list,vpp_list,load_list,vpp_list)
        with open(all_data_path, 'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(['Input Current(A)', 'Input Voltage(V)','Load Current(A)', 'Output Voltage(V)','Vpp(V)','Load Current(A)','Pk2Pk(V)'])
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

    
    def text_to_image(self,text):
        plt.figure()
        plt.text(0.5, 0.5, text, ha='center', va='center', fontsize=20)
        plt.axis('off')  # 关闭坐标轴
        return plt.gcf()

    
    def power_sequence_check(self,sequence_checks):
        '''
        sequence_chekcs[]
        [channel_in,V_in],
        [channel_o1,V_o1],
        ...
        '''
        
        self.power_supply.set_value(2,"V",0)
        self.power_supply.off()
        self.load.off()
        self.tb.set_channel(-1)
        sequence_folder_path=f"{self.folder_path}/power_sequence"
        os.mkdir(sequence_folder_path)
        #Get channels that need to be tested
        channel_list=[]
        for i,v,n in sequence_checks:
            self.oscilloscope.channel_on(i)
            self.oscilloscope.set_coupling(i,'DC')
            scale=self.oscilloscope.nearest_v_scale(v)
            self.oscilloscope.set_y_scale(i,scale)
            channel_list.append(i)
        channel_name = [n for _, _, n in sequence_checks]
        
        #Scale horizontal
        self.oscilloscope.set_t_scale(0.4)
        self.oscilloscope.write("HORIZONTAL:MAIN:DELAY:TIME 8e-1") 
        self.oscilloscope.write("TRIGger:A:MODe NORMAL")
        self.oscilloscope.write(f"TRIGGER:A:EDGE:SOURCE CH{sequence_checks[0][0]}" )  #input voltage as trigger
        self.oscilloscope.write(f"TRIGGER:A:LEVel {sequence_checks[0][1]*0.5}")   #50% level
                
        #ADD MEASUREMENTS FOR POWER ON TEST
        channel_num=len(channel_list)
        for i in range(channel_num):
            self.oscilloscope.add_measurement(i+1,channel_list[i],'RISe')
        for i in range(channel_num-1):
            self.oscilloscope.add_measurement(i+channel_num+1,channel_list[i+1],'DELay',channel_list[0]) 
            self.oscilloscope.write(f"MEASUrement:MEAS{i+channel_num+1}:DELay:EDGE{1} RISE")
            self.oscilloscope.write(f"MEASUrement:MEAS{i+channel_num+1}:DELay:EDGE{2} RISE")
        #POWER ON
        self.oscilloscope.write("TRIGGER:A:EDGE:SLOPE RISE") 
        self.oscilloscope.write("ACQuire:STOPAfter SEQUENCE")
        self.oscilloscope.write("ACQuire:STATE RUN")
        while( self.oscilloscope.query("TRIGGER:STATE?") != 'READY'):
            pass
        self.power_supply.on()
        time.sleep(5)
        rise_wave_list,rise_ts,rise_plot=self.oscilloscope.get_waveform_all()
        #Generate file
        rise_info='Power up\n'
        for i in range(channel_num):
            m=self.oscilloscope.get_measurement(i+1)
            print(f"meas{i+1},{m}")
            signal=sequence_checks[i][2]
            rise_info+=f"RISE TIME {signal}: {m}s\n"
        for i in range(channel_num-1):
            m=self.oscilloscope.get_measurement(i+channel_num+1)
            print(f"meas{i+channel_num+1},{m}")
            signal=sequence_checks[i+1][2]
            rise_info+= f"DELAY {signal}: {m}s\n"  
        rise_wave_path=f"{sequence_folder_path}/rise_waveform.csv"
        sequence_info_path=f"{sequence_folder_path}/powersequence.txt"
        data = zip(rise_ts,*[w[3] for w in rise_wave_list])
        with open(rise_wave_path, 'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(channel_name)
            csv_writer.writerows(data)
        with open(sequence_info_path, 'a') as file:
            file.write(rise_info)
               
         #ADD MEASUREMENTS FOR POWER OFF TEST
        channel_num=len(channel_list)
        for i in range(channel_num):
            self.oscilloscope.add_measurement(i+1,channel_list[i],'FALL')
        for i in range(channel_num-1):
            self.oscilloscope.add_measurement(i+channel_num+1,channel_list[i+1],'DELay',channel_list[0]) 
            self.oscilloscope.write(f"MEASUrement:MEAS{i+channel_num+1}:DELay:EDGE{1} FALL")
            self.oscilloscope.write(f"MEASUrement:MEAS{i+channel_num+1}:DELay:EDGE{2} FALL")
        #POWER OFF
        self.oscilloscope.write("TRIGGER:A:EDGE:SLOPE FALL") 
        #self.oscilloscope.write(f"TRIGGER:A:LEVel {self.config['DUT']['input']['voltage']*0.5}")
        self.oscilloscope.write("ACQuire:STOPAfter SEQUENCE")
        self.oscilloscope.write("ACQuire:STATE RUN")
        while( self.oscilloscope.query("TRIGGER:STATE?") != 'READY'):
            pass
        self.power_supply.off()
        time.sleep(5)
        fall_wave_list,fall_time,fall_plot=self.oscilloscope.get_waveform_all()
        #Generate file
        fall_info='Power off \n'
        for i in range(channel_num):
            m=self.oscilloscope.get_measurement(i+1)
            print(f"meas{i+1},{m}")
            signal=sequence_checks[i][2]
            fall_info+=f"FALL TIME {signal}: {m}s\n"
        for i in range(channel_num-1):
            m=self.oscilloscope.get_measurement(i+channel_num+1)
            print(f"meas{i+channel_num+1},{m}")
            signal=sequence_checks[i+1][2]
            fall_info+= f"DELAY {signal}: {m}s\n"
               
        fall_wave_path=f"{sequence_folder_path}/fall_waveform.csv"      
        data = zip(fall_time,*[w[3] for w in fall_wave_list])

        with open(fall_wave_path, 'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(channel_name)
            csv_writer.writerows(data)
        with open(sequence_info_path, 'a') as file:
            file.write(fall_info)
        #QUIT single mode
        self.oscilloscope.write("ACQuire:STATE RUN")
        self.oscilloscope.write("ACQuire:STOPAfter RUNSTOP")
        self.oscilloscope.write("TRIGger:A:MODe AUTO")

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
        print(f"******DC test mode for channel {channel}******")
        self.oscilloscope.set_acquire_mode('SAMple')
        self.oscilloscope.set_t_scale(0.002)
        self.oscilloscope.set_measurement_source(2,channel)
        for i in range(self.oscilloscope.get_channel_number()):
            s=self.oscilloscope.query(f"select:ch{i+1}?")
            if s=='1':              
                self.oscilloscope.set_coupling(i+1,'DC')
                self.oscilloscope.set_bandwidth(i+1,'FULl')
                self.oscilloscope.set_y_scale(i+1,10)
                time.sleep(0.1)
                self.oscilloscope.auto_range_vertical(i+1)

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
        self.tb.close()
        print("Test ended")

# In[ ]:
