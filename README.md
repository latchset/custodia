[![Build Status](https://travis-ci.org/latchset/custodia.svg?branch=master)](https://travis-ci.org/latchset/custodia)

# Custodia

A tool for managing secrets.

See our [Quick Start Guide](docs/source/quick.rst)

Custodia is a project that aims to define an API for modern cloud applications
that allows to easily store and share passwords, tokens, certificates and any
other secret in a way that keeps data secure, manageable and auditable.

The Custodia project offers example implementations of clear text and encrypted
backends, and aims to soon provide drivers to store data in external data
stores like the Vault Project, OpenStack's Barbican, FreeIPA's Vault and
similar.

In future the Custodia project plans to enhance and enrich the API to provide
access to even more secure means of dealing with private keys, like HSM as a
Service and other similar security systems.

See the Custodia documentation for more information:
https://custodia.readthedocs.io


## Requirements

### Runtime

* configparser (Python 2.7)
* cryptography
* jwcrypto >= 0.2
* requests
* six

### Testing

* pip
* setuptools >= 18.0
* tox >= 2.3.1
* wheel

custodia.ipa depends on several binary extensions and shared libraries for
e.g. python-cryptography, python-gssapi, python-ldap, and python-nss. For
testing and installation in a virtual environment, a C compiler and
several development packages are required.

#### Fedora

```
$ sudo dnf install python2 python-pip python-virtualenv python-devel \
    gcc redhat-rpm-config krb5-workstation krb5-devel libffi-devel \
    nss-devel openldap-devel cyrus-sasl-devel openssl-devel
```

#### Debian / Ubuntu

```
$ sudo apt-get update
$ sudo apt-get install -y python2.7 python-pip python-virtualenv python-dev \
    gcc krb5-user libkrb5-dev libffi-dev libnss3-dev libldap2-dev \
    libsasl2-dev libssl-dev
```

## API stability

Some APIs are provisional and may change in the future.

* Command line interface in module ```custodia.cli```.
* The script custodia-cli.
* *custodia.ipa* plugins

---

# custodia.ipa — IPA plugins for Custodia

**WARNING** *custodia.ipa is a tech preview with a provisional API.*

custodia.ipa is a collection of plugins for
[Custodia](https://custodia.readthedocs.io/). It provides integration with
[FreeIPA](http://www.freeipa.org). The *IPAVault* plugin is an interface to
[FreeIPA vault](https://www.freeipa.org/page/V4/Password_Vault). Secrets are
encrypted and stored in [Dogtag](http://www.dogtagpki.org)'s Key Recovery
Agent. The *IPACertRequest* plugin creates private key and signed certificates
on-demand. Finally the *IPAInterface* plugin is a helper plugin that wraps
ipalib and GSSAPI authentication.
 

## custodia.ipa requirements

* ipalib >= 4.5.0
* ipaclient >= 4.5.0
* Python 2.7 (Python 3 support in IPA vault is unstable.)

ipalib and ipaclient are not pulled in and install by default. The packages
depend on additional OS packages for Kerberos/GSSAPI, LDAP and NSS crypto
library. The dependencies are listed under *testing* requirements above.

```
$ pip install custodia[ipa]
```

custodia.ipa requires an IPA-enrolled host and a Kerberos TGT for
authentication. It is recommended to provide credentials with a keytab file or
GSS-Proxy. Furthermore *IPAVault* depends on Key Recovery Agent service
(``ipa-kra-install``).

---

## Example configuration

Create directories

```
$ sudo mkdir /etc/custodia /var/lib/custodia /var/log/custodia /var/run/custodia
$ sudo chown USER:GROUP /var/lib/custodia /var/log/custodia /var/run/custodia
$ sudo chmod 750 /var/lib/custodia /var/log/custodia
```

Create service account and keytab

```
$ kinit admin
$ ipa service-add custodia/$HOSTNAME
$ ipa service-allow-create-keytab custodia/$HOSTNAME --users=admin
$ mkdir -p /etc/custodia
$ ipa-getkeytab -p custodia/$HOSTNAME -k /etc/custodia/ipa.keytab
$ chown custodia:custodia /etc/custodia/ipa.keytab
```

The IPA cert request plugin needs additional permissions

```
$ ipa privilege-add \
    --desc="Create and request service certs with Custodia" \
    "Custodia Service Certs"
$ ipa privilege-add-permission \
    --permissions="Retrieve Certificates from the CA" \
    --permissions="Request Certificate" \
    --permissions="Revoke Certificate" \
    --permissions="System: Modify Services" \
    "Custodia Service Certs"
# for add_principal=True
$ ipa privilege-add-permission \
    --permissions="System: Add Services" \
    "Custodia Service Certs"
$ ipa role-add \
    --desc="Create and request service certs with Custodia" \
    "Custodia Service Cert Adminstrator"
$ ipa role-add-privilege \
    --privileges="Custodia Service Certs" \
    "Custodia Service Cert Adminstrator"
$ ipa role-add-member \
    --services="custodia/$HOSTNAME" \
    "Custodia Service Cert Adminstrator"
```

Create ```/etc/custodia/ipa.conf```

```
# /etc/custodia/ipa.conf

[global]
debug = true
makedirs = true

[auth:ipa]
handler = IPAInterface
keytab = ${configdir}/${instance}.keytab
ccache = FILE:${rundir}/ccache

[auth:creds]
handler = SimpleCredsAuth
uid = root
gid = root

[authz:paths]
handler = SimplePathAuthz
paths = /. /secrets

[store:vault]
handler = IPAVault

[store:cert]
handler = IPACertRequest
backing_store = vault

[/]
handler = Root

[/secrets]
handler = Secrets
store = vault

[/secrets/certs]
handler = Secrets
store = cert
```

Create ``/etc/systemd/system/custodia@ipa.service.d/override.conf``

On Fedora 26 and newer, the Custodia service file defaults to Python 3.
Although FreeIPA 4.5 has support for Python 3, it's not stable yet. Therefore
it is necessary to run the ``custodia.ipa`` plugins with Python 2.7. You
can either use ``systemctl edit custodia@py2.service`` to create an override
or copy the file manually. Don't forget to run ``systemctl daemon-reload`` in
the latter case.

```
[Service]
ExecStart=
ExecStart=/usr/sbin/custodia-2 --instance=%i /etc/custodia/%i.conf
```

Run Custodia server

```
$ systemctl start custodia@ipa.socket
```


## IPA cert request

The *IPACertRequest* store plugin generates or revokes certificates on the
fly. It uses a backing store to cache certs and private keys. The plugin can
create service principal automatically. However the host must already exist.
The *IPACertRequest* does not create host entries on demand.

A request like ```GET /path/to/store/HTTP/client1.ipa.example```
generates a private key and CSR for the service
```HTTP/client1.ipa.example``` with DNS subject alternative name
```client1.ipa.example```. The CSR is then forwarded to IPA and signed by
Dogtag. The resulting cert and its trust chain is returned together with the
private key as a PEM bundle.

```
$ export CUSTODIA_INSTANCE=ipa
$ custodia-cli get /certs/HTTP/client1.ipa.example
-----BEGIN RSA PRIVATE KEY-----
...
-----END RSA PRIVATE KEY-----

Issuer: organizationName=IPA.EXAMPLE, commonName=Certificate Authority
Subject: organizationName=IPA.EXAMPLE, commonName=client1.ipa.example
Serial Number: 22
Validity:
    Not Before: 2017-04-27 09:44:20
    Not After: 2019-04-28 09:44:20
-----BEGIN CERTIFICATE-----
...
-----END CERTIFICATE-----

Issuer: organizationName=IPA.EXAMPLE, commonName=Certificate Authority
Issuer: organizationName=IPA.EXAMPLE, commonName=Certificate Authority
Serial Number: 1
Validity:
    Not Before: 2017-04-26 08:24:11
    Not After: 2037-04-26 08:24:11
-----BEGIN CERTIFICATE-----
...
-----END CERTIFICATE-----
```

A DELETE request removes the cert/key pair from
the backing store and revokes the cert at the same time.

Automatic renewal of revoked or expired certificates is not implemented yet.

### FreeIPA 4.4 support

The default settings and permissions are tuned for FreeIPA >= 4.5. For 4.4,
the plugin must be configured with ```chain=False```. The additional
permission ```Request Certificate with SubjectAltName``` is required, too.

```
ipa privilege-add-permission \
    --permissions="Request Certificate with SubjectAltName" \
    "Custodia Service Certs"
```
