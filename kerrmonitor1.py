import time
import os
from numpy import arcsin,cos,sqrt,pi

from visa import *

lockin = instrument("GPIB::12")
#lockin2 is the borrowed lockinamplifier

dmm  = instrument("GPIB::23")

def lockin1info():
    "Gives the current values displayed on screen, as well as the X and Y magnitudes."
    print lockin.ask("*IDN?")
    print lockin.ask_for_values("XY.")

def lockin1phase():
    "Autophases lockin 1"
    lockin.write("AQN")
    print ('lockin.write(AQN)')

def dmminfo():
    "Prints current display of Digital Multimeter."
    print dmm.ask_for_values("*IDN?")

def harmonic(a):
    "Switches the harmonic of the Lock-in to inputted value for a."
    lockin.write("REFN %d" % a )   
    lockin.write("AQN")
    print  'Current harmonic is', a
    

def polarization(outfile=None):
    """
    Measures both X, Y in both harmonics, and DC voltage,
    and calculates the ellipticity(radians) in the light.
    If conditions of y < 10% of x, magnitude is used to
    calculate ellipticity.
    Both ellipticity and azimuth are written to file.
    """

    (z,)= dmm.ask_for_values("*IDN?")
    (u,)= lockin.ask_for_values("TC.")
#1st harmonic on fist lockin
    lockin.write("REFN 1")
    lockin.write("AQN")
    time.sleep(u)#wait before measuring
    (x,y)= lockin.ask_for_values("XY.")
#    print "(x,y)=(%g,%g)" % (x,y)
    i=0
#    print u
    #checking condition
    while abs(y) > (abs(x) * 0.01):
        lockin.write("AQN")
        time.sleep(u);
        (x,y)= lockin.ask_for_values("XY.")
        i+=1; 
#        print "(x,y)=(%g,%g)" % (x,y)
        if i > 10:
#            print "Warning: phase may be incorrect."
            (m,)= (lockin.ask_for_values("MAG."))
            mag = m*abs(x)/(x)
#            print "Magnitude of 1st Harmonic = (%g)" % (m)
            break
    time.sleep(u*100) #wait to switch between harmonics.


#2nd harmonic on first lockin
    lockin.write("REFN 2")
    time.sleep(u) #wait to switch between harmonics.    
    lockin.write("AQN")
    (v,w)= lockin.ask_for_values("XY.")
    v1 = v
#    print "(v,w)=(%g,%g)" % (v,w)
    i=0
    while abs(w) > (abs(v) * 0.01):
        lockin.write("AQN")
        time.sleep(u);
#        print "(v,w)=(%g,%g)" % (v,w)
        i+=1;
        if i > 10:
#            print "Warning: phase may be incorrect."
            (n,) = lockin.ask_for_values("MAG.")
            nag = (n*abs(v)/(v))
            #0.8472 is conversion factor to account for gain piqueing
#            print "Magnitude of 2st Harmonic on fist lockin= (%g)" % (n)
            break

        
#    print "DC voltage 1 is ", (z)
#    print "DC voltage 2 is ", (d)
    if abs(y) < (abs(x) * 0.01):
        e1 = 0.5*arcsin((abs(x))/(abs(z)*(0.519147*sqrt(2))))
    else:
        e1 = 0.5*arcsin((abs(mag)/abs(z))/(0.519147*sqrt(2)))
#        print "Magnitude used to calculate the following"
#l = abs((nag)/(cos(2. * e1)*z*(0.431755*sqrt(2))))

#    if l < 1.0:
    if abs(w) < (abs(v) * 0.01):
        b1 = 0.5*arcsin((v)/(cos(2. * e1)*z*(0.431755*sqrt(2))))
    else:
        b1 = 0.5*arcsin((nag)/(cos(2. * e1)*z*(0.431755*sqrt(2))))
#    else:
#        b1 = .785398
#        print "magnitude used to calculate"
    
    #(azi,) = pi/4.
    #lockin.write("REFN 1")
    #lockin.write("AQN")
    tester=outfile
    ellip = str(e1)
    os.chdir("C:\lockindata")
    #sets directory
    if outfile is not None:
        try:
            #write out the values to a txt file
            fout = open("%s.txt" % (tester), 'a')
            fout.write('%s\n ' % (ellip))
            fout.close()
        except:
            print("FILE OUTPUT FAILED, trying to continue")
    lockin.write("REFN 1")   
    lockin.write("AQN")
    print "(ellipticity, azimuth) = (%g,%g)" % (e1, b1)
#    print "(ellipticity1, ellipticity2, azimuth1, azimuth2)"
#    return (e1, e2, b1, b2)1

def findaxis(outfile=None):
    """
Repeats the polarization scheme to get the diff. every second. Can be used to
find the axis on the lambda/2 plate that crosses the polarization with the axis
of the polarizer after the PEM.
"""

    control = True
    while control:
        #userinput=raw_input("Type 'stop' to stop")
        #if userinput == "stop":
        #    control = False
        #else: polarization()
        out=outfile
        polarization(out)    
        time.sleep(.5)
        
def ellipticity(outfile=None):
    """
Will only measure ellipticity. HIgh auto rephase rate
"""
    
    (z,)= dmm.ask_for_values("*IDN?")
    (u,)= lockin.ask_for_values("TC.")
#1st harmonic on fist lockin
    lockin.write("REFN 1")
    lockin.write("AQN")
    time.sleep(u)#wait before measuring
    (x,y)= lockin.ask_for_values("XY.")
#    print "(x,y)=(%g,%g)" % (x,y)
    i=0
#    print u
    #checking condition
    while abs(y) > (abs(x) * 0.01):
        lockin.write("AQN")
        time.sleep(u);
        (x,y)= lockin.ask_for_values("XY.")
        i+=1; 
#        print "(x,y)=(%g,%g)" % (x,y)
        if i > 10:
#            print "Warning: phase may be incorrect."
            (m,)= (lockin.ask_for_values("MAG."))
            mag = m*abs(x)/(x)
#            print "Magnitude of 1st Harmonic = (%g)" % (m)
            break
    time.sleep(u*100) #wait to switch between harmonics.

    if abs(y) < (abs(x) * 0.01):
        e1 = 0.5*arcsin((abs(x))/(abs(z)*(0.519147*sqrt(2))))
    else:
        e1 = 0.5*arcsin((abs(mag)/abs(z))/(0.519147*sqrt(2)))
#        print "Magnitude used to calculate the following"
#l = abs((nag)/(cos(2. * e1)*z*(0.431755*sqrt(2))))

    tester=outfile
    ellip = str(e1)
    os.chdir("C:\lockindata")
    #sets directory
    if outfile is not None:
        try:
            #write out the values to a txt file
            fout = open("%s.txt" % (tester), 'a')
            fout.write('%s\n ' % (ellip))
            fout.close()
        except:
            print("FILE OUTPUT FAILED, trying to continue")
    lockin.write("REFN 1")   
    lockin.write("AQN")
    print "(ellipticity = %g)" % (e1)
#    print "(ellipticity1, ellipticity2, azimuth1, azimuth2)"
#    return (e1, e2, b1, b2)1

def findkerr(outfile=None):
    """
Repeats the ellipticity scheme to get the diff. every half second. Can be used to
find the axis on the lambda/2 plate that crosses the polarization with the axis
of the polarizer after the PEM.
"""

    control = True
    while control:
        #userinput=raw_input("Type 'stop' to stop")
        #if userinput == "stop":
        #    control = False
        #else: polarization()
        out=outfile
        ellipticity(out)    
        time.sleep(.5)
