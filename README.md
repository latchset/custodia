# FreeIPA vault plugin for Custodia

**WARNING** highly experimental



## Requirements


### Installation and testing

* pip
* setuptools >= 18.0
* wheel

### Runtime

* custodia >= 0.3.1
* ipalib >= 4.5.0
* ipaclient >= 4.5.0
* Python 2.7 (Python 3 support in IPA vault is unstable)

custodia.ipa requires an IPA-enrolled host and a Kerberos TGT for
authentication. It is recommended to provide credentials with a keytab file or
GSS-Proxy.

## Example configuration

### Create service account and keytab
```
$ kinit admin
$ ipa service-add custodia/client1.ipa.example
$ ipa service-allow-create-keytab custodia/client1.ipa.example --users=admin
$ mkdir -p /etc/custodia
$ ipa-getkeytab -p custodia/client1.ipa.example -k /etc/custodia/custodia.keytab
```

### /etc/custodia/custodia.conf

```
[DEFAULT]
confdir = /etc/custodia
libdir = /var/lib/custodia
logdir = /var/log/custodia
rundir = /var/run/custodia

[global]
debug = true
server_socket = ${rundir}/custodia.sock
auditlog = ${logdir}/audit.log

[store:vault]
handler = IPAVault
keytab = {confdir}/custodia.keytab
ccache = FILE:{rundir}/ccache

[auth:creds]
handler = SimpleCredsAuth
uid = root
gid = root

[authz:paths]
handler = SimplePathAuthz
paths = /. /secrets

[/]
handler = Root

[/secrets]
handler = Secrets
store = vault
```
