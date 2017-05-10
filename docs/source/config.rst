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
   Path to :const:`AF_UNIX` socket file. In the absence of *server_url* and
   *server_socket*, the default value for *server_socket* is
   ``/var/run/custodia/${instance}.sock``.

server_string [str]
   String to send as HTTP Server string

debug [bool, default=False]
   enable debugging

makedirs [bool, default=False]
   Create *libdir*, *logdir*, *rundir*, and *socketdir*.

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

The :const:`DEFAULT` section contains default values for all sections. Some
values are always defined. Predefined values can be overridden. Paths to
files and directories are converted to absolute paths.

hostname
    hostname from ``socket.gethostname()``

instance
    name of the Custodia server instance or empty string

configdir
    Directory of the server's config file

confdpattern
    Glob pattern for additional config files

libdir
    Directory for persistent variable data (e.g. sqlite database)

logdir
    Directory for log files

rundir
    Directory for ephemeral data (e.g. ccache)

socketdir
    Directory for socket file

Example for ``custodia --instance=example /etc/custodia/ex.conf`` with an
empty config file::

    [DEFAULT]
    hostname = hostname.example
    configdir = /etc/custodia
    confdpattern = /etc/custodia/ex.conf.d/*.conf
    libdir = /var/lib/custodia/example
    logdir = /var/log/custodia/example
    rundir = /var/run/custodia/example
    socketdir = /var/run/custodia

    [global]
    auditlog = /var/log/custodia/example/audit.log
    debug = False
    server_socket = /var/run/custodia/example.sock
    makedirs = True
    umask = 027

ENV
---

The :const:`ENV` is populated with all environment variables. To reference
:const:`HOME` variable::

   server_socket = ${ENV:HOME}/server_socket


.. spelling::

    Fpath
    Fto
    Fserver
