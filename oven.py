"""
Classes and functions for controlling the trash-can oven. Needs a
temperature controller for measuring the oven temperature and a DAQ for
sending +5V (min. +3V) signal to the oven heater relay.
"""
import re, threading, time, usb.core, usb.util, struct

# constants for USB-2001-TC
ID="TC"
IDVENDOR=0x09db
IDPRODUCT=0x00f9
# all control transfers are vendor transfers
CTRLOUT=64
CTRLIN=192
STR=0x80
RAW=0x81
BUFFERSIZE=64
# constants for type K (voltages are given in mV)
RANGES=(
    (-5.891,0.0),
    (0.0,20.644),
    (20.644,54.886));
COEFFS=(
    (0.0,25.173462,-1.1662878,-1.0833638,-8.9773540,
     -3.7342377,-8.6632643,-1.0450598,-5.1920577,0.0),
    (0.0,25.08355,0.07860106,-0.2503131,0.08315270,
     -0.01228034,0.0009804036,-0.00004413030,
     1.057734E-06,-1.052755E-08),
    (-131.8058,48.30222,-1.646031,0.05464731,-0.0009650715,
     8.802193E-06,-3.110810E-08,0.0,0.0,0.0));
# constants for SIIG USB hub
HUBVENDOR=0x2109
HUBPRODUCT=0x3431
HUB_REQUEST_TYPE=0x23
USB_PORT_FEAT_POWER=8
CLEAR_FEATURE=1
SET_FEATURE=3
PORT=1

class Oven:
    def __init__(self):
        """
        initialize device connections; define variables
        """
        # INITIALIZE USB-2001-TC thermocouple controller
        self.tc=usb.core.find(idVendor=IDVENDOR,idProduct=IDPRODUCT)
        self.tc.set_configuration()
        # set the sensor type to K
        self.tcLock=threading.Lock()
        self.tcWrite("AI{0}:SENSOR=TC/K")
        # INITIALIZE SIIG hub
        self.hub=usb.core.find(idVendor=HUBVENDOR,idProduct=HUBPRODUCT)
        # start out with relay turned off
        self.relayState=0
        self.hub.ctrl_transfer(HUB_REQUEST_TYPE,CLEAR_FEATURE,
                               USB_PORT_FEAT_POWER,PORT,"")
    def tcWrite(self,cmd,msgin=None):
        """
        write a command to USB-2001-TC and verify that it's been processed
        """
        self.tcLock.acquire()
        # write the command
        assert self.tc.ctrl_transfer(CTRLOUT,STR,0,0,cmd) == len(cmd)
        # if msgin (i.e. the expected response) is not None, then read a
        # message and verify that we get expected response back
        if msgin is not None:
            msg=self.tc.ctrl_transfer(CTRLIN,STR,0,0,BUFFERSIZE)
            assert msg[-1] == 0
            assert msgin == struct.pack("="+str(len(msg)-1)+"b",
                                        *msg[0:-1])
        self.tcLock.release()
    def tcRead(self,cmd):
        """
        write a command to USB-2001-TC and read a response
        """
        self.tcLock.acquire()
        # write the command
        assert self.tc.ctrl_transfer(CTRLOUT,STR,0,0,cmd) == len(cmd)
        msg=self.tc.ctrl_transfer(CTRLIN,STR,0,0,BUFFERSIZE)
        self.tcLock.release()
        return struct.pack("="+str(len(msg)-1)+"b",*msg[0:-1])
    def tcReadFloat(self,cmd):
        """
        write a command to USB-2001-TC and read a raw response that is a
        floading point number
        """
        self.tcLock.acquire()
        # write the command
        assert self.tc.ctrl_transfer(CTRLOUT,STR,0,0,cmd) == len(cmd)
        msg=self.tc.ctrl_transfer(CTRLIN,RAW,0,0,BUFFERSIZE)
        self.tcLock.release()
        return struct.unpack("=1f",msg)[0]
    def tcReadInt(self,cmd):
        """
        write a command to USB-2001-TC and read a raw response that is
        an unsigned integer
        """
        self.tcLock.acquire()
        # write the command
        assert self.tc.ctrl_transfer(CTRLOUT,STR,0,0,cmd) == len(cmd)
        msg=self.tc.ctrl_transfer(CTRLIN,RAW,0,0,BUFFERSIZE)
        self.tcLock.release()
        return struct.unpack("=1I",msg)[0]
    def getmV(self):
        """
        read voltage from temperature controller
        """
        # unscaled integer reading
        val=self.tcReadInt("?AI{0}:VALUE")-2**19
        # scale it to the actual mV scale
        scale=73.125/float(2**19)
        return val*scale        
    def getT(self):
        """
        read temperature and return it
        """
        # read the voltage 100 times and average
        self.mV=0.
        j=0
        while j < 100:
            try:
                self.mV+=self.getmV()
                j+=1
                time.sleep(0.01)
            except:
                # silently ignore; wait 100 mS, clear locks and retry
                time.sleep(0.1)
                self.tcLock.release()
        self.mV=self.mV/float(j)
        # determine the coefficients to use
        j=0
        while not (RANGES[j][0]<=self.mV and self.mV<=RANGES[j][1]):
            if j==len(RANGES)-1:
                break
            j+=1
        activeCoeffs=COEFFS[j]
        # calculate the delta T using the coefficients
        deltaT=0.
        for j in range(len(activeCoeffs)):
            deltaT+=activeCoeffs[j]*(self.mV**float(j))
        # get the cold junction temperature and add to get temperature in degC
        self.T=self.tcReadFloat("?AI{0}:CJC")+deltaT        
        return self.T        
    def onRelay(self):
        """
        turn the relay on
        """
        self.hub.ctrl_transfer(HUB_REQUEST_TYPE,SET_FEATURE,
                               USB_PORT_FEAT_POWER,PORT,"")
        self.relayState=1
    def offRelay(self):
        """
        turn the relay off
        """
        self.hub.ctrl_transfer(HUB_REQUEST_TYPE,CLEAR_FEATURE,
                               USB_PORT_FEAT_POWER,PORT,"")
        self.relayState=0
    def toggleRelay(self):
        """
        toggle relay; turn it off if it was on, turn it on if it was off.
        """
        if self.relayState == 0:
            self.onRelay()
        else:
            self.offRelay()
    
