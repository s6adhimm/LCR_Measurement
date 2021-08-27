import numpy as np
import tables as tb
import logging
from tqdm import tqdm
import matplotlib.pyplot as plt
import time
#import glob

from basil.dut import Dut
# from basil.TL.Visa import visa
import visa as vs
########################################################
###############SETTINGS#################################
sample_type='To be deleted'
sample_description='_1000V_bias_box_NW_Sg_Px_to_GND_backside_biasing'

voltage_start=0
voltageR = -290     #Voltage sweep will be performed from voltage_start to voltageR
delta_V= 1
datapoints_per_voltage=1
ACV = '30 MV' #V_pp of test signal
waiting_time=1  # Time between voltage measurements                                            
settling_time=1   # Time between voltage change and start of voltage measurements
frequency=[1e4]
output_filename = sample_type + sample_description + '_V_range_%s_ACV_%s_settling_time_%s_frequency_%s_to_%s' % \
    (voltageR,ACV,settling_time,frequency[0],frequency[-1])
########################################################



# --- functions ---
def TriggerMode(s):
    LCR.write('TRIG:SOUR '+s)
def SetACV(v):
    print LCR.write('VOLT '+v)
def GetFreq():
    freq = LCR.query('FREQ?')
    freq=float(freq)
    return freq
def GetValue():
    val = LCR.query('FETC?')
    return val
def MeasureCp(times=5):
    val_R = []
    val_C=[]
    val_V=[]
    val_I=[]
    for i in range(times):
        time.sleep(waiting_time)
        LCR.write('TRIG')
        SetMeasQuant('CPRP')
        res_I= float(dut['BIAS'].get_current().split(',')[1])
        time.sleep(0.5)
        res_V=float(dut['BIAS'].get_voltage().split(',')[0])
        res=GetValue()
        res_C = float(res.split(',')[0])
        res_R = float(res.split(',')[1])
        val_C.append(res_C)
        val_R.append(res_R)
        freq=GetFreq()
        val_V.append(res_V)
        val_I.append(res_I)
        print "CP",res_C,"R",res_R,"f",freq,"V", res_V, "I", res_I
    return np.mean(val_C), np.std(val_C), np.mean(val_R), np.std(val_R), np.mean(val_I), np.std(val_I), np.mean(val_V), np.std(val_V) 
def MeasureZTD(times=5):
    val1 = []
    val2 = []
    for i in range(times):
        LCR.write('TRIG')
        SetMeasQuant('ZTD')
        time.sleep(3)
        res=GetValue()
        z = float(res.split(',')[0])
        t = float(res.split(',')[1])
        val1.append(z)
        val2.append(t)
        freq=GetFreq()
        print('Z-Theta (Deg): ', z,t)
    return np.mean(val1), np.std(val1),np.mean(val2),np.std(val2)
def MeasureX(times=5):
    val = []
    for i in range(times):
        LCR.write('TRIG')
        SetMeasQuant('RX')
        time.sleep(3)
        res=GetValue()
        res = float(res.split(',')[0])
        val.append(res)
        freq=GetFreq()
        print("X: ",res)
    return np.mean(val), np.std(val)

def SetMeasQuant(s):
    LCR.write('FUNC:IMP '+s)
def SetFrequency(f):
    LCR.write('FREQ '+ repr(f) +'HZ')
def Name():
    print(LCR.query('*IDN?'))
def OpenCorrection():
    LCR.write('CORR:OPEN')
def ShortCorrection():
    LCR.write('CORR:SHOR')

def cooldown(cooldown_time=180, bias_off=True):
    print 'Cooldown has been activated'
    print 'Decrease ACV'
    SetACV('MIN')
    #get current voltage:
    V_now=float(dut['BIAS'].get_voltage().split(',')[0])
    V_cooldown_array=np.linspace(V_now,0,cooldown_time)
    for v_i in tqdm(V_cooldown_array):
        dut['BIAS'].set_voltage(v_i)
        print 'new voltage:', v_i
        time.sleep(1)
    V_now=float(dut['BIAS'].get_voltage().split(',')[0])
    if np.abs(V_now)>1:
        print ('repeat cooldown')
        cooldown(bias_off=False)
    if bias_off:
        dut['BIAS'].off()
        print 'cooldown is done'

    

def MeasCVF():
    ##### Few helper arrays for a monitoring plot...

