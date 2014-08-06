"""
provides class objects and methods for working with instruments of
this experiment.
"""

# needed for various connections and operations
import serial, struct, gpib, numpy, re
import Silver.analysis as analysis

# basic class for storage; specialized by two other classes
class Storage:
    """
    class object for storing many instances of one stuff,
    for later averaging. In the context of the experiment, it really
    counts only as one.
    """
    def __init__(self, maxStored=0):
        """
        initializes the class; add initialization of self.data in
        subclasses
        """
        # if maxStored = 0, the class will store all added data. If set
        # to a positive integer, the class keeps only up to maxStored
        # number of sets (in FIFO style).
        self.maxStored = maxStored
        
    def mean(self, indices = None):
        """
        averages items in over indices given if no indices, averages all
        """

        # make sure that data is well-formed
        for j in range(len(self.data)-1):
            assert len(self.data[j]) == len(self.data[j+1])

        # populate indices, if not given:
        if (indices == None):
            indices = range(len(self.data[0]))
        
        # __average__() need to be defined in child classes
        # the child class also knows what needs to be averaged
        # and what needs to be sanity checked.
        return self.__average__(indices)
    
    def add(self, newdata):
        """
        adds an additional instance of the data.
        """
        # check whether we have too much data and remove the excess
        if self.maxStored > 0:
            n = len(self.data[0]) - self.maxStored
            if n >= 0:
                for j in range(len(self.data)):
                    tmp = self.data[j][n+1:]
                    self.data[j] = tmp
        # add the new data
        for j in range(len(self.data)):
            self.data[j].append(newdata[j])
    def num(self):
        return len(self.data[0])
    
    def clear(self):
        """
        clears the stored values, usually done when the values
        have been saved to a more permanent storage.
        """
        length = len(self.data)
        self.data = [[] for j in range(length)]
    
# special class for storing plots
class PlotStorage(Storage):
    """
    class object for storing plots
    """
    def __init__(self,chs,*args):
        apply(Storage.__init__,(self,) + args)
        self.data = [[],[]]
        self.chs = chs
    def __average__(self,indices):
        """
        averages the vector quantities
        """
        # first, do a sanity check on the X parameters
        for index in indices[1:]:
            # this assertion expects data to be a numpy array
            assert (self.data[0][0] == self.data[0][index]).all()
        # first, build the matrix of quantities to be averaged over
        tmp = [[] for j in range(4)]
        for ch in self.chs:
            for index in indices:
                tmp[ch-1].append(self.data[1][index][ch-1])
        # compute the average of dependent quantities, as well as the
        # standard deviation
        Y = [[[],[]] for j in range(4)]
        for ch in self.chs:
            Y[ch-1][0] = numpy.mean(tmp[ch-1],0)
            Y[ch-1][1] = numpy.std(tmp[ch-1],0)
        return (self.data[0][0], Y)
    
    def add(self,x,y):
        """
        adds an additional instance of the data.  x is a list variable
        containing the independent variable values and y is a list of
        list variables containing the dependent variables y is almost
        always 4-elements-long and may contain empty elements if not all
        channels are monitored.
        """
        # assert that independent variable is as long as each of the
        # dependent variables
        for ch in self.chs:
            assert len(x) == len(y[ch-1])
        apply(Storage.add, (self,[x,y]))

# special class for storing T and dens
class ParamStorage(Storage):
    """
    class object for storing parameters (T and dens)
    """
    def __init__(self, *args):
        apply(Storage.__init__,(self,)+args)
        self.data = [[], []]
    def clearAll(self):
        self.data = [[], []]
    def __average__(self,indices):
        """
        averages scalar quantities
        """
        # compute and return standard deviation, as well as the mean.
        result = [[numpy.mean(self.data[0]), numpy.std(self.data[0])],
                  [numpy.mean(self.data[1]), numpy.std(self.data[1])]]
        return result

