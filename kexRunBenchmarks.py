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
# where [algname] is the KEX algorithm name used by OpenSSL and [starting port] marks starting port.
# The full port range depends on the number of threads
# For example: if we have 32 threads then we expect that on the server ports 5000-5031 are going to be using x25519 as a KEX algorithm.
# The signature algorithm used is selected by the server. By default it is ECDSA with P-256 curve

purelyPQKEMportsOQS4 = {
    'x25519' : 5000,
    'x448' : 5100,
    'lightsaber' : 5200,
    'saber' : 5300,
    'firesaber' : 5400,
    'bikel1' : 5500,
    'bikel3' : 5600,
#    'bikel5' : 5700, BIKE L5 not supported by oqsprovider 0.4.0
    'kyber512' : 5800,
    'kyber768' : 5900,
    'kyber1024' : 6000,
    'frodo640aes' : 6100,
    'frodo976aes' : 6200,
    'frodo1344aes' : 6300,
    'hqc128' : 6400,
    'hqc192' : 6500,
    'hqc256' : 6600,
    'ntru_hps2048509' : 6700,
    'ntru_hps2048677' : 6800,
    'ntru_hps4096821' : 6900,
    'ntru_hps40961229' : 7000,
    'ntru_hrss701' : 7100,
    'ntru_hrss1373' : 7200,
    'ntrulpr653' : 7300,
    'ntrulpr761' : 7400,
    'ntrulpr857' : 7500,
    'ntrulpr1277' : 7600,
    'sntrup653' : 7700,
    'sntrup761' : 7800,
    'sntrup857' : 7900,
    'sntrup1277' : 8000,
}

purelyPQKEMportsOQS52 = {
    'x25519' : 5000,
    'x448' : 5100,
    'bikel1' : 5500,
    'bikel3' : 5600,
    'bikel5' : 5700,
    'kyber512' : 5800,
    'kyber768' : 5900,
    'kyber1024' : 6000,
    'frodo640aes' : 6100,
    'frodo976aes' : 6200,
    'frodo1344aes' : 6300,
    'hqc128' : 6400,
    'hqc192' : 6500,
    'hqc256' : 6600,
}

hybridKEMportsHybridOQS52 = {
    'x25519' : 5000,
    'x448' : 5100,
    'P-256' : 5200,
    'P-384' : 5300,
    'P-521' : 5400,
    'p256_bikel1' : 9000,
    'x25519_bikel1' : 9100,
    'p384_bikel3' : 9200,
    'x448_bikel3' : 9300,
    'p521_bikel5' : 9400,
    'p256_kyber512' : 9500,
    'x25519_kyber512' : 9600,
    'p384_kyber768' : 9700,
    'x448_kyber768' : 9800,
    'x25519_kyber768' : 9900,
    'p256_kyber768' : 10000,
    'p521_kyber1024' : 10100,
    'p256_frodo640aes' : 10200,
    'x25519_frodo640aes' : 10300,
    'p384_frodo976aes' : 10400,
    'x448_frodo976aes' : 10500,
    'p521_frodo1344aes' : 10600,
    'p256_hqc128' : 10700,
    'x25519_hqc128' : 10800,
    'p384_hqc192' : 10900,
    'x448_hqc192' : 11000,
    'p521_hqc256' : 11100,
}

KEMports = hybridKEMportsHybridOQS52 #which set of algorithms is to be tested, this needs to correspond to values in kexStartServers.py on the server side

opensslPath = "/opt/oqs/openssl/bin/openssl" #path to the OpenSSL binary.
dataFolder = "data/" #folder which will store each measurement output from openssl s_time
resultsFolder = "results/" #folder to store results

#arguments parsing
hostname = sys.argv[1]
repeats = int(sys.argv[2])
threads = int(sys.argv[3])
testTime = int(sys.argv[4])

skipMeasurement = False # option to skip the measurement phase -> go to processing of results

suffix = datetime.datetime.now().strftime("%d-%m-%Y_%H-%M-%S") # suffix used in the file names that are part of this benchmark, sort of an ID of a benchmark run

if not skipMeasurement:
    for alg in KEMports: #for each algorithm tested
        modifiedEnv = os.environ.copy()
        modifiedEnv["DEFAULT_GROUPS"] = alg #modify ENV variables to pass the KEX algorithm to s_time. s_time doesnt have a parameter to set the KEX algorithm... 
        startPort = KEMports[alg]
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
for alg in KEMports:
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
    expectedNumberOfDataPoints = repeats * threads
    print("missing", str(expectedNumberOfDataPoints-len(resultFloats)), "data points")

    #calculate average, stdev and trimmed average and log into results file together with all the raw data
    avg = round(mean(resultFloats), 4)
    dev = round(stdev(resultFloats), 4)
    trimavg = round(stats.trim_mean(resultFloats, 0.05), 4)
    stringifiedData = str(resultFloats).replace("[", "").replace("]", "").replace(",", ";")
    finalFile.write(alg + "; " + str(avg) + "; " + str(dev) + "; " + str(trimavg) + ";;" + stringifiedData + "\n")

finalFile.close()








