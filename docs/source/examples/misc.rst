Clients
=======

Docker credential store
-----------------------

`docker-credential-custodia`_ is an implementation of `Docker Credentials Store`_ in Go.


.. _Docker Credentials Store: http://www.projectatomic.io/blog/2016/03/docker-credentials-store/

.. _docker-credential-custodia: https://github.com/latchset/docker-credential-custodia


curl
----

Test Custodia::

    $ curl --unix-socket /var/run/custodia/custodia.sock -X GET http://localhost/
    {"message": "Quis custodiet ipsos custodes?"}

Initialize a container for secrets::

    $ curl --unix-socket /var/run/custodia/custodia.sock -X POST http://localhost/secrets/container/

Create or update a secret::

    $ curl --unix-socket /var/run/custodia/custodia.sock -H "Content-Type: application/json" -X PUT http://localhost/secrets/container/key -d '{"type": "simple", "value": "secret value"}'

Get a secret::

    $ curl --unix-socket /var/run/custodia/custodia.sock -X GET http://localhost/secrets/container/key
    {"type":"simple","value":"secret value"}

Delete a secret::

    $ curl --unix-socket /var/run/custodia/custodia.sock -X DELETE http://localhost/secrets/container/key
