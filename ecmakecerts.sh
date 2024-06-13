#!/bin/bash

ALG=$1

OPENSSL_BIN=/opt/oqs/openssl/bin/openssl
OPENSSL_CONFIG=/opt/oqs/openssl/ssl/openssl.cnf

SERVER_DOMAIN=example.com

mkdir cacerts/$ALG
mkdir servercerts/$ALG

$OPENSSL_BIN req -x509 -new -newkey ec -pkeyopt ec_paramgen_curve:$ALG -keyout "cacerts/$ALG/CA.key" -out "cacerts/$ALG/CA.crt" -nodes -subj "/CN=Benchmark CA" -days 365

$OPENSSL_BIN req -new -newkey ec -pkeyopt ec_paramgen_curve:$ALG -keyout "servercerts/$ALG/server.key" -out "servercerts/$ALG/server.csr" -nodes -subj "/CN=$SERVER_DOMAIN"

$OPENSSL_BIN x509 -req -in "servercerts/$ALG/server.csr" -out "servercerts/$ALG/server.crt" -CA "cacerts/$ALG/CA.crt" -CAkey "cacerts/$ALG/CA.key" -CAcreateserial -days 365 -extfile <(printf "subjectAltName=DNS:$SERVER_DOMAIN")
