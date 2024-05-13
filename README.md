# pyvisa-automation-test
This is for automating DC power converter test using pyvisa and serial communication.  


# How to Use  
    
```python
from PSUTester import *
p=PSUTester('information about your DUT.yaml')
#Test flow
p.test_flow()
```  

# Test content   
 ## I/O  
 - Efficiency  
 - Load regulation  
 ## DC  
 - DC output waveform  
## Ripple
 - Ripple pkpk  
 - Ripple waveform

## For several PSU
 - If needed，Power on/off Sequence  

# What was get
## Folder "DUT Name Test Time"
 - efficiency_plot(png),efficiency_data(csv)  
 - load_regulation_plot(png),load_rugulation_data(csv)
 - ripple_pkpk_plot(png),ripple_pkpk_data(csv)
 - all(ci,vi,co,vo,vout_pkpk)(csv)
 - dc_waveform_plot(png), dc_waveform_data(csv)
 - Folder "Ripple"
      - ripple_waveform(png),ripple_waveform_data(csv)
      - xN(N = samle number)

# The configure template  (.yaml)
```yaml
test_configuration: 
  default:
    min_load:  # ratio to max load
    max_load:  #ratio to max load
    sample_num:  # sample points between min/max load
    sample_scale:  # [linear,log]
test_instrument:
  oscilloscope: 
    path: 
  load:
    path: 
  power_supply: 
    path: 
DUT:
  device_name: 
  input: 
    signal:   
    voltage:      #V
    current:  #A max
    channel: 
  output: #3 at most
    1:
      signal:  
      voltage: 
      channel: 
      max_load: 
      sequence_check: #true/false
    #2:   
    #3:
testboard:
  voltage_supply:  #V
  current_supply:  #A maximum
```  


# Test instrument
**Oscilloscope**  Tekronix DPO400 Series, 4channel, VISA supported      
**DCPowerSupply**  PeakTech 6705, Serial Communication      
**ElectronicLoad**  Tenma 72 13210, VISA supported  