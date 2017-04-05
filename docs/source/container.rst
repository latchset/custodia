##################
Custodia Container
##################

The Custodia Docker image allows the Custodia server to be easily run in a
container.  By locating the socket that Custodia listens on in a data volume
that is located on the host, other containers and applications on the host
itself can use your Custodia container to manage secrets.

Data Volumes
============

The following data volumes are defined in the Custodia Docker image:

   * /etc/custodia
   * /var/lib/custodia
   * /var/log/custodia
   * /var/run/custodia

When a new Custodia container is created, new mount points on the native host
will be automatically created for each of these volumes.  You can use the
``docker inspect`` command to display the location of the volume on the host
with the following command::

    docker inspect -f '{{ range .Mounts }}{{ printf "%s -> %s\n" .Source .Destination }}{{ end }}' <container_id>

By default, the mount point on the host will use a very long unique name.
This causes problems with the Custodia socket file, as a UNIX domain socket
path is not allowed to be over 108 bytes in length.  The Custodia socket file
path will exceed this limit unless you specify a different host mount point
when creating your container.  This can be seen in the :ref:`example-section`
section below.

Systems using SELinux will need to use the ``Z`` mount option for the
``/var/run/custodia`` volume to allow proper access to the socket file.

.. _example-section:

Example
=======

The following example creates a Custodia container where Docker will
automatically create the local volume mount locations with the exception of
``/var/run/custodia``.  This volume will be mounted from ``/var/run/custodia``
on the host to allow other applications to access the Custodia socket file in
it's standard location.

The Custodia container runs as a ``custodia`` user using the uid number
``447``.  To allow the Custodia service in the container to create the socket
file on the host, we will create a local ``custodia`` user and group with the
expected uid and gid numbers, then use it to create the volume mount point on
the host with the proper permissions and ownership.  The commands to do this
are::

    $ sudo groupadd -r custodia -g 447
    $ sudo useradd -u 447 -r -g custodia custodia
    $ sudo mkdir -m 755 /var/run/custodia
    $ sudo chown custodia /var/run/custodia

Now that the volume mount point for the socket file is created on the host, the
container can be created using the following command::

    $ sudo docker run -it -v /var/run/custodia:/var/run/custodia:Z <image_id>

The Custodia service should start successfully, and its logs will be displayed
in the terminal where the container was created.

Once the container is created, you can list the location of the mounted
volumes::

    $ sudo docker inspect -f '{{ range .Mounts }}{{ printf "%s -> %s\n" .Source .Destination }}{{ end }}' <container_id>
    /var/run/custodia -> /var/run/custodia
    /var/lib/docker/volumes/a2eb52bc00586536b70a27b4395a8d4f0bd782290783132f7bdcf2bb16524250/_data -> /var/lib/custodia
    /var/lib/docker/volumes/88d00edd2c7d6c2da94fa4b8eb97246450e39d108e7fb53cff2d832969482d1c/_data -> /var/log/custodia

You can test that your Custodia container is working from your host by running
the following command::

    $ sudo curl --unix-socket /var/run/custodia/custodia.sock -X GET http://localhost/
    {"message": "Quis custodiet ipsos custodes?"}
