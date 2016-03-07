[![Build Status](https://travis-ci.org/latchset/custodia.svg?branch=master)](https://travis-ci.org/latchset/custodia)

Custodia
========

A tool for managing secrets.


Custodia is a project that aims to define an API for modern cloud applications
that allows to easily store and share passwords, tokens, certificates and any
other secret in a way that keeps data secure, mangeable and auditable.

The Custodia project offers example implementations of clear text and encrypted
backends, and aims to soon provide drivers to store data in external data
stores like the Vault Project, OpenStack's Barbican, FreeIPA's Vault and
similar.

In future the Custodia project plans to enhance and enrich the API to provide
access to even more secure means of dealing with private keys, like HSM as a
Service and other similar security systems.

See the Custodia wiki for more information about the current architecture:
https://github.com/latchset/custodia/wiki