class OvenControl(threading.Thread):
    """
    This class controls oven temperature; supports ramping and
    maintaining the oven temperature at a setpoint.
    """
    def __init__(self,oven,outfile=None):
        self.outfile=outfile
        self.oven=oven
        # get the inital temperature and set the setpoint there
        self.setpoint=self.oven.getT()
        print("Setpoint: %g" % self.setpoint)
        # allow for +-1 deg variation
        self.deadband=0.5
        threading.Thread.__init__(self)
    def run(self):
        """
        continuously maintain setpoint once the thread starts;
        the rest of the task is handled by adjusting the setpoint
        """
        self.running=True
        while self.running:
            try:
                self.maintain_setpoint()
                if self.outfile is not None:
                    try:
                        # write out the temperature to a file
                        fout=open(self.outfile,'a')
                        fout.write("%d,%g,%g\n" % (time.time(),self.oven.T,self.setpoint))
                        fout.close()
                    except:
                        print("file output failed, trying to continue")
                time.sleep(1)
            except:
                print("maintaining setpoint failed, trying to continue (turning off oven for now)")
                self.oven.offRelay()
    def maintain_setpoint(self):
        """
        maintain the setpoint by deciding whether to toggle the relay state
        """
        # check the relay state and get comparison of current
        # temperature and the setpoint
        if self.oven.relayState==1:
            # relay is on, toggle if current temperature is too high
            if self.oven.getT() > self.setpoint+self.deadband:
                self.oven.toggleRelay()
        else:
            # relay is off, toggle if current temperature is too low
            if self.oven.getT() < self.setpoint-self.deadband:
                self.oven.toggleRelay()
    def ramp(self,target,duration):
        """
        change the setpoint slowly over time (in seconds) to ramp oven
        temperature
        """
        # make sure that thread is running to maintain setpoint
        assert self.isAlive()
        # set the initial setpoint to current temperature if the thread
        # is running to maintain setpoint, self.oven.T is a relatively
        # current temperature; use that instead
        self.setpoint=self.oven.T
        print("New setpoint: %g" % self.setpoint)
        print(time.ctime())
        # plan on changing the setpoint by 1 degree at a time
        diff=target-self.setpoint
        tdelta=float(duration)/abs(diff)
        # slowly change the setpoint; exit condition is given by sign of
        # target-self.setpoint changing (until that changes, the
        # quantity below should be a positive number)
        while diff*(target-self.setpoint) > 0:
            time.sleep(tdelta)
            self.setpoint+=1*diff/abs(diff)
            print("New setpoint: %g" % self.setpoint)
            print(time.ctime())
        # with the loop over, put the setpoint at the target, precisely
        self.setpoint=target
        print("Final setpoint: %g" % self.setpoint)
    def rampSeries(self,series):
        """
        program and run a series of ramps; series is a list of tuples,
        each tuple specifying the following: (target, duration, stay);
        target and duration are as defined in ramp, stay defines how
        long to stay at the target temperature before moving on to the
        next point in the series.        
        """
        print("Starting on ramp series with:\n")
        print(series)
        print(time.ctime())
        for point in series:
            print("Start ramp for: ")
            print(point)
            self.ramp(point[0],point[1])
            print("Ramp done; staying here for %d sec" % point[2])
            print(time.ctime())
            time.sleep(point[2])
        print("ramp series done; final setpoint: %g" % self.setpoint)
        print(time.ctime())
