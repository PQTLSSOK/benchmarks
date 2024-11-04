# PQ TLS benchmarking scripts user guide
This repository contains scripts which can be used to contain TLS benchmarks using OpenSSL. There are 4 Python scripts and 2 helper bash scripts.

2 of the Python scripts prefixed by `sig`, are used to benchmark signatures in TLS and the other two prefixed by `kex` are used to benchmark key exchange algorithms in TLS.

The 2 bash scripts are used to generate certificates and keys.

For simplicty, we describe the setup for benchmarking signatures. Benchmarking KEMs 
can be done similarly: by using the other two scripts.

We also provide a Dockerfile which produces a Docker image that can be used to create the client and the server. If you want to use Docker, you can skip Prerequisites and Setup sections and follow the steps in the section Docker.

## Prerequisites 
We assume we have two machines: the client and the server. They have a common set of requirements.

We assume Ubuntu 22.04 x86 is used. To run the benchmark scripts we need 
 - Python 3 with the SciPy library https://scipy.org/install/: `sudo apt install python3-scipy` (SciPy is only needed on the client to aggregate results).
 - OpenSSL with the OQS provider: The build instructions are available at https://github.com/openssl/openssl and https://github.com/open-quantum-safe/oqs-provider. Note that we used the oqsprovider version 0.5.2 (with liboqs 0.9.0) and oqsprovider version 0.4.0 (with liboqs 0.7.2) together with OpenSSL 3.2 alpha 2.

We also provide our modified OpenSSL configuration which enables the oqsprovider for TLS testing at https://github.com/PQTLSSOK/benchmarks/blob/main/openssl.cnf.

We assume the OpenSSL install directory is located at `/opt/oqs/openssl`, the `oqsprovider.so` located at `/opt/oqs/openssl/lib64/ossl-modules/oqsprovider.so`. 
The OpenSSL configuration file is to be copied to `/opt/oqs/openssl/ssl/openssl.conf`. 

In case OpenSSL is installed somewhere else, the paths inside the Python/shell scripts/environment variables need to be updated accordingly.
 
We also need to define two environment variables, e.g., by adding the following into `~/.bashrc`.
```
export LD_LIBRARY_PATH="/opt/oqs/openssl/lib64"
export DEFAULT_GROUPS=kyber512
```
The first variable is needed due to possible conflicts with existing OpenSSL installations (by the OS). The second variable needs to be set for proper OpenSSL initialization (It is required due to the last line in the `openssl.conf` file.)

## Setup
We assume we have working OpenSSL with oqsprovider on both machines.

### Client 
We copy the client script `sigRunBenchmarks.py` onto the client machine. We assume the script is copied into the home directory `~/sigRunBenchmarks.py`. 

We need to create a two subdirectories to store the data and results.
```
mkdir data results
```

### Server
We copy the client script `sigStartServers.py` onto the server machine. We assume the script is copied into the home directory `~/sigStartServers.py`. 

We need to create a subdirectories to store logs and certificates/private key ("PKI").
```
mkdir logs pki pki/cacerts pki/servercerts
```

We provide helper scripts to generate CA and server certificates/key:
 - `ecmakecerts.sh` - used to generate ECDSA certificates/keys,
 - `makecerts.sh` - used to generate everything else except EC algorithms.

 These scripts are to be copied into the pki directory `~/pki/`.

 The shell scripts take one parameter which is the algorithm id used by OpenSSL. The script will generate a CA and a server certificate (signed by the CA) and their corresponding private keys and store them at `~/pki/cacerts/[alg]/` and `~/pki/servercerts/[alg]/`. 

 For example, the first command generates certificates signed by the algorithm ECDSA (with curve P-256) and the second command generates certificates signed by the algorithm Dilithium-2.

 ```
 ./ecmakecerts.sh prime256v1
 ./makecerts.sh dilithium2
 ```

 We note that prime256v1 certificates/keys need to be generated for key exchange benchmarks as it is the default signature algorithm used (it can be changed inside the Python script, see comments inside).

## Docker
First, we need to build the Docker image from the Dockerfile. This can take a long time since the build process builds OpenSSL, libOQS and the OQS provider. The following command needs to be executed in the folder where `Dockerfile` is and it creates a Docker image under the tag `[name]`.
```
docker build -t [name] -f Dockerfile .
```
Then, we can use the docker container as the server and the client. For example the following command creates a docker container and runs the command `python sigStartServers.py 10`.
```
docker run -it --rm --net=host --mount type=bind,source="$PWD",target=/home/results [name] /bin/sh -c "python sigStartServers.py 10"
```
In general, any command described in the section below can be executed in this way.
```
docker run -it --rm --net=host --mount type=bind,source="$PWD",target=/home/results [name] /bin/sh -c "[COMMAND]"
```
Note that this command also mounts the current directory as the `/home/results` directory inside the container, therefore, if we run the client benchmarking script inside the container, the results file gets output into our current directory.

