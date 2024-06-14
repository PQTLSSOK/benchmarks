import subprocess
import sys

# Below are a few sets of algorithms to be tested
# The dictionary has format [algname] : [starting port]
# where [algname] is the signature algorithm name used by OpenSSL and [starting port] marks starting port.
# The full port range depends on the number of threads
# For example: if we have 32 threads then we spawn servers in the port range 5000-5031 are going to be using ED25519 as a signature algorithm.
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

sigPorts = hybridPQSignaturesPorts #which set of algorithms is to be tested, this needs to correspond to values in sigRunBenchmarks.py on the client side

processes = []  #list of threads

opensslPath = "/opt/oqs/openssl/bin/openssl" #path to the OpenSSL binary.
logsFolder = "logs/" #folder which will store output from openssl s_server
serverCertificateFolder = "pki/servercerts/" #folder where server certificate + private key is
caCertificateFolder = "pki/cacerts/" #folder where CA certificate is
defaultKEM = "x25519" #KEX algorithm used with every signature

#arguments parsing
serverCount = int(sys.argv[1]) # how many threads

for alg in sigPorts: #for each algorithm
    startPort = sigPorts[alg]
    #prepare log files to capture output
    logFiles = [open(logsFolder + alg + "_p_" + str(port) + ".log", "w") for port in range(startPort, startPort + serverCount)]
    # start threads
    algProcesses = [subprocess.Popen([opensslPath, "s_server", "-cert", serverCertificateFolder + alg + "/server.crt", "-key", serverCertificateFolder + alg + "/server.key", "-tls1_3", "-curves", defaultKEM, "-WWW", "-accept", "*:" + str(port), "-cert_chain", caCertificateFolder + alg + "/CA.crt"], stdout=logFiles[port - startPort], stderr=subprocess.STDOUT) for port in range(startPort, startPort + serverCount)]
    processes.append(algProcesses)


processes[0][0].wait() #wait for just one is enough