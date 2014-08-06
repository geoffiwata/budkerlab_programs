import time
import os
from numpy import arcsin,cos,sqrt,pi

from visa import *
"""
/use this program to get all data from the modulation scheme: i.e. first and
second harmonics. Note that the time constant of second lockin (10s) limits the
accuracy of the measurement you will take here
"""
lockin = instrument("GPIB::12")
lockin2 = instrument("GPIB::13")
#lockin2 is the borrowed lockinamplifier

dmm  = instrument("GPIB::23")

def lockin1info():
    "Gives the current values displayed on screen, as well as the X and Y magnitudes."
    print lockin.ask("*IDN?")
    print lockin.ask_for_values("XY.")

def lockin2info():
    "Gives the current values displayed on screen, as well as the X and Y magnitudes."
    print lockin2.ask("*IDN?")
    print lockin2.ask_for_values("XY.")

def dmminfo():
    "Prints current display of Digital Multimeter."
    print dmm.ask_for_values("*IDN?")

def harmonic(a):
    "Switches the harmonic of the Lock-in to inputted value for a."
    lockin.write("REFN %d" % a )   
    lockin.write("AQN")
    print  'Current harmonic is', a
    
def getvalue(outfile=None):
    #lockin.write("REFN 2")
    (x2,y2) = lockin2.ask_for_values("XY.")
    (mag) = lockin2.ask_for_values("MAG.")
    os.chdir("C:\lockindata")
    tester = outfile
    if outfile is not None:
        try:
            #write out the values to a file
            fout=open("%sr_2.txt" % (tester),'a')
            fout.write('%s\n' % (mag))
            fout.close()
        except:
            print("FILE OUTPUT FAILED, trying to continue")
        try:
            #write out the values to a file
            fout=open("%sxy_2.txt" % (tester),'a')
            fout.write('%s,%s\n' % (x2,y2))
            fout.close()
        except:
            print("FILE OUTPUT FAILED, trying to continue")
    print("Harmonic 2 Magnitude: %s" % (mag))
#now switch to first harmonic
    lockin.write("REFN 1")
    time.sleep(10)
    (x2,y2) = lockin2.ask_for_values("XY.")
    (mag) = lockin2.ask_for_values("MAG.")
    os.chdir("C:\lockindata")
    tester = outfile
    if outfile is not None:
        try:
            #write out the values to a file
            fout=open("%sr_1.txt" % (tester),'a')
            fout.write('%s\n' % (mag))
            fout.close()
        except:
            print("FILE OUTPUT FAILED, trying to continue")
        try:
            #write out the values to a file
            fout=open("%sxy_1.txt" % (tester),'a')
            fout.write('%s,%s\n' % (x2,y2))
            fout.close()
        except:
            print("FILE OUTPUT FAILED, trying to continue")
    print("Harmonic 1 Magnitude: %s" % (mag))
    lockin.write("REFN 2")
          

def getvalues(outfile=None, sec = .5):
    """
Repeats the get value scheme to get the diff. every second.
"""
    
    control = True
    while control:
        out=outfile
        getvalue(out)    
        time.sleep(sec)
