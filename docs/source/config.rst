###############
Custodia Config
###############

Custodia uses a ini-style configuration file with
`extended interpolation <https://docs.python.org/3/library/configparser.html#configparser.ExtendedInterpolation>`_.

Sections
========

globals
-------

server_url [str]
   * http://hostname:port
   * https://hostname:port
   * http+unix://%2Fpath%2Fto%2Fserver_sock

   Custodia supports systemd socket activation. The server automatically
   detects socket activation and uses the first file descriptor (requires
   python-systemd). Socket family and port/path must match settings in
   configuration file::

       $ /usr/lib/systemd/systemd-activate -l $(pwd)/custodia.sock python -m custodia.server custodia.conf

server_socket [str]
   Path to :const:`AF_UNIX` socket file.

server_string [str]
   String to send as HTTP Server string

debug [bool, default=False]
   enable debugging

tls_certfile [str]
   The filename of the server cert file and its intermediate certs. The server
   cert file can also contain the private key. The option is required for
   HTTPS server.

tls_keyfile [str]
   The filename of the private key file for Custodia's HTTPS server.

tls_cafile [str]
   Path to a file with trust anchors. The trust anchors are used to verify
   client certificates. When the option is not set, Python loads root CA
   from the system's default verify location.

tls_verify_client [bool, default=False]
   Require TLS client certificates

authenticators
--------------

Example::

   [auth:header]
   handler = custodia.httpd.authenticators.SimpleHeaderAuth
   name = REMOTE_USER


authorizers
-----------

Example::

   [authz:namespaces]
   handler = custodia.httpd.authorizers.UserNameSpace
   path = /secrets/
   store = simple


stores
------

Example::

   [store:simple]
   handler = custodia.store.sqlite.SqliteStore
   dburi = /path/to/secrets.db
   table = secrets


consumers
---------

Example::

   [/]
   handler = custodia.root.Root
   store = simple


Special sections
================

DEFAULT
-------

The :const:`DEFAULT` section contains default values for all sections.

ENV
---

The :const:`ENV` is populated with all enviroment variables. To reference
:const:`HOME` variable::

   server_socket = ${ENV:HOME}/server_socket
