FROM alpine:3.20.3

LABEL maintainer="PQTLSSOK"

#openssl compilation
WORKDIR /home
RUN apk update
RUN apk add git python3 py3-scipy perl
RUN apk add alpine-sdk linux-headers
RUN wget https://github.com/openssl/openssl/releases/download/openssl-3.2.0-alpha2/openssl-3.2.0-alpha2.tar.gz
RUN tar -xf openssl-3.2.0-alpha2.tar.gz
WORKDIR /home/openssl-3.2.0-alpha2
RUN ./Configure --prefix="/opt/oqs/openssl" --openssldir="/opt/oqs/openssl/ssl"
RUN make -j 8
RUN make install

#liboqs compilation
WORKDIR /home
RUN apk add astyle cmake gcc samurai libressl-dev py3-pytest py3-pytest-xdist unzip py3-jinja2 py3-yaml py3-tabulate clang18-extra-tools
RUN wget https://github.com/open-quantum-safe/liboqs/archive/refs/tags/0.9.0.tar.gz
RUN tar -xf 0.9.0.tar.gz
WORKDIR /home/liboqs-0.9.0
RUN mkdir build
WORKDIR /home/liboqs-0.9.0/build
RUN cmake -GNinja .. -DOPENSSL_ROOT_DIR="/opt/oqs/openssl" -DOQS_DIST_BUILD=ON -DCMAKE_INSTALL_PREFIX="/opt/oqs/liboqs"
RUN ninja
RUN ninja install
WORKDIR /home
ENV LIBOQS_SRC_DIR=/home/liboqs-0.9.0

#oqs provider compilation
RUN wget https://github.com/open-quantum-safe/oqs-provider/archive/refs/tags/0.5.2.tar.gz
RUN tar -xf 0.5.2.tar.gz
WORKDIR /home/oqs-provider-0.5.2/oqs-template
#enable missing sphincs versions
RUN awk '/sphincssha2256fsimple/{n=NR+6}NR==n{sub(/enable: false/, "enable: true")}1' generate.yml > generate.tmp && mv generate.tmp generate.yml
RUN awk '/sphincssha2256ssimple/{n=NR+6}NR==n{sub(/enable: false/, "enable: true")}1' generate.yml > generate.tmp && mv generate.tmp generate.yml
WORKDIR /home/oqs-provider-0.5.2
#we need to regenerate since we change the yaml file
RUN python oqs-template/generate.py
#link clang-format 
RUN ln -s /usr/lib/llvm18/bin/clang-format /usr/bin/clang-format 
RUN find . -type f -and '(' -name '*.h' -or -name '*.c' -or -name '*.inc' ')' | xargs "${CLANG_FORMAT:-clang-format}" -i
#build oqs provider
WORKDIR /home/oqs-provider-0.5.2
RUN liboqs_DIR="/opt/oqs/liboqs" cmake -DOPENSSL_ROOT_DIR="/opt/oqs/openssl" -S . -B _build && cmake --build _build && cmake --install _build

#download openssl cnf enabling the provider.
WORKDIR /home
RUN wget https://raw.githubusercontent.com/PQTLSSOK/benchmarks/9d07a8c03a3ca998d8304acd5e3902bedb06bd11/openssl.cnf
RUN mv openssl.cnf /opt/oqs/openssl/ssl/openssl.cnf
#download benchmarking python scripts
RUN wget https://raw.githubusercontent.com/PQTLSSOK/benchmarks/9d07a8c03a3ca998d8304acd5e3902bedb06bd11/kexRunBenchmarks.py
RUN wget https://raw.githubusercontent.com/PQTLSSOK/benchmarks/9d07a8c03a3ca998d8304acd5e3902bedb06bd11/kexStartServers.py
RUN wget https://raw.githubusercontent.com/PQTLSSOK/benchmarks/9d07a8c03a3ca998d8304acd5e3902bedb06bd11/sigRunBenchmarks.py
RUN wget https://raw.githubusercontent.com/PQTLSSOK/benchmarks/9d07a8c03a3ca998d8304acd5e3902bedb06bd11/sigStartServers.py
RUN mkdir data logs pki pki/cacerts pki/servercerts
WORKDIR /home/pki
#download scripts to generate certs
RUN wget https://raw.githubusercontent.com/PQTLSSOK/benchmarks/9d07a8c03a3ca998d8304acd5e3902bedb06bd11/ecmakecerts.sh
RUN wget https://raw.githubusercontent.com/PQTLSSOK/benchmarks/9d07a8c03a3ca998d8304acd5e3902bedb06bd11/makecerts.sh
RUN apk add lsof
#prepare to use the openssl fork
ENV LD_LIBRARY_PATH="/opt/oqs/openssl/lib"
ENV DEFAULT_GROUPS=kyber512

RUN chmod +x ecmakecerts.sh makecerts.sh
#fix bash to sh
RUN sed -i "1s/.*/#!\/bin\/sh/" ecmakecerts.sh
RUN sed -i "1s/.*/#!\/bin\/sh/" makecerts.sh
#generate all certs
RUN ./ecmakecerts.sh prime256v1
RUN ./ecmakecerts.sh secp384r1
RUN ./ecmakecerts.sh secp521r1
RUN ./makecerts.sh ED25519
RUN ./makecerts.sh dilithium2
RUN ./makecerts.sh dilithium3
RUN ./makecerts.sh dilithium5
RUN ./makecerts.sh falcon512
RUN ./makecerts.sh falcon1024
RUN ./makecerts.sh sphincssha2128fsimple
RUN ./makecerts.sh sphincssha2128ssimple
RUN ./makecerts.sh sphincssha2256fsimple
RUN ./makecerts.sh sphincssha2256ssimple
RUN ./makecerts.sh p256_dilithium2
RUN ./makecerts.sh rsa3072_dilithium2
RUN ./makecerts.sh p384_dilithium3
RUN ./makecerts.sh p521_dilithium5
RUN ./makecerts.sh p256_falcon512
RUN ./makecerts.sh rsa3072_falcon512
RUN ./makecerts.sh p521_falcon1024

WORKDIR /home
#cleanup
RUN rm 0.5.2.tar.gz
RUN rm 0.9.0.tar.gz
RUN rm openssl-3.2.0-alpha2.tar.gz
RUN rm -rf liboqs-0.9.0
RUN rm -rf openssl-3.2.0-alpha2
RUN rm -rf oqs-provider-0.5.2

