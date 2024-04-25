#!/usr/bin/env python
# coding: utf-8

# In[1]:

#This is wriiten based on Tektronix DPO4000 series Digital Oscilloscopes

import matplotlib.pyplot as plt
import pyvisa as visa
import time
import numpy as np
from scipy.interpolate import interp1d

# class DPO4000Series(Oscilloscope):
#     def __init__(self, model):
#         super().__init__(model)
# 

# In[ ]:


class Oscilloscope:
    def __init__(self,oscilloscope_path,channel_num=4):
        self.scope = visa.ResourceManager().open_resource(oscilloscope_path)
        self.scope.write("*RST")
        self.scope.encoding = 'latin_1'
        self.scope.read_termination = '\n'
        self.scope.write_termination = None
        self.channel_number=channel_num
        print(f"{self.scope.query('*IDN?')} Connected")

    def query(self, command):
        return self.scope.query(command)

    def write(self, command):
        self.scope.write(command)
        
    def read(self, command):
        return self.scope.read(command)
    
    def autoset(self):
        self.write("AUTOset")
        
    def add_measurement(self,index,channel,TYPe):
        command = f"SELECT: CH{channel} ON"
        self.write(command)
        time.sleep(0.05)
        command = f"MEASUREMENT:MEAS{index}:SOURCE1 CH{channel}"
        #print(command)
        self.write(command)
        time.sleep(0.05)
        command = f"MEASUREMENT:MEAS{index}:TYPe {TYPe}"
        self.write(command)
        time.sleep(0.05)
        command = f"MEASUREMENT:MEAS{index}:STATE ON"
        self.write(command)
        time.sleep(0.05)
        
    def get_measurement(self,index):
        return float(self.query(f"MEASUREMENT:MEAS{index}:VALUE?"))
    
    def set_coupling(self,channel,mode):
        command = f"CH{channel}:COUPLING {mode.upper()}"
        self.write(command)

    def set_bandwidth(self,channel,mode):
        command = f"CH{channel}:BANDWIDTH {mode.upper()}"#{TWEnty|TWOfifty|FULl|<NR3>}
        self.write(command)
    #def get_immed_value(self,TYPe)
    
    def get_IDN(self):
        return self.query("*IDN?")
    
    def get_waveform(self,channel):
        command = f"DATA:SOURCE CH{channel}"
        self.write(command)
        self.write("DATA:ENCdg ASCII")
        bin_wave = self.scope.query_ascii_values('CURV?')
        # retrieve scaling factors
        tscale = float(self.query("WFMOUTPRE:XINcr?"))
        tstart = float(self.query('WFMOUTPRE:xzero?'))
        vscale = float(self.query('WFMOUTPRE:ymult?')) 
        voff = float(self.query('WFMOUTPRE:yzero?')) 
        vpos = float(self.query('WFMOUTPRE:yoff?')) 
        vunit=self.query("WFMOUTPRE:yunit?")
        tunit=self.query("WFMOUTPRE:xunit?")
        record = int(self.query('WFMOUTPRE:nr_pt?'))
        
        total_time=total_time = tscale * record
        tstop = tstart + total_time
        time_space=np.linspace(tstart,tstop,num=record,endpoint=False)
        unscaled_ts=time_space
        display_t_scale=float(self.query('HORIZONTAL:SCALE?'))
        display_t_scale,tunit,factor=self.convert_time_scale(display_t_scale)

        display_v_scale=float(self.query(f'CH{channel}:SCALE?'))
        display_v_scale,vunit,factor_v=self.convert_voltage_scale(display_v_scale)
        unscaled_wave = np.array(bin_wave, dtype='double')
        scaled_wave = (unscaled_wave - vpos) * vscale + voff
        time_space=time_space*factor 
        scaled_wave=scaled_wave*factor_v

        plt.figure(figsize=(10, 5))
        plt.xlim(min(time_space),max(time_space))
        plt.xticks(np.arange(min(time_space), max(time_space), display_t_scale))
        plt.ylim(-5*display_v_scale, 5*display_v_scale)
        plt.yticks(np.arange(-5*display_v_scale, 5*display_v_scale,display_v_scale))
        #print(-5*display_v_scale, 5*display_v_scale,display_v_scale)
        plt.grid(True)
        plt.plot(time_space,scaled_wave)
        plt.xlabel(tunit)
        plt.ylabel(vunit)
        plt.show()

    def get_waveform_data(self,channel):
        command = f"DATA:SOURCE CH{channel}"
        self.write(command)
        self.write("DATA:ENCdg ASCII")
        bin_wave = self.scope.query_ascii_values('CURV?')
        tscale = float(self.query("WFMOUTPRE:XINcr?"))
        tstart = float(self.query('WFMOUTPRE:xzero?'))
        vscale = float(self.query('WFMOUTPRE:ymult?')) 
        voff = float(self.query('WFMOUTPRE:yzero?')) 
        vpos = float(self.query('WFMOUTPRE:yoff?')) 
        record = int(self.query('WFMOUTPRE:nr_pt?'))
        
        total_time=total_time = tscale * record
        tstop = tstart + total_time
        time_space=np.linspace(tstart,tstop,num=record,endpoint=False)

        unscaled_wave = np.array(bin_wave, dtype='double')
        scaled_wave = (unscaled_wave - vpos) * vscale + voff
        return scaled_wave,time_space
    
    #FIXME not compledted
    def get_waveform_all(self):
        print("write this function!!!")
        self.write("DATA:ENCdg ASCII")
        wave_list=[]
        for i in range(self.channel_number):
            s=self.query(f"select:ch{i+1}?")
            if s=='1':
                wave_list.append(i)
        wave_data_list=[]
        for wave in wave_list:
            command = f"DATA:SOURCE CH{wave+1}"
            self.write(command)
            bin_wave = self.scope.query_ascii_values('CURV?')
            vscale = float(self.query('WFMOUTPRE:ymult?')) 
            vunit=self.query("WFMoutpre:yunit?")
            voff = float(self.query('wfmoutpre:yzero?')) # reference voltage
            vpos = float(self.query('WFMOUTPRE:yoff?')) # reference position (level)
            unscaled_wave = np.array(bin_wave, dtype='double')
            scaled_wave = (unscaled_wave - vpos) * vscale + voff
            wave_data_list.append((wave,bin_wave))

        tunit=self.query("WFMOUTPRE:xunit?")
        record = int(self.query('WFMOUTPRE:nr_pt?'))
              
        tscale = float(self.query("WFMOUTPRE:XINcr?"))
        tstart = float(self.query('WFMOUTPRE:xzero?'))
        total_time = tscale * record
        tstop = tstart + total_time
        time_space=np.linspace(tstart,tstop,num=record,endpoint=False)
        
        plt.grid(True)
        #plt.figure(figsize=(10, 5))#
        display_t_scale=float(self.query('HORIZONTAL:SCALE?'))
        display_t_scale,tunit,factor=self.convert_time_scale(display_t_scale)     
        time_space=time_space*factor 
        for wave,bin_wave in wave_data_list:
            l=f"CH{wave+1}"
            plt.plot(time_space,bin_wave,label=l)
        plt.xlabel(tunit)
        plt.ylabel(vunit)
        #plt.ylim(-5*display_v_scale, 5*display_v_scale)
        #plt.yticks(np.arange(-5*display_v_scale, 5*display_v_scale,display_v_scale))
        plt.legend()
        plt.show()

    def auto_y_scale(self,channel):       
        self.write(f':MEASUREMENT:IMMed:SOURCE CH{channel}')
        self.write( ':MEASUREMENT:IMMed:TYPE HIGH')
        valid=False
        t_scale=float(self.query("HORizontal:SCAle?"))
        while not valid:
            current_scale=self.query(f'CH{channel}:SCALE?')
            current_scale_value=float(current_scale)
            value=float(self.query(':MEASUREMENT:Immed:vALUE?'))
            mul=0
            div=0
            new_scale=0.
            
            if(int(current_scale[0])==1):
                mul=2
                div=2
            elif(int(current_scale[0])==2):
                mul=2.5
                div=2
            else:
                mul=2
                div=2.5
            if value>1000 :
                new_scale=current_scale_value*mul               
                self.write(f'CH{channel}:SCALE {new_scale}') 
                time.sleep(1)
            elif value/current_scale_value<0.2:
                new_scale=current_scale_value/10
                if new_scale<0.01:
                    valid=True
                else:
                    self.write(f'CH{channel}:SCALE {new_scale}')  
            elif value/current_scale_value>5:
                new_scale=current_scale_value*mul
                if new_scale<0.01:
                    valid=True
                else:
                    self.write(f'CH{channel}:SCALE {new_scale}')  
            elif value/current_scale_value<1:
                new_scale=current_scale_value/div
                if new_scale<0.01:
                    valid=True
                else:
                    self.write(f'CH{channel}:SCALE {new_scale}')  
            elif value/current_scale_value<1.8:
                new_scale=current_scale_value/div
                if new_scale<0.01:
                    valid=True
                else:
                    self.write(f'CH{channel}:SCALE {new_scale}')  
            else:
                valid=True

            if new_scale==0.01:
                valid=True
            if value==0:
                valid=True   
            time.sleep(15*t_scale) 
        time.sleep(1)

    def set_y_scale(self,channel,value):
        self.write(f'CH{channel}:SCALE {value}') 
    
    def set_offset(self,channel,value):
        self.write(f'CH{channel}:OFFSET {value}') 

    def auto_t_scale(self,channel):
        self.write(f':MEASUREMENT:IMMed:SOURCE CH{channel}')
        self.write( ':MEASUREMENT:IMMed:TYPE PERIOD')
        valid=False
        while not valid:
            current_scale=self.query("HORizontal:SCAle?")
            current_scale_value=float(current_scale)
            value=float(self.query(':MEASUREMENT:Immed:VALUE?'))
            mul=1
            div=1
            if(int(current_scale[0])==1):
                mul=2
                div=2.5
            elif(int(current_scale[0])==2):
                mul=2
                div=2
            elif(int(current_scale[0])==4):
                mul=2.5
                div=2
            else:
                mul=10
                div=10
            new_scale=0
            if value>1000 :
                new_scale=current_scale_value*mul               
                self.write(f'HORizontal:SCALE {new_scale}') 
                time.sleep(0.3)
            elif value<1E-6:
                #new_scale=current_scale_value*mul      
                self.write(f'HORizontal:SCALE 1E-3') 
            elif value/current_scale_value>5:
                new_scale=current_scale_value*mul
                self.write(f'HORizontal:SCALE {new_scale}')                  
            elif value/current_scale_value<1:
                new_scale=current_scale_value/div
                self.write(f'HORizontal:SCALE {new_scale}')             
            elif value/current_scale_value<1.8:
                new_scale=current_scale_value/div
                self.write(f'HORizontal:SCALE {new_scale}')                   
            else:
                valid=True
            time.sleep(10*new_scale)
        time.sleep(1)

    def set_t_scale(self,new_scale):
        self.write(f'HORizontal:SCALE {new_scale}') 

    def auto_scale(self,channel,init=True,t_scale=0.1,v_scale=10):   
            if init: 
                self.write(f'HORizontal:SCALE {t_scale}')   
                time.sleep(5*t_scale)          
                self.write(f'CH{channel}:SCALE {v_scale}') 
            #time.sleep(1)
            self.auto_y_scale(channel)   
            self.auto_t_scale(channel)
            self.auto_y_scale(channel) 

    def get_frequency(self,channel,fft=False,fig=False):
        #print("take 5 average!")
        if not fft:
            for i in range(5):
                fre=list()
                self.write(f"MEASUrement:IMMed:SOURCE CH{channel}")
                self.write(f"MEASUrement:IMMed:TYPE FREQUENCY")
                fre.append(float(self.query("MEASUrement:IMMed:VALUE?")))
                #time.sleep(0.1)
            return np.average(fre)
        
        else:
            wave,t=self.get_waveform_data(channel)
            tscale = float(self.query("WFMoutpre:XINcr?"))
            tstart = float(self.query('WFMoutpre:xzero?'))
            vscale = float(self.query('WFMoutpre:ymult?')) 
            voff = float(self.query('WFMoutpre:yzero?')) 
            vpos = float(self.query('WFMoutpre:yoff?')) 
            vunit=self.query("WFMoutpre:yunit?")
            tunit=self.query("WFMoutpre:xunit?")
            record = int(self.query('WFMoutpre:nr_pt?'))
                        
            total_time=total_time = tscale * record
            tstop = tstart + total_time
            time_space=np.linspace(tstart,tstop,num=record,endpoint=False)
                
            # fft
            fft_result = np.fft.fft(wave)
            freqs = np.fft.fftfreq(len(wave), tscale)
            n=len(wave)
            main_freq_index = np.argmax(np.abs(fft_result))
            interp_func = interp1d(range(len(wave)), freqs)
            main_freq = interp_func(main_freq_index)
            print("Main Frequency:", main_freq)
            # find main frequency

            print("frequency",abs(main_freq))
            #print(f"FREQUENCY{ self.conver_freq_scale(abs(main_freq))}=={abs(main_freq)}")
            if fig:
                # draw spectrum
                plt.figure(figsize=(10, 5))
                plt.plot(freqs[:len(freqs)//2], np.abs(fft_result)[:len(freqs)//2])
                plt.xlabel('Frequency (Hz)')
                plt.ylabel('Magnitude')
                plt.title('Frequency Spectrum ')
                plt.xscale('log')  
                plt.yscale('log')  
                plt.xlim(0, main_freq*1000)  
                plt.grid(True)
                plt.show()
            return abs(main_freq) 

    def convert_time_scale(self,scale):
        if  scale >= 1e-3:
            return scale, 's',1
        elif scale >= 1e-5:
            return scale * 1e3, 'ms',1e3
        else:
            return scale * 1e6, 'us',1e6
    def convert_voltage_scale(self,scale):
        if  scale >= 1e-2:
            return scale, 'V',1
        elif scale >= 1e-5:
            return scale * 1e3, 'mV',1e3
        else:
            return scale * 1e6, 'uV',1e6
    def conver_freq_scale(self,freq):
        if freq>1E6:
            return freq/1000000.00,'MHz'
        elif freq>1E3:
            return freq/1000.00,'KHz'
        else:
            return freq,"Hz"
    
    def measure_ripple(self,channel,window_size=None):
        if window_size==None:
            window_size = int(200/len(str(int(self.get_frequency(3,False)))))
        bin_wave,t=self.get_waveform_data(channel)
        smooth_bin_wave = np.convolve(bin_wave, np.ones(window_size)/window_size, mode='same')
        smooth_max = np.max(smooth_bin_wave)
        smooth_min = np.min(smooth_bin_wave)
        vpp = smooth_max - smooth_min
        print(f"Vpp：{vpp:.2f}V")     

        plt.figure(figsize=(10, 5))
        plt.plot(t, bin_wave, label='Original Signal')
        plt.plot(t, smooth_bin_wave, label='Filtered Signal')
        plt.xlabel('Time')
        plt.ylabel('Amplitude')
        plt.title('Original vs Smoothed Signal')
        plt.legend()
        plt.grid(True)
              
        plt.hlines([smooth_max, smooth_min], t[0], t[-1], colors='r', linestyles='dashed')
        plt.annotate(f'{smooth_max:.4f}V', (t[len(t)//2], smooth_max), textcoords="offset points", xytext=(0,10), ha='center', fontsize=8, color='r')
        plt.annotate(f'{smooth_min:.4f}V', (t[len(t)//2], smooth_min), textcoords="offset points", xytext=(0,0), ha='center', fontsize=8, color='r')
        plt.show()
        return vpp
    def channel_on(self,channel):
       self.write(f"SELECT:CH{channel} ON")    
    def channel_off(self,channel):
       self.write(f"SELECT:CH{channel} OFF")    

    def get_channel_number():
        return 4
# %%

