.. Custodia documentation master file, created by
   sphinx-quickstart on Wed Apr 15 17:49:46 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Custodia's documentation!
====================================

Custodia is a Secrets Service Provider, it stores or proxies access to keys,
password, and secret material in general. Custodia is built to use the HTTP
protocol and a RESTful API as an IPC mechanism over a local Unix Socket. It
can also be exposed to a network via a Reverse Proxy service assuming proper
authentication and header validation is implemented in the Proxy.

Custodia is modular, the configuration file controls how authentication,
authorization, storage and API plugins are combined and exposed.

Contents:

.. toctree::
   :maxdepth: 2

   readme.rst
   quick.rst
   config.rst
   commands.rst
   api.rst
   examples/index.rst
   plugins/index.rst
   container.rst

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

