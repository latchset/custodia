.. Keep in sync with API.md

============
Custodia API
============

Custodia uses a RESTful interface to give access to secrets.
Authentication and authorization are fully pluggable and are therefore,
not standardized.

Access paths are also not standardized, although the common practice is
to mount the secrets api under the /secrets URI.

The Custodia API uses JSON to format requests and replies.

Key/Request formats
===================

A key is a dictionary that contains the 'type' and 'value' of a key.

Simple
------

Format: ``{ type: "simple", value: }``

The Simple type is an arbitrary value holder. It is recommended, but not
required to base64 encode binary values or non-string values.

The value must be presentable as a valid JSON string. Keys are
validated before being stored. Unknown key types or invalid JSON values
are refused and an error is returned.

NOTE: As an alternative, it is possible to send a simple "raw" value by
setting the Content-type of the request to "application/octet-stream".
In this case, the value will be base64 encoded when received and can be
accessed as a base64 encoded value in the JSON string when the default
GET operation is used. Sending the "Accept: application/octet-stream"
header will instead cause the GET operation to return just the raw value
that was originally sent.

Key Exchange Message
--------------------

The Key Exchange Message format builds on the JSON Web Signature and the
JSON Web Encryption specifications to build respectively the request and
reply messages. The aim is to provide the Custodia server the means to
encrypt the reply to a client that proves possession of private key.

Format:

- Query arguments for GET: type=kem value=Message
- JSON Value for PUT/GET Reply: ``{"type:"kem","value":"Message"}``

The Message for a GET is a JWT (JWS): (flattened/decoded here for
clarity): ``{ "protected": { "kid": , "alg": "a valid alg name"}, "claims":
{ "sub": , "exp": , ["value": ]}, "signature": "XYZ...." }``

Attributes:

- public-key-identifier: This is the kid of a key that must
  be known to the Custodia service. If opportunistic encryption is
  desired and the requesting client is authenticated in other ways, a
  "jku" header could be used instead and a key fetched on the fly. This
  is not recommended for the general case and is not currently supported by
  the implementation.
- name-of-secret: this repeats the name of the secret embedded in the GET.
  This is used to prevent substitution attacks where a client is intercepted
  and its signed request is reused to request a different key.
- unix-timestamp: used to limit replay attacks, indicated expiration time,
  and should be no further than 5 minutes in the future, with leeway up to 10
  minutes to account for clock skews.
- Additional claims may be present, for example a 'value'.

The Message for a GET reply or a PUT is a JWS Encoded message (see
above) nested in a JWE Encoded message: (flattened/decoded here for
clarity): ``{ "protected": { "kid": , "alg": "a valid alg name", "enc": "a
valid enc type"}, "encrypted\_key": , "iv": , "ciphertext": , "tag": }``

Attributes:

- public-key-identifier: Must be the server public key identifier. reply (see
  above). Or the server public key for a PUT.
- The inner JWS payload will typically contain a 'value' that is an arbitrary
  key. example: ``{ type: "simple", value: }``

REST API
========

Objects
-------

There are essentially 2 objects recognized by the API:

- keys
- key containers

Key containers can be nested and named arbitrarily, however depending on
authorization schemes used the basic container is often named after a
group or a user in order to make authorization checks simpler.

Getting keys
------------

A GET operation with the name of the key: ``GET /secrets/name/of/key``

A query parameter named 'type' can be provided, in that case the key is
returned only if it matches the requested type.

Returns:

- 200 and a JSON formatted key in case of success.
- 401 if authentication is necessary
- 403 if access to the key is forbidden
- 404 if no key was found
- 406 not acceptable, key type unknown/not permitted

Storing keys
------------

A PUT operation with the name of the key: ``PUT /secrets/name/of/key``

The Content-Type MUST be 'application/json' The Content-Length MUST be
specified, and the body MUST be a key in one of the valid formats
described above.

Returns:

- 201 in case of success
- 400 if the request format is invalid
- 401 if authentication is necessary
- 403 if access to the key is forbidden
- 404 one of the elements of the path is not a valid container
- 405 if the target is a directory instead of a key (path ends in '/')
- 406 not acceptable, key type unknown/not permitted
- 409 if the key already exists

Deleting keys
-------------

A DELETE operation with the name of the key: ``DELETE /secrets/name/of/key``

Returns:

- 204 in case of success
- 401 if authentication is necessary
- 403 if access to the key is forbidden
- 404 if no key was found
- 406 not acceptable, type unknown/not permitted

Listing containers
------------------

A GET operation on a path that ends in a '/' translates into a listing
for a container: ``GET /secrets/container/``

Implementations may assume a default container if none is explicitly
provided: GET /secrets/ may return only keys under //\*

Returns:

- 200 in case of success and a dictionary containing a list of all keys
  in the container and all subcontainers
- 401 if authentication is necessary
- 403 if access to the key is forbidden
- 404 if no key was found
- 406 not acceptable, type unknown/not permitted

Creating containers
-------------------

A POST operation on a path will create a container with that name. A
trailing '/' is required: ``POST /secrets/mycontainer/``

Default containers may be automatically created by an implementation.

Returns:

- 200 if the container already exists
- 201 in case of success
- 400 if the request format is invalid
- 401 if authentication is necessary
- 403 if access to the key is forbidden
- 404 one of the elements of the path is not a valid container
- 406 not acceptable, type unknown/not permitted

Deleting containers
-------------------

A DELETE operation with the name of the container: ``DELETE /secrets/mycontainer/``

Returns:

- 204 in case of success
- 401 if authentication is necessary
- 403 if access to the container is forbidden
- 404 if no container was found
- 406 not acceptable, type unknown/not permitted
- 409 if the container is not empty
