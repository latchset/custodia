#!/bin/sh
# Written by Christian Heimes
set -e

export CAOUTDIR=.
export CATMPDIR=tmp

rm -rf $CATMPDIR

mkdir -p $CAOUTDIR
mkdir -p $CATMPDIR

touch $CATMPDIR/custodia-ca.db
touch $CATMPDIR/custodia-ca.db.attr
echo '01' > $CATMPDIR/custodia-ca.crt.srl
echo '01' > $CATMPDIR/custodia-ca.crl.srl


# root CA
openssl req -new \
    -config custodia-ca.conf \
    -out $CATMPDIR/custodia-ca.csr \
    -keyout $CAOUTDIR/custodia-ca.key \
    -batch

openssl ca -selfsign \
    -config custodia-ca.conf \
    -in $CATMPDIR/custodia-ca.csr \
    -out $CAOUTDIR/custodia-ca.pem \
    -extensions custodia_ca_ext \
    -batch

# server cert
openssl req -new \
    -config custodia-server.conf \
    -out $CATMPDIR/custodia-server.csr \
    -keyout $CAOUTDIR/custodia-server.key \
    -batch

openssl ca \
    -config custodia-ca.conf \
    -in $CATMPDIR/custodia-server.csr \
    -out $CAOUTDIR/custodia-server.pem \
    -policy match_pol \
    -extensions custodia_server_ext \
    -batch

# client cert
openssl req -new \
    -config custodia-client.conf \
    -out $CATMPDIR/custodia-client.csr \
    -keyout $CAOUTDIR/custodia-client.key \
    -batch

openssl ca \
    -config custodia-ca.conf \
    -in $CATMPDIR/custodia-client.csr \
    -out $CAOUTDIR/custodia-client.pem \
    -policy match_pol \
    -extensions custodia_client_ext \
    -batch

echo DONE