# minimally history-aware implementation.
# to be used with simple uses of the scope.
# For performing computer-assisted averaging, use the ScopeAvg class.
class Scope(serial.Serial):
    """
    subclass of serial.Serial object for connecting to an oscilloscope;
    GDS and Tektronics commands implemented into purpose-driven functions.
    """
    def __init__(self, port='/dev/ttyUSB1', baudrate=19200,
                 model='TDS', chs=(1,2,3)):
        """
        makes the serial connection, but no checking is done.
        chs: a tuple of channels. default: (1,2,3)
        port: serial device. default: /dev/ttyUSB1
        model: specifies set of commands. TDS or GDS. default: TDS
        baudrate: same rate as the device is set at (matters only for TDS).
                  default: 19200, the fastest for TDS.
        """
        serial.Serial.__init__(self, port=port, baudrate=baudrate)
        self.model = model
        self.chs = chs
        self.seq = self.readSeq()
        # it should never take more than 5 seconds for any I/O
        self.setTimeout(5)
        # clear buffer in case of errors
        self.flushInput()
    
    def idn(self):
        """
        Check *IDN? response. Returns true if response is expected.
        """
        # clear buffer in case of errors
        self.flushInput()
        self.write('*IDN?\n')
        # can put the answer in the output buffer.
        answer = self.readline()

        if (re.match('GW,GDS-2204,', answer) != None) and \
                 (self.model == 'GDS'):
            return True
        elif (re.match('TEKTRONIX,TDS 2024,',answer) != None) and \
            (self.model == 'TDS'):
            return True
        else:
            return False
        # clear buffer in case of errors
        self.flushInput()
        
    def isUpdated(self):
        """
        checks whether the oscilloscope is updated.
        """
        seq = self.readSeq()

        if (seq != self.seq):
            self.seq = seq
            return True
        else:
            return False
        
    def readWaveform(self):
        """
        reads waveform,
        outputs calibrated time and data in a tuple
        """
        # prepare data holder
        y = [ 0 for j in range(4) ]
        # in case of previous errors
        self.flushInput()
        for ch in self.chs:
            # mostly for TDS
            self.setCh(ch)
            # calibration factor we will need soon
            (vmult, voff) = self.calibV()
            # read and calibrate data
            data = (numpy.array(self.readData()) - voff) * vmult
            # This is from the formula in TDS manual, without the
            # "vzero" in it---I couldn't figure out when that wouldn't
            # be exactly zero.
            y[ch-1]=data[:]

        (hstep, hoff) = self.calibH()
        # initialize time array
        t = numpy.array(range(len(y[0])))
        t = (t * hstep) + hoff

        # update the sequence number (... for isUpdated())
        self.seq = self.readSeq()

        return (t, y)
    
    def calibV(self):
        """
        return calibration factors for vertical scale
        """
        # clear buffer in case of errors
        self.flushInput()
        
        if (self.model == 'GDS'):
            self.write(':CHAN'+str(ch)+':SCAL?\n')
            # returns V/div, turn it into multiplicative factor
            # between digitizer and actual volts
            vmult = float(self.readline()) * 10./255.
            # GDS includes vertical offset in the data returned.
            voff = 0.
        elif (self.model == 'TDS'):
            self.write('WFMPre:YMUlt?\n')
            # formula I am using later is from TDS manual, so this
            # is straightforward.
            vmult = float(self.readline())
            self.write('WFMPre:YOFf?\n')
            voff = float(self.readline())
        
        # clear buffer in case of errors
        self.flushInput()

        return (vmult, voff)

    def calibH(self):
        """
        return calibration factors for horizontal scale
        """
        # in case of errors
        self.flushInput()
        if (self.model == 'GDS'):
            # GDS includes the sampling rate data with the waveform
            # data. hstep obtained later.
            self.write(':TIM:DEL?\n')
            # minus sign necessary to make hoff on two scopes congruous
            hoff = -float(self.readline())
        elif (self.model == 'TDS'):
            self.write('WFMPre:XZEro?\n')
            hoff = float(self.readline())
            self.write('WFMPre:XINcr?\n')
            hstep = float(self.readline())
        # in case of errors
        self.flushInput()
        return (hstep, hoff)
        
    def setCh(self, ch):
        """
        set channel for TDS, and ensure a bunch of options/modes for TDS
        this command does nothing for GDS, as these are specified in the
        command itself for GDS
        """
        if (self.model == 'TDS'):
            # according to the manual, RIBanary mode with 2-bit width is
            # the fastest mode for data transfer.
            # but I have to think 1-bit transfer ought to be faster.
            self.write('DATa:SOUrce CH'+str(ch)+
                       '; ENCdg RIBinary; STARt 1; STOP 2500; WIDth 1\n')
            # obtain vertical scale and offset (for calibration)
    def readData(self):
        """
        acquire waveform data; not calibrated
        """
        if (self.model == 'GDS'):
            self.write(':ACQ'+str(ch)+':MEM?\n')
        elif (self.model == 'TDS'):
            self.write('CURVe?\n')

        # Check for the initial '#'; if not present, raise error.
        if (self.read(1) != '#'):
            raise Exception, "Expected header not present"

        # Read the data length indicator
        dataSize = int(self.read(int(self.read(1))))

        # extra steps for GDS
        if (self.model == 'GDS'):
            # subtract the 8 bytes we will read.
            dataSize -= 8
            # Read the sampling period
            hstep = struct.unpack('>f', self.read(4))[0]
            # also, fix hoff so it corresponds with that for TDS
            # FIXME: check with the scope at some point.
            hoff = hoff - float(dataSize/4) * hstep
            # Read 4 bytes to advance to the actual data: first byte
            # contains the channel and the three are not used,
            # according to the GDS800 manual.
            self.read(4)
        
        # Read data; TDS expects a 1-byte data, GDS expects 2-byte one.
        if (self.model == 'TDS'):
            data = list(struct.unpack('>'+str(dataSize)+'b',
                                      self.read(dataSize)))
            # TDS has a trailing '\n' that should be drained.
            self.read(1)
        elif (self.model == 'GDS'):
            data = list(struct.unpack('>'+str(dataSize/2)+'h',
                                      self.read(dataSize)))

        return data

    def readSeq(self):
        """
        reads sequence number, for the purpose of checking whether scope
        trig'd.
        (GDS does not have a specific command for this; program
        something for it)
        """
        # clear buffer in case of errors
        self.flushInput()

        if (self.model == 'TDS'):
            self.write('ACQuire:NUMACq?\n')
            return int(self.readline())

        # clear buffer in case of errors
        self.flushInput()

    def readAvg(self):
        """
        reads the average number (i.e. the max number of plots the scope
        will average.
        """
        self.flushInput()

        if (self.model == 'TDS'):
            self.write('ACQuire:NUMAVg?\n')
            return int(self.readline())
        #elif (self.model == 'GDS'):
            # FIXME: I'll implement this later. I need to do some
            # testing, re: whether GDS returns the actual average
            # number, or log-base-2 of the average number.

