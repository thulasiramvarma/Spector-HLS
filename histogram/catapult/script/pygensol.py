#!/usr/bin/env python3

import subprocess
import itertools
import sys
import os
import multiprocessing as mp
import argparse
import shutil
import time
import datetime

FULL_UNROLL = -1


tparamFilepath = "./src/params.h.template"
tdirectiveFilepath = "./src/directives.tcl.template"

logName = ""
outRootPath = "./solutions"
benchmark_name = "histogram"

files_to_copy = ["./src/histogram_hls.cpp", "./src/histogram_hls.h", "./src/hist_test.cpp"]

def run_script(path):
    print(path, "started at", datetime.datetime.now())

    try:
        start = time.time()
        command = " ".join(["timeout 1800", "catapult", "-f", "directives.tcl"])
        subprocess.check_output(command, cwd=path, shell=True)
        end = time.time()

        outFile = open(logName, 'at')
        outFile.write(path + "\n")
        outFile.close()

        outFile = open(logName + ".time", 'at')
        outFile.write(path + ',' + str(end-start) + '\n')
        outFile.close()

        print(path, "end at", datetime.datetime.now(), " elapsed", end-start)

    except subprocess.CalledSubprocessError:
        print(path, "Timeout at", datetime.datetime.now())

        outFile = open(logName + '.timeout', 'at')
        outFile.write(path + '\n')
        outfile.close()

    except:
        raise

def write_params(finalCombinations, tparamFilepath, tdirectiveFilepath):
    dirlist = []
    
    for (num, values) in enumerate(finalCombinations):

        # Progress bar
        if(num % 1000) == 0:
            percent = float(num) / len(finalCombinations) * 100.0
            print("[" + str(int(percent)) + "%]")

        strValues = [' ' if v==FULL_UNROLL else str(v) for v in values]
        
        # Read template file and set the knob values
        directives_text = ""
        params_text = ""
        with open(tparamFilepath, "rt") as fin:
            for line in fin:

                newline = line

                for (i, replace) in reversed(list(enumerate(strValues))):
                    text = '%' + str(i)
                    newline = newline.replace(text, replace)

                params_text += newline
        
        with open(tdirectiveFilepath, "rt") as fin:
            for line in fin:

                newline = line

                for (i, replace) in reversed(list(enumerate(strValues))):
                    if replace == 'I' or replace == 'B':
                        if replace == 'I':
                            replace = "INTERLEAVED"
                        else:
                            replace = "BLOCK"
                    text = '%' + str(i)
                    newline = newline.replace(text, replace)

                directives_text += newline


        # Write the params.h file
        dirname = os.path.join(outRootPath, benchmark_name + str(num).zfill(4))
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        dirlist.append(dirname)
        with open(os.path.join(dirname, "params.h"), "wt") as fout:
            fout.write(params_text)
        with open(os.path.join(dirname, "directives.tcl"), "wt") as fout:
            fout.write(directives_text)
        # Copy source files
        for f in files_to_copy:
            shutil.copy(f, dirname)

    return dirlist

# *****************
# knobs 
# *****************

KNOB_NUM_HIST = [i for i in range(1,16)] # 0
KNOB_HIST_SIZE = [256] # 1

KNOB_UNROLL_LMM = [i for i in range(1,8)] # 2 
KNOB_UNROLL_LP  = [i for i in range(1,4)] # 3

KNOB_DATA_DIV = [True, False] # True for interleave, false for block # 4
KNOB_DATA_INTERLEAVE = [1, 2] # 5
KNOB_DATA_BLOCK = [i for i in range(1,8)] # 5

blockCombinations = list(itertools.product(
    KNOB_HIST_SIZE, #0
    KNOB_NUM_HIST,  #1
    KNOB_UNROLL_LMM, #2
    KNOB_UNROLL_LP, #3
    "B", #4
    KNOB_DATA_BLOCK #5
    ))

interleaveCombinations = list(itertools.product(
    KNOB_HIST_SIZE, #0
    KNOB_NUM_HIST,  #1
    KNOB_UNROLL_LMM, #2
    KNOB_UNROLL_LP, #3
    "I", #4
    KNOB_DATA_INTERLEAVE #5
    ))

print("HELLO")
finalCombinations = blockCombinations + interleaveCombinations
print("final combinations are " + str(len(finalCombinations)))
# -------------------------------------------------------

def main():

    global logName
    global run_place_route

    parser = argparse.ArgumentParser(description='Generate HLS RTL set.')
    parser.add_argument('-np', '--num-processes', metavar='N', type=int, default=-1, help='Number of parallel processes (default: all)')
    parser.add_argument('-dl', '--dir-list', help='Get directories to compile from a file.')
    parser.add_argument('-g', '--generate-only', action='store_true', help='Only generate solution folders.')
    parser.add_argument('-onc', '--output-not-compiled', help='Output list of folders not synthesized.')

    args = parser.parse_args()

    num_processes = args.num_processes

    if num_processes > 0:
        print("Using " + str(num_processes) + " processes")
    else:
        print("Using all available processes")

    logName = logNameSynth

    dirlist = write_params(finalCombinations, tparamFilepath, tdirectiveFilepath)

    print("Num combinations: " + str(len(finalCombinations)))

    if args.dir_list:
        dirlist = [line.strip() for line in open(args.dir_list)]


    # Get folders already compiled from previous log file
    compiled = []

    if os.path.isfile(logName):
        print("Reading processed folders from log file")
        logFile = open(logName, 'rt')
        for line in logFile:
            name = line.split('\n')
            compiled.append(name[0])
        logFile.close()


    for f in compiled:
        dirlist.remove(f)


    if args.output_not_compiled:
        with open(args.output_not_compiled, 'wt') as f:
            for d in dirlist:
                f.write(d + '\n')


    if not args.generate_only:

        # Start processes 
        print("Processing " + str(len(dirlist)) + " folders")



        if num_processes > 0:
        	pool = mp.Pool(num_processes)
        else:
        	pool = mp.Pool()
        #pool.map(run_script, dirlist)
        result = pool.map_async(run_script, dirlist).get(31536000) # timeout of 365 days

#i = 0
#for (num, values) in enumerate(finalCombinations):
#    i = i + 1
#    strValues = [str(v) for v in values]
#    for (i, replace) in reversed(list(enumerate(strValues))):
#    if i == 1:
#        break

#if __name__ == "__main__":
#    main()

