###########
Quick Start
###########

This is a quick start guide to get something up quickly to see the API in
action.

Installing
==========

We'll simply clone the git tree and use Custodia in place to quickly test it.
Clone the repository, and run the make egg_info command to prepare the tree
for execution::

   $ git clone https://github.com/latchset/custodia.git
   $ cd custodia
   $ make egg_info

Configuring
===========

We'll use a simple a bare minimum configuration to start off.

Write a file named quick.conf with the following contents (feel free to omit
the comments):

.. literalinclude:: quick/quick.conf
   :language: ini

Also create the ``logdir`` directory (where Custodia writes its
audit log)::

   $ mkdir -p log


Running
=======

Now all we need is to start the server.
We do that with the following command::

   $ bin/custodia quick.conf

The server will output to the terminal logs about the operations being
performed against it.


Testing
=======

Once the server is started we can move to another terminal to test it.
To avoid some typing we'll create a shell alias::

   $ alias curls='curl -s --unix-socket ./quick -H "REMOTE_USER: me"'

Let's use curl to fetch the root object
::

   $ curls http://localhost/
   {"message": "Quis custodiet ipsos custodes?"}

The message "Quis custodiet ipsos custodes?" is emitted by the Root handler by
default when querying the root ('/'). It is used to test that the basic
pipeline is working and authorizing correctly.

The Root handler automatically adds also a 'secrets' handler under the path
'/secrets/', this is the actual basename of our secrets storage and will always
be used going forward.

Let's now create a new container for our secrets
::

   $ curls -X POST http://localhost/secrets/bucket/

Be sure to always pass the trailing '/' character, or the server will assume you
are trying to operate on a key rather than a container and will return you an
error.

Now that we have a container let's store a secret in the simplest way
::

   $ curls -H "Content-Type: application/octet-stream" -X PUT http://localhost/secrets/bucket/mykey -d 'P@ssw0rd'

This command is telling the server that we want to store raw data (by passing
the "Content-Type: application/octet-stream" header) in the secret named
"mykey" in the container named "bucket". The content is the string "P@ssw0rd".
NOTE: you must provide a Content-Type header or the operation will fail, the
supported types are: application/json and application/octet-stream

Let's now retrieve the secret we just stored
::

   $ curls -H "Accept: application/octet-stream" http://localhost/secrets/bucket/mykey
   P@ssw0rd

NOTE: when getting the header to use to indicate the Content-Type we want is
"Accept: application/octet-stream", this follows the standard HTTP protocol.

When the raw data method is used, the database will generally store data base64
encoded, let's try to get the same data without specifying an accepted content
type (which is the same as specifying "Accept: application/json")
::

   $ curls http://localhost/secrets/bucket/mykey
   {"type":"simple","value":"UEBzc3cwcmQ="}

NOTE: The value is the base64 encoding of the string "P@ssw0rd"

Let's now try to list the contents of our container
::

   $ curls http://localhost/secrets/bucket/
   ["mykey"]

We are returned a json array with the list of available keys.

Let's now remove this key
::

   $ curls -X DELETE http://localhost/secrets/bucket/mykey

And list again our container
::

   $ curls http://localhost/secrets/bucket/
   []

Finally let's cleanup and remove the container too
::

   $ curls -X DELETE http://localhost/secrets/bucket/


Adding Authentication
=====================

You may notice that we are currently performing no real authentication, we are
just advising the server to treat us as the "me" user. This phony
authentication is actually used when setting up Custodia behind a real HTTP
server like Apache Httpd or Nginx and using one of their modules for
authentication. For simpler setups where custodia is directly accessed we can
use one of the available modules for actual authentication.

We can add a new authentication module to the configuration.

In quick.conf add:

.. literalinclude:: quick/quick.conf.d/00-sak.conf
   :language: ini

We chose the namespace keys/sak as this will allow us to manipulate keys via
normal methods by placing them under the container named 'sak'.

Restart the server and run the following operations
::

   $ curls -X POST http://localhost/secrets/sak/
   $ curls -H "Content-Type: application/json" -X PUT http://localhost/secrets/sak/qid -d '{"type":"simple","value":"secretcode"}'

We can now created a new key called qid (from the unimaginative Quick ID) and
we can now authenticate with our new "user" QID and the proper secret key.

Set a new alias
::

   $ alias curlq='curl -s --unix-socket ./quick -H "CUSTODIA_AUTH_ID: qid" -H "CUSTODIA_AUTH_KEY: secretcode"'

Now remove the section named '[auth:header]' from the quick.conf configuration
file and restart the server.
Try to get keys with the old alias::

   $ curls http://localhost/

You will get a 403 error.
However the new alias with the correct authentication keys will work.
Try to get keys with the new alias::

   $ curlq http://localhost/


Adding Authorization
====================

Now that we can have authentication using proper keys it's time to deal with
authorization. In most cases we want to restrict access by user. When using the
SimpleAuthKeys authentication method Custodia will treat the CUSTODIA_AUTH_ID
string as the user name string (equivalent to using the REMOTE_USER header with
the SimpleHeaderAuth authentication method).

We can restrict access by user using the UserNameSpace handler.
Remove the current [authz:paths] section and replace it with:

.. literalinclude:: quick/quick.conf.d/10-namespace.conf
   :language: ini


Restart the server and try to fetch the base path.
It will fail::

   $ curlq http://localhost/

It fails because we change authorization and we do not allow '/' anymore, only
paths under /secrets/ are now allowed. However if you try to fetch any random
path under /secrets that will also fail! This is because the UserNameSpace
handler allows to access only containers under the specified path that are named
exactly as the authenticating user.

So try this::

   $ curlq -X POST http://localhost/secrets/qid/

It will create a new container for our user "qid", now we are allowed to create
and fetch any key under /secrets/qid/


Adding Encryption
=================

So far we have been using the most basic database used for testing which is
sqlite based. If you use the sqlite3 command to look into the secrets table you
will pretty quickly realize that all the stored secrets are available in plain
text.

Custodia comes with a nice overlay database type that can encrypt the data
stored in any backend storage. It is useful in case the backend chosen does
not encrypt data at rest on its own.

We'll also show how we can add a whole new subtree backed by this new database
so we can keep using both in parallel
Let's add a new database with overlay encryption to the configuration file:

.. literalinclude:: quick/quick.conf.d/20-encrypted.conf
   :language: ini

``autogen_master_key = True`` ensures that the key is auto-created on first
start. The content of the file is a symmetric key formatted according to the
JWK_ specification.

Restart the server and now try to create a container for qid under the
/encrypted tree and then try to store a secret there
::

   $ curlq -X POST http://localhost/encrypted/qid/
   $ curlq -H "Content-Type: application/octet-stream" -X PUT http://localhost/encrypted/qid/mykey -d 'P@ssw0rd'

If we now examine the database with the sqlite3 editor we'll see that the keys
in the 'encrypted' table are indeed encrypted (the encryption format is just a
JWE_ token). We can also see that the key names are not encrypted. This overlay
only encrypts the individual keys, not the metadata surrounding them.


Closing
=======

In this Quick Start Guide you've seen how to create and fetch secrets with the
Custodia API and a few of the simple authentication and authorization plugins
available. Other plugins are available, and custom ones are rather simple to
build.

Have Fun!

.. _JWK: https://tools.ietf.org/html/rfc7517
.. _JWE: https://tools.ietf.org/html/rfc7516

.. spelling::

    Quis
    custodiet
    ipsos
    custodes
    qid
    mykey
