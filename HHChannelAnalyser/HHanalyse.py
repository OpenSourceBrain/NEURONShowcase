#!/usr/bin/env python

#
#
#   A file which can be run in (Python enabled) NEURON to analyse the rate
#   variables contained in a mod file
#
#

import argparse

import neuron
print("\n\n") 

import matplotlib.pyplot as plt
from pylab import *


def process_args():
    """ 
    Parse command-line arguments.
    """
    parser = argparse.ArgumentParser(description="A script which can be run in (Python enabled) NEURON to analyse the rate variables contained in a mod file")

    parser.add_argument('channel', type=str, metavar='<channel name>', 
                        help='Name of the channel as used by NEURON (i.e. in SUFFIX statement)')
                        
    parser.add_argument('-v',
                        action='store_true',
                        default=False,
                        help="Verbose output")
                        
    parser.add_argument('-minV', 
                        type=int,
                        metavar='<min v>',
                        default=-100,
                        help='Minimum voltage to test (integer)')
                        
    parser.add_argument('-maxV', 
                        type=int,
                        metavar='<max v>',
                        default=100,
                        help='Maximum voltage to test (integer)')
                        
                        
    parser.add_argument('-stepV', 
                        type=int,
                        metavar='<step v>',
                        default=10,
                        help='Voltage step to use (integer)')
                        
    parser.add_argument('-dt', 
                        type=float,
                        metavar='<time step>',
                        default=0.01,
                        help='Timestep for simulations, dt')
                        
    parser.add_argument('-modFile', 
                        type=str,
                        metavar='<name of mod file>',
                        help='Name of the mod file containing the channel')

    
    return parser.parse_args()

