Custodia Plugins
================

Custodia is built as an HTTP based pipeline where each stage of the process is
pluggable. The main stages are:

  * Authentication
  * Authorization
  * Request handling
  * Storage

Plugin Stages
-------------

Authentication
^^^^^^^^^^^^^^

Authentication is handled by a stackable set of arbitrary plugins (python
modules referenced in the configuration file). If any of the authentication
plugins returns a negative answer the request is aborted with a 403 error. If
any returns a positive answer then the request is allowed to proceed to the
next phase. If none of the plugins returns either a positive or negative
answer the request fails, as by default access is denied.

Authorization
^^^^^^^^^^^^^

Authorization is also handled by a stackable set of plugins, however in this
case plugins are ordered. As soon as one plugin returns a positive or negative
answer the request can pass to the next stage or is refused. If no plugin
returns a positive or negative answer, the request is refused as access is
denied by default.

Request Handling
^^^^^^^^^^^^^^^^

Request handling is also pluggable and depends mostly on the path used in the
request. Multiple handlers can be used, and each will be associated to a path.
Handlers can be arbitrarily complex, custodia provides a default handler called
'secrets', this handler can manage access to secrets using various request
message types (currently simple or key-exchange-message).

Storage
^^^^^^^

The storage in custodia is also pluggable and doesn't need to be an actual
database or file system. It can as well be a chaining module that will call
another Custodia instance up the chain, usually massaging the request path and
the request headers to provide hints or authentication tokens to the upstream
Custodia instance. This is very powerful and allows the infrastructure to
partition the namespace and redirect requests to multiple sources, based on
arbitrary rules, either for load balancing reasons, or in order to segregate
different tenants to different storage systems.

Plugin Modules
--------------

.. toctree::
   :maxdepth: 2

   baseclasses.rst
   authenticators.rst
   authorizers.rst
   consumers.rst
   stores.rst
   clients.rst
   ipa.rst
