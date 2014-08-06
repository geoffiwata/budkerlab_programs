import time
from numpy import arcsin,cos,sqrt,pi

from visa import *

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
    

def polarization(intensity):
    """
    Measures both X, Y in both harmonics, and DC voltage,
    and calculates the ellipticity(radians) in the light.
    If conditions of y < 10% of x, magnitude is used to
    calculate ellipticity.
    Both ellipticity and azimuth are written to file.
    """

    d = float (intensity)
    (z,)= dmm.ask_for_values("*IDN?")
    (u,)= lockin.ask_for_values("TC.")
    (p,)= lockin2.ask_for_values("TC.")
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
    #time.sleep(u*100) #wait to switch between harmonics.

#1st harmonic on 2nd lockin
    lockin2.write("REFN 1")
    lockin2.write("AQN")
    time.sleep(u)#wait before measuring
    (x1,y1)= lockin2.ask_for_values("XY.")
#    print "(x1,y1)=(%g,%g)" % (x1,y1)
    i=0
#    print u
    #checking condition
    while abs(y1) > (abs(x1) * 0.01):
        lockin2.write("AQN")
        time.sleep(u);
        (x1,y1)= lockin2.ask_for_values("XY.")
        i+=1; 
#        print "(x1,y1)=(%g,%g)" % (x1,y1)
        if i > 10:
#            print "Warning: phase may be incorrect."
            (k,)= (lockin2.ask_for_values("MAG."))
            kag = k*abs(x1)/(x1)
#            print "Magnitude of 1st Harmonic on Second lockin= (%g)" % (k)
            break
    
#2nd harmonic on first lockin
    lockin.write("REFN 2")
    lockin.write("AQN")
    time.sleep(u) #wait to switch between harmonics.    
    (v,w)= lockin.ask_for_values("XY.")
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
            nag = n*abs(v)/(v)
#            print "Magnitude of 2st Harmonic on fist lockin= (%g)" % (n)
            break
#Now do 2nd harmonic on second lockin
    lockin2.write("REFN 2")
    lockin2.write("AQN")
    time.sleep(u) #wait to switch between harmonics.    
    (v1,w1)= lockin2.ask_for_values("XY.")
#    print "(v1,w1)=(%g,%g)" % (v1,w1)
    i=0
    while abs(w1) > (abs(v1) * 0.01):
        lockin2.write("AQN")
        time.sleep(u);
        (v1,w1)= lockin2.ask_for_values("XY.")
#        print "(v1,w1)=(%g,%g)" % (v1,w1)
        i+=1;
        if i > 10:
#            print "Warning: phase may be incorrect."
            (c,) = lockin2.ask_for_values("MAG.")
            cag = c*abs(v1)/(v1)
#            print "Magnitude of 2st Harmonic on second lockin= (%g)" % (c)
            break
    
#    print "DC voltage 1 is ", (z)
#    print "DC voltage 2 is ", (d)
    if abs(y) < (abs(x) * 0.01):
        e1 = 0.5*arcsin((abs(x)/abs(z))/(0.519147*sqrt(2)))
    else:
        e1 = 0.5*arcsin((abs(mag)/abs(z))/(0.519147*sqrt(2)))
#        print "Magnitude used to calculate the following"
    if abs(w) < (abs(v) * 0.01):
        b1 = 0.5*arcsin((abs(v)*cos(2. * abs(e1)))/abs(z))/(0.431755*sqrt(2))
    else:
        b1 = 0.5*arcsin((abs(nag)*cos(2. * abs(e1)))/abs(z))/(0.431755*sqrt(2))
#        print "magnitude used to calculate"
    if abs(y1) < (abs(x1) * 0.01):
        e2 = 0.5*arcsin((abs(x1)/abs(d))/(0.519147*sqrt(2)))
    else:
        e2 = 0.5*arcsin((abs(kag)/abs(d))/(0.519147*sqrt(2)))
#        print "Magnitude used to calculate the following"
    if abs(w1) < (abs(v1) * 0.01):
        b2 = 0.5*arcsin((abs(v1)*cos(2. * abs(e2)))/abs(d))/(0.431755*sqrt(2))
    else:
        b2 = 0.5*arcsin((abs(cag)*cos(2. * abs(e2)))/abs(d))/(0.431755*sqrt(2))
#        print "magnitude used to calculate"
    diff = float(e2 - e1)
    #(azi,) = pi/4.
    #lockin.write("REFN 1")
    #lockin.write("AQN")
 #   if outfile is not None:
  #      try:
            # write out the values to a file
            #open("C:\lockindata")
   #         fout=open(outfile,'a')
    #        fout.write("%g,%g" % (e,b))
     #       fout.close()
#        except:
#            print("FILE OUTPUT FAILED, trying to continue")

    print "(Difference, ellip1, ellip2) = (%g,%g,%g)" % (diff, e1, e2)
#    print "(ellipticity1, ellipticity2, azimuth1, azimuth2)"
    return (e1, e2, b1, b2)

def findaxis(dmm2value):
    """
Repeats the polarization scheme to get the diff. every second. Can be used to
find the axis on the lambda/2 plate that crosses the polarization with the axis
of the polarizer after the PEM.
"""
    h = float(dmm2value)
    control = True
    while control:
        #userinput=raw_input("Type 'stop' to stop")
        #if userinput == "stop":
        #    control = False
        #else: polarization()
        polarization(h)    
        time.sleep(1)