For example, if we want to run the server and the client on the same machine, we would execute:
```
docker run -it --rm --net=host --mount type=bind,source="$PWD",target=/home/results [name] /bin/sh -c "python sigStartServers.py 10"
```
and then
```
docker run -it --rm --net=host --mount type=bind,source="$PWD",target=/home/results [name] /bin/sh -c "python sigRunBenchmarks.py 0.0.0.0 1 10 10"
```

Note that the Dockerfile compiles only OQS provider version 0.5.2 with libOQS 0.9.0. The dockerfile can be easily modified to instead use other versions.
## Running benchmarks
 Now that we have everything set up on the client machine and on the server machine. We can begin benchmarking.

### Server
On the server side, we run the Python script which starts the servers. Internally, the Python script starts parallel processes of `openssl s_server` (https://www.openssl.org/docs/man3.2/man1/openssl-s_server.html).
 ```
 python3 sigStartServers.py [threads]
 ```
 Where `[threads]` is the number of servers spawned for each algorithm tested. Maximum number of threads is 100.

 Algorithms tested are hardcoded inside the script and need to be modified inside the script (see comments inside).

 At this point, the servers are ready to receive connections. Note that we assume there are no firewall rules which interfere with the testing. The scripts use ports in the range 5000-12000 (these can of course be modified).

 After the client benchmark is finished, this script needs to be manually terminated.

 ### Client
 On the client, we run the Python script which makes measurements using the `openssl s_time` tool (https://www.openssl.org/docs/man3.2/man1/openssl-s_time.html).

 ```
 python3 sigRunBenchmarks.py [hostname] [num_of_repetitions] [threads] [benchmark_time]
 ```
 Where 
 - `[hostname]` is the hostname of the server, e.g., `example.com`,
 - `[num_of_repetitions]` is how many times is the benchmark repeated (each taking `[benchmark_time]` seconds).
 - `[threads]` is the number of parallel threads of `openssl s_time`. This should correponds to the parameter used on the server. (so each client thread has its own server thread). 
 - `[benchmark_time]` is the `time` parameter of `s_time`, i.e., how many seconds does one measurement take.

 In total, the benchmark will take roughly `[num_of_repetitions]*[benchmark_time]*[number of tested algorithms]` seconds (where `[number of tested algorithms]` depends on the selected values inside `sigRunBenchmarks.py`).

 ### Results
When the benchmark finishes, it outputs a file into the folder `results`. The filename is `results_[start time].csv` where `[start time]` contains the date and time when the benchmark began.

The results file is a CSV file (with a semicolon as a separator). Each line in the file corresponds to a tested algorithm. The line format is as follows:
```
[alg name]; [average]; [stdev]; [trimmed average];; [measurements]
```
where 
 - `[alg name]` refers to the tested algorithm (using the OpenSSL naming conventions).
 - `[average]` is the average over `[measurements]`.
 - `[stdev]` is the standard deviation over `[measurements]`.
 - `[trimmed average]` is the average over `[measurements]` where 5% of the most extreme values are not part of the calculation (see https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.trim_mean.html).
  - `[measurements]` contains semicolon separated values output from each `openssl s_time` invocation, specifically, we take the value `[value] connections/user sec` from the output.

The results processing doesn't include the computation of the slowdown coefficient which is computed as described in the paper using the averages (not trimmed).

# Limitations
During our experiments, we encountered an issue with our experimental setup, which may result in the need to rerun parts of the experiment.

We suspect the issue is caused by a bug (rather a lack of implementing some timeout) in OpenSSL. What may happen is that the `openssl s_server` will get into a state where it won't respond to new connections. 

Assuming the benchmark is ran with multiple repetitions, if the error happens during iteration `i` on thread `t`, the subsequent iterations of thread `t` will not measure anything and the `openssl  s_time` will hang (outputing only a few characters). 

In the client python script, we can set a timeout for each thread, therefore, the `s_time` instance will terminate eventually (we set the time to be 2x the test time). However, the server thread will not terminate as it is spawned once at the beginning of the benchmarking.

Inspecting closely the unresponsive `s_server` instance using `netstat`, we see that the port is in the state `CLOSE_WAIT`. This is not related to the oqsprovider as it happens also when testing classical algorithms.

We do not have specific steps how to reproduce this bug but we suspect it is caused by lost packets. 

Consequently, it seems that using this setup is not ideal as `s_server` doesn't have any option to set a timeout and similarly `s_time`. For future use, we recommend creating a more robust setup. For example, one that would periodically respawn server threads while being synchronized with the client.

Additionally, when the network has high packet loss, this bug happens more frequently and renders this setup inadequate to benchmark in high packet loss environments. Which supports our hypothesis about the trigger of the bug.

## 