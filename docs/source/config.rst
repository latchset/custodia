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
   * http+unix://%2Fpath%2Fto%2Fserver_sock

server_socket [str]
   Path to :const:`AF_UNIX` socket file.

server_string [str]
   String to send as HTTP Server string

debug [bool, default=False]
   enable debugging


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