#initialise the figure:
    #initialise Basil
    global dut 
    dut= Dut('DIO.yaml')
    dut.init()
    logging.info('Initialized SMU: %s' % dut['BIAS'].get_name())
    #Open a pyvisa entity for the LCR meter
    rm = vs.ResourceManager()
    print(rm.list_resources())
    global LCR 
    LCR = rm.open_resource('GPIB0::17::INSTR')

    if voltageR > 0:
        logging.info("please check again the Bias voltage range")
        raise
    BIA = np.linspace(voltage_start,voltageR,int(np.abs(voltageR)/delta_V+1))
    #include a customary range with bias voltages here:
    #BIA=np.array([0,-0.001,-0.01,-0.05,-0.2,-0.3,-5e-1,-0.7,-1,-2,-5,-10,-20,-25,-30])
    FREQ=frequency

    dut['BIAS'].on()
    TriggerMode('HOLD')
    SetACV(ACV)
    """
    #warmup
    print 'Raise bias until ', BIA[-1], 'V is reached'
    for v in tqdm(np.linspace(0.,BIA[-1],(BIA[-1]/5+1))):
        print 'current voltage:', v
        dut['BIAS'].set_voltage(v)
        time.sleep(10)

    """
    # for i in range(5):
    #     LCR.write('TRIG')
    #     SetMeasQuant('ZTD')
    #     time.sleep(3)
    #     res=GetValue()
    #     print(res.split(','))
    acv = ACV[:-3:]+'mV'
    #create h5 file to save the data:
    # description = np.dtype([('Voltage',np.float),('Frequency',np.float),('Cp',np.float),('Cp_STAerr',np.float),("X",np.float),('Xerr',np.float),("Z",np.float),("Zerr",np.float),("TH",np.float),("THerr",np.float)])
    description = np.dtype([('Voltage',np.float),('Voltage_measured',np.float),('Voltage_measured_err',np.float),('Current',np.float),('Current_err',np.float),('Frequency',np.float),\
        ('Cp',np.float),('Cp_STAerr',np.float), ('Rp', np.float),('Rp_STAerr', np.float)])
    plt.figure(1)
    helper_V=np.array([])
    helper_Cp=np.array([])
    helper_Cp_err=np.array([])
    with tb.open_file('./data/CVF' + output_filename + '_ACV' +\
         acv + '_DCV' + repr(voltageR) + '.h5', mode='w') as h5_file:
        #append data to helper arrays for plotting:
        data = h5_file.create_table(h5_file.root, name='CVF_data',\
             description=description, title='Data C-V-f')
        print 'applied voltages:\n', BIA
        time.sleep(5)
        for v in tqdm(BIA):
            try:  
                dut['BIAS'].set_voltage(v)

                time.sleep(settling_time)
                for f in FREQ:
                    SetFrequency(f)
                    time.sleep(waiting_time)
                    cp, cp_err, Rp, Rp_err, I, I_err, V_meas, V_meas_err = MeasureCp(datapoints_per_voltage)
                    # time.sleep(1)
                    # x, x_err = MeasureX(5)
                    # time.sleep(1)
                    # z,z_err,th,th_err = MeasureZTD(5)
                    fr = GetFreq()
                    data.row['Voltage'] = v
                    data.row['Voltage_measured']=V_meas
                    data.row['Voltage_measured_err']=V_meas_err
                    data.row['Current']=I
                    data.row['Current_err']=I_err
                    data.row['Frequency']=fr
                    data.row['Cp'] = cp
                    data.row['Cp_STAerr'] = cp_err
                    data.row['Rp'] = Rp
                    data.row['Rp_STAerr'] = Rp_err


                    helper_V=np.append(helper_V,v)
                    helper_Cp=np.append(helper_Cp, cp)
                    helper_Cp_err=np.append(helper_Cp_err,cp_err)
                    #refresh plot:
                    #plt.errorbar(x=helper_V,y=helper_Cp, xerr=helper_Cp_err, color='blue')
                    #plt.show(block=False)
                    plt.xlabel('Bias Voltage / V')
                    plt.ylabel('$C_p$ / pF')
                    # data.row['X'] = x
                    # data.row['Xerr'] = x_err
                    # data.row['Z'] = z
                    # data.row['Zerr'] = z_err
                    # data.row['TH'] = th
                    # data.row['THerr'] = th_err
                    data.row.append()
                    data.flush()
                    # print('C_p:',cp,'; err:', cp_err,'; X:',x,'; err:', x_err,'; Z:',z,'; err:', z_err,'; TH:',th,'; err:', th_err,'; Frequency:',fr,'; Voltage: ', v)
                    print('C_p:',cp,'; err:', cp_err,'; Frequency:',fr,'; Voltage: ', v, 'Current:', I)
            except KeyboardInterrupt:
                cooldown(5)
                break
    time.sleep(0.5)
    try:
        cooldown(180)
    except Exception:
        pass
    plt.scatter(helper_V,helper_Cp**(-2))
    plt.show()
    #Perform a cooldown to protect the sensor
    """
    print 'cooldown'
    for v in np.linspace(BIA[-1],0.,30):
        dut['BIAS'].set_voltage(v)
        print 'current voltage:', v
        time.sleep(1)
    """
    dut['BIAS'].off()
    SetACV('MIN')

MeasCVF()
