
from visa import *
import serial, re, numpy, time
print "NOTE: all inputs need to be mulitplied by 1000. eg. 0.388 => 0388."
pem=serial.Serial("Com4",2400)
pem.write("R\r\n")
time.sleep(.25)
val=pem.read(pem.inWaiting())
val1=re.sub("\*","",val)
val2=float(val1)
pem.write("R:%s\r\n" %(val2))
print "Retardation is currently set to %s" % val1

dmm  = instrument("GPIB::23")

def setR(Retar):
    pem.write("R:%s\r\n" %(Retar))

def peminfo():
    """gives current values of retardation, frequency 1 & 2, and wavelength"""
    pem.write("R\r\n")
    time.sleep(.25)
    num=pem.inWaiting()
    val=pem.read(num)
    val1=re.sub("\*","",val)
    print "Retardation is %s" % val1
    time.sleep(1)
    pem.write("1F\r\n")
    time.sleep(2)
    pem.read(pem.inWaiting())
    time.sleep(.5)
    pem.write("1F\r\n")
    time.sleep(2)
    num1=pem.inWaiting()
    f1val=pem.read(num1)
    f1val1=re.sub("\*","",f1val)
    f1=float(f1val1)
    print "1f frequency is %g" % (f1*0.001)
    time.sleep(1)
    pem.write("2F\r\n")
    time.sleep(2)
    pem.read(pem.inWaiting())
    time.sleep(.5)
    pem.write("2F\r\n")
    time.sleep(2)
    num2=pem.inWaiting()
    f2val=pem.read(num2)
    f2val1=re.sub("\*","",f2val)
    f2=float(f2val1)
    print "2f frequency is %s" % (f2*0.001)
    time.sleep(1.5)
    pem.write("W\r\n")
    time.sleep(.5)
    wnum=pem.inWaiting()
    wval=pem.read(wnum)
    wval1=re.sub("\*","",wval)
    print "Wavelength (nm) is %s" % wval1
    

def dmminfo():
    "Prints current display of Digital Multimeter."
    print dmm.ask_for_values("*IDN?")

def finder(Ret,outfile=None):
    """
    For an inputted value of Ret, the retardation, finder will keep reading the
    DMM output with time intervals set by u, putting each of those values into
    a list. When the user types 'stop', it will stop reading, and take the
    difference in the extreme values of the list, saving the result in an outfile
    with the associated retardation value.
    """
    #ALL INPUT VALUES SHOULD BE MULTIPLIED BY 1000. eg. 0.388 => 0388.
    Re=float(Ret)
    pem.write("R:%s\r\n" %Re)
    timeinput=raw_input("How much time?")
    T=float(timeinput)
    u=0.5
    i=0
    result=[]
    
    while i < (T/u):
        [d] = dmm.ask_for_values("*IDN?")
        result.append(d) 
        time.sleep(u)
        i+=1
        if i==(T/u):
            break
    #print result

    diff = max(result)-min(result)
    print ("Retardation, difference: %s, %s " % (Re, diff))
    if outfile is not None:
        try:
            fout=open(outfile, 'a')
            fout.write("%s, %s \n" % (Re, diff))
            fout.close()
        except:
            print("NOTE: failed to output")

        
#    control = True
#   while control:
#      userinput=raw_input("Type 'stop' to stop")
#        if userinput == "stop":
#            control = False
#        else:
#            d = dmm.ask_for_values("*IDN?")
#            result.append(d) 
#            time.sleep(u)
#    print result
