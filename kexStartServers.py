import subprocess
import sys

# Below are a few sets of algorithms to be tested
# The dictionary has format [algname] : [starting port]
# where [algname] is the KEX algorithm name used by OpenSSL and [starting port] marks starting port.
# The full port range depends on the number of threads
# For example: if we have 32 threads then we spawn servers in the port range 5000-5031 are going to be using x25519 as a KEX algorithm.
# Signature algorithm is static. By default is it ECDSA with P-256 curve.

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

KEMports = hybridKEMportsHybridOQS52 #which set of algorithms is to be tested, this needs to correspond to values in kexRunBenchmarks.py on the client side

processes = [] #list of threads

opensslPath = "/opt/oqs/openssl/bin/openssl" #path to the OpenSSL binary.
logsFolder = "logs/" #folder which will store output from openssl s_server
serverCertificateFolder = "pki/servercerts/" #folder where server certificate + private key is
caCertificateFolder = "pki/cacerts/" #folder where CA certificate is
signatureAlg = "prime256v1" #signature algorithm used with every KEM

#arguments parsing
serverCount = int(sys.argv[1]) # how many threads

for alg in KEMports: #for each algorithm
    startPort = KEMports[alg]
    #prepare log files to capture output
    logFiles = [open(logsFolder + alg + "_p_" + str(port) + ".log", "w") for port in range(startPort, startPort + serverCount)]
    # start threads
    algProcesses = [subprocess.Popen([opensslPath, "s_server", "-cert", serverCertificateFolder + signatureAlg + "/server.crt", "-key", serverCertificateFolder + signatureAlg + "/server.key", "-tls1_3", "-curves", alg, "-WWW", "-accept", "*:" + str(port), "-cert_chain", caCertificateFolder + signatureAlg + "/CA.crt"], stdout=logFiles[port - startPort], stderr=subprocess.STDOUT) for port in range(startPort, startPort + serverCount)]
    processes.append(algProcesses)

processes[0][0].wait() #wait for just one is enough