# A class more or less operates independently (but be careful not to
# probe the device LakeShore thermometer is connected to, especially
# after it has been initialized).
#
# * it keeps the DMM running (to display density)
# * it can be used to update the global variables T and dens used in
#   the backend.

class DMM:
    def __init__(self, port='/dev/ttyUSB0', baudrate=1200,
                 calib=[-0.49125, 1.0613], Tident='LSCI,MODEL321', mode=0):
        """
        initialize device connections and set up variables and constants
        mode (0 = no change to DMM, 1 = update in torr, 2 = update in dens)
        """
        # for the baratron reading and updating display
        self.dmm = gpib.find('3478a')
        self.__bytes__ = 32
        # so that DMM knows to put something in the output buffer
        gpib.read(self.dmm, self.__bytes__)
        
        # for the temperature reading, many values hardcoded for
        # Lakeshore 321 cryogenic temperature sensor
        self.Tsensor = serial.Serial(port=port, baudrate=baudrate,
                                     bytesize = 7, parity = 'O')
        self.Tsensor.setTimeout(1)
        self.Tsensor.flushInput()
        self.Tsensor.write('*IDN?\n')
        answer = self.Tsensor.readline()

        if (re.match(Tident, answer) == None):
            raise Exception, "LS321 ident string not matched"
                
        # calibration factors consist of two numbers: voltage reading
        # at vacuum, and voltage reading at 1 atm.
        self.calib = calib
        self.mode = mode
        
        # some constants; declared here so that improved versions
        # of front-ends could modify them.
        self.atm = 760.0
        self.unit='TORR'
        self.pascalPerTorr = 133.322
        self.boltzmann = 1.38065e-23
        self.BGUnit='HE'
        
    def update(self):
        """
        updates the DMM;
        set the mode variable appropriately:
         0 = returns DMM to the local display (voltage)
         1 = DMM display in TORR
         2 = DMM display in buffer gas density
        """
        # read voltage
        self.V = float(gpib.read(self.dmm, self.__bytes__))
        self.torr = (self.V - self.calib[0])\
                    * (self.atm/(self.calib[1]-self.calib[0]))
        # read temperature
        self.Tsensor.write('CDAT?\n')
        self.T = float(self.Tsensor.readline())
        # calculate density. 100^3 necessary to bring the density to
        # 1/cm^3 that we are used to.
        self.dens = (self.torr * self.pascalPerTorr) / \
                    (1000000 * self.boltzmann * self.T)
        if self.mode == 2:
            gpib.write(self.dmm, "D2%.4E %s\r\n" % (self.dens,self.BGUnit))
        elif self.mode == 1:
            gpib.write(self.dmm, "D2%.5f %s\r\n" % (self.torr,self.unit))
        elif self.mode == 0:
            gpib.write(self.dmm, "D1\n")