def main():

    args = process_args()
        
    verbose = args.v
    
    ## Get name of channel mechanism to test

    chanToTest = args.channel
    if verbose: print "Going to test channel: "+ chanToTest

    ## Create the standard vars h, p for accessing hoc from Python & vice versa

    print "Starting NEURON in Python mode..."
    h = neuron.h
    h.load_file('stdrun.hoc')
    h('''
    objref p
    p = new PythonObject()
    ''')


    ## Create a section, set size & insert pas, passive channel mechanism

    sec = h.Section()

    secname = sec.name()
    sec.L=10
    sec.nseg=1
    for seg in sec :seg.diam = 5

    sec.insert("pas")
    sec(0.5).g_pas = 0.001
    sec(0.5).e_pas = -65


    ## insert channel into section

    sec.insert(str(chanToTest))


    ## Read state variables from mod file

    modFileName = chanToTest+".mod"
    if args.modFile:
        modFileName = args.modFile
    modFile = open(modFileName, 'r')
    inState = 0
    states = []
    for line in modFile:
        if line.count('STATE') > 0:
            inState = 1

        if inState==1:
            if line.count('}') > 0:
                inState = 0
            chopped = line.split()
            for el in chopped:
                if el != '{' and el != '}' and el != 'STATE': 
                    if el.startswith('{'): states.append(el[1:])
                    elif el.endswith('}'): states.append(el[:-1])
                    else: states.append(el)

    if verbose: print "States found in mod file: " + str(states)


    ## Settings for the voltage clamp test

    minV = args.minV
    maxV = args.maxV
    interval = args.stepV
    volts = range(minV,maxV,interval)

    v0 = -0.5                           # Pre holding potential
    preHold = 150                       # and duration
    postHoldStep = 10                  # Post step holding time between steady state checks
    postHoldMax = postHoldStep * 1000   # Max sim run time



    steadyStateVals = {}
    timeCourseVals = {}
    for s in states:
        steadyStateVals[s] = []
        timeCourseVals[s] = []




    if verbose: 
        figV = plt.figure()
        plV = figV.add_subplot(111, autoscale_on=True)

        figR = plt.figure()
        plR = figR.add_subplot(111, autoscale_on=True)


    for vh in volts:

        tstopMax = preHold + postHoldMax

        h('tstop = '+str(tstopMax))
        h.dt = args.dt
        '''
        clampobj = h.VClamp(.5)
        clampobj.dur[0]=preHold
        clampobj.amp[0]=v0
        clampobj.dur[1]=postHoldMax
        clampobj.amp[1]=vh

        '''
        # Alternatively use a SEClamp obj
        clampobj = h.SEClamp(.5)
        clampobj.dur1=preHold
        clampobj.amp1=v0
        clampobj.dur2=postHoldMax
        clampobj.amp2=vh
        clampobj.rs=0.001



        tRec = []
        vRec = []
        rateRec = {}
        for s in states:
            rateRec[s] = []

        print "Starting a simulation of max time: %f, with holding potential: %f"%(tstopMax, vh)
        #h.cvode.active(1)
        h.finitialize(v0)
        steady = False
        tolerance = 0.01
        checksPassed = 0
        checksToPass = 3
        lastCheckTime = -1
        lastCheckVal = {}
        initSlopeVal = {}
        foundTau = {}

        for s in states:
            lastCheckVal[s]=-1e-9
            initSlopeVal[s]=1e9
            foundTau[s]=False


        while ( (checksPassed < checksToPass) and (h.t <= tstopMax) ) or not foundTau[s]:

            h.fadvance()
            tRec.append(h.t)
            vRec.append(sec(0.5).v)

            for s in states:
                rateVal = eval("sec(0.5)."+s+"_"+chanToTest)
                rateRec[s].append(float(rateVal))
                if(h.t >= preHold):
                    slope = (rateRec[s][-1] - rateRec[s][-2])/h.dt
                    #print "Slope of %s: %f, init slope: %f; at val: %f and time: %f"%(s, slope, initSlopeVal[s], rateVal,  h.t)
                    timeToCheck = preHold+ (10*h.dt)

                    if initSlopeVal[s]==1e9 and h.t >= timeToCheck:
                        initSlopeVal[s] = slope
                        if verbose: print "Init slope of %s: %f at val: %f and time: %f"%(s, slope, rateVal,  h.t)
                    elif initSlopeVal[s]!=1e9 and slope/initSlopeVal[s] < 0.367879441 and not foundTau[s]:
                        foundTau[s] = True
                        timeCourseVals[s].append(h.t-timeToCheck)




            if h.t >= preHold and h.t >= lastCheckTime+postHoldStep:
                if verbose: print "Carrying out check at %f"%h.t
                lastCheckTime = h.t
                allChecksPassed = True

                for s in states:
                    val = eval("sec(0.5)."+s+"_"+chanToTest)

                    if abs((lastCheckVal[s]-val)/val) > tolerance:
                        allChecksPassed = allChecksPassed and False
                        if verbose: print "State %s has failed at %f"%(s,val)
                    else:
                        if verbose: print "State %s has passed at %f"%(s,val)

                    lastCheckVal[s] = val

                if allChecksPassed:
                    if verbose: print "One more check passed..."
                    checksPassed = checksPassed +1


        if verbose: print "Finished run,  t: %f, v: %f, vh: %f, checksPassed: %i, initSlopeVal: %s, timeCourseVals: %s ---  "%(h.t, sec(0.5).v, vh, checksPassed, str(initSlopeVal), str(timeCourseVals))

        if verbose: plV.plot(tRec, vRec, solid_joinstyle ='round', solid_capstyle ='round', color='#000000', linestyle='-', marker='None')

        for s in states:
            col='#000000'
            if s=='m': col='#FF0000'
            if s=='h': col='#00FF00'
            if s=='n': col='#0000FF'
            if verbose: plR.plot(tRec, rateRec[s], solid_joinstyle ='round', solid_capstyle ='round', color=col, linestyle='-', marker='None')

        for s in states:
            val = eval("sec(0.5)."+s+"_"+chanToTest)
            steadyStateVals[s].append(val)


    if verbose: print "steadyStateVals"+str(steadyStateVals)
    if verbose: print "timeCourseVals"+str(timeCourseVals)



    figRates = plt.figure()
    plRates = figRates.add_subplot(111, autoscale_on=False, xlim=(minV - 0.1*(maxV-minV), maxV + 0.1*(maxV-minV)), ylim=(-0.1, 1.1))


    figTau = plt.figure()
    plTau = figTau.add_subplot(111, autoscale_on=True)

    for s in states:
        col='#000000'
        if s=='m': col='#FF0000'
        if s=='h': col='#00FF00'
        if s=='n': col='#0000FF'

        plRates.plot(volts, steadyStateVals[s], label='Steady state of %s in %s'%(s,chanToTest), solid_joinstyle ='round', solid_capstyle ='round', color=col, linestyle='-', marker='o')

        plRates.legend(loc='center right')

        if len(timeCourseVals[s])==len(volts):
            plTau.plot(volts, timeCourseVals[s], label='Time course of %s in %s'%(s,chanToTest), solid_joinstyle ='round', solid_capstyle ='round', color=col, linestyle='-', marker='o')

        plTau.legend(loc='center right')

    plt.show()


    for s in states:
        file_name = "%s.%s.inf.dat"%(chanToTest, s)
        file = open(file_name, 'w')
        for i in range(len(volts)):
            file.write("%f\t%f\n"%(volts[i], steadyStateVals[s][i]))
        file.close()
        print("Written info to file: %s"%file_name)

        file_name = "%s.%s.tau.dat"%(chanToTest, s)
        file = open(file_name, 'w')
        for i in range(len(volts)):
            file.write("%f\t%f\n"%(volts[i], timeCourseVals[s][i]))
        file.close()
        print("Written info to file: %s"%file_name)

    print "Done!"


if __name__ == '__main__':
    main()