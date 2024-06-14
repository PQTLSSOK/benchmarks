import subprocess
import os

import re
import time
import datetime
import sys

from statistics import mean, stdev
from scipy import stats

# Below are a few sets of algorithms to be tested
# The dictionary has format [algname] : [starting port]
# where [algname] is the signature algorithm name used by OpenSSL and [starting port] marks starting port.
# The full port range depends on the number of threads
# For example: if we have 32 threads then we expect that on the server ports 5000-5031 are going to be using ED25519 as a signature algorithm.
# KEX algorithm is static. By default is it x25519.

purelyPQSignaturesPorts = {
    'ED25519' : 5000,
    'prime256v1' : 5100,
    'dilithium2' : 5200,
    'dilithium3' : 5300,
    'dilithium5' : 5400,
    'falcon512' : 5500,
    'falcon1024' : 5600,
    'sphincssha2128fsimple' : 5700,
    'sphincssha2128ssimple' : 5800,
    'sphincssha2256fsimple' : 5900,
    'sphincssha2256ssimple' : 6000,
}

hybridPQSignaturesPorts = {
    'ED25519' : 5000,
    'prime256v1' : 5100,
    'secp384r1' : 5200,
    'secp521r1' : 5300,
    'p256_dilithium2' : 7000,
    'rsa3072_dilithium2' : 7100,
    'p384_dilithium3' : 7200,
    'p521_dilithium5' : 7300,
    'p256_falcon512' : 7400,
    'rsa3072_falcon512' : 7500,
    'p521_falcon1024' : 7600,
}

sigPorts = hybridPQSignaturesPorts #which set of algorithms is to be tested, this needs to correspond to values in sigStartServers.py on the server side


opensslPath = "/opt/oqs/openssl/bin/openssl" #path to the OpenSSL binary.
dataFolder = "data/" #folder which will store each measurement output from openssl s_time
resultsFolder = "results/" #folder to store results

defaultKEM = "x25519" #KEX algorithm to be used with every signature

#arguments parsing
hostname = sys.argv[1]
repeats = int(sys.argv[2])
threads = int(sys.argv[3])
testTime = int(sys.argv[4])

skipMeasurement = False # option to skip the measurement phase -> go to processing of results

#modify ENV variables to pass the KEX algorithm to s_time. s_time doesnt have a parameter to set the KEX algorithm... 
modifiedEnv = os.environ.copy()
modifiedEnv["DEFAULT_GROUPS"] = defaultKEM

suffix = datetime.datetime.now().strftime("%d-%m-%Y_%H-%M-%S") # suffix used in the file names that are part of this benchmark, sort of an ID of a benchmark run

if not skipMeasurement:
    for alg in sigPorts: #for each algorithm tested
        startPort = sigPorts[alg]
        for i in range(repeats):
            procs = [] #list of threads
            try:
                #prepare files to record output
                logFiles = [open(dataFolder + alg + "_" + suffix + "_t_" + str(threadId) + "_it_" + str(i) + ".log", "w") for threadId in range(threads)]
                #start [threads] threads of s_time, each connecting to different port, capture each STDOUT into a file inside data/
                procs = [subprocess.Popen([opensslPath, "s_time", "-connect", hostname + ":" + str(startPort + threadId), "-new", "-tls1_3", "-www", "/index.html", "-verify", "2", "-time", str(testTime)], stdout=logFiles[threadId], stderr=subprocess.STDOUT, env=modifiedEnv) for threadId in range(threads)]
                for p in procs: #wait for all to terminante - they should terminate roughly after [testTime] seconds. Throw exception if the process doesnt end after 2x the expected time
                    p.wait(timeout=testTime*2)

                for logFile in logFiles:
                    logFile.close()
            except subprocess.TimeoutExpired as exception: #a process timed out, log it and kill all in this iteration: the ones that completed successfully have terminated already, kill the rest
                print("timeout", alg, i, "killing processes", exception.cmd, exception.timeout, exception.output, exception.stdout, exception.stderr)
                for p in procs:
                    p.kill()

        print("finished " + alg)

print("finished benchmarking")

regex = r"\d+ connections in .*; (\d+\.\d+) connections/user" #regex to parse results from s_time

#prepare results file
finalFilename = "results_" + suffix + ".csv"
finalFile = open(resultsFolder + finalFilename, "w")

#process measurements
for alg in sigPorts:
    allData = ''
    print("processing", alg)
    #go over all measurements done - each iteration + each thread
    for i in range(repeats):
        for j in range(threads):
            logFile = open(dataFolder + alg + "_" + suffix + "_t_" + str(j) + "_it_" + str(i) + ".log", "r")
            allData = allData + logFile.read()
            logFile.close()

    result = re.findall(regex, allData) #extract connections/sec
    resultFloats = list(map(lambda x: float(x), result)) #convert to floats so we can do statistics
    
    #log if there are not enough measurements
    expectedNumberOfDataPoints = repeats*threads
    print("missing", str(expectedNumberOfDataPoints-len(resultFloats)), "data points")

    #calculate average, stdev and trimmed average and log into results file together with all the raw data
    avg = round(mean(resultFloats), 4)
    dev = round(stdev(resultFloats), 4)
    trimavg = round(stats.trim_mean(resultFloats, 0.05), 4)
    stringifiedData = str(resultFloats).replace("[", "").replace("]", "").replace(",", ";")
    finalFile.write(alg + "; " + str(avg) + "; " + str(dev) + "; " + str(trimavg) + ";;" + stringifiedData + "\n")

finalFile.close()








