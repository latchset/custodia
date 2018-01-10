FROM registry.fedoraproject.org/fedora:27
LABEL \
    name="latchset/custodia" \
    maintainer="Christian Heimes <cheimes@redhat.com>" \
    url="https://latchset.github.io/"

# install updates and custodia dependencies
RUN dnf -y update \
    && dnf -y install \
        python3 python3-pip python3-wheel \
        python3-requests python3-six python3-jwcrypto \
        python3-ipaclient \
    && dnf clean all

# Create Custodia user and group
# sum(ord(c) for c in 'cust') == 447
RUN groupadd -r custodia -g ${CUSTODIA_GID:-447} \
    && useradd -u ${CUSTODIA_GID:-447} -r -g custodia -d /var/lib/custodia -s /bin/bash -c "Custodia" custodia

# Directories
RUN install -d -m 755 -o custodia -g custodia \
    /etc/custodia \
    /var/log/custodia \
    /var/run/custodia \
    /var/lib/custodia
VOLUME ["/etc/custodia", "/var/log/custodia", "/var/lib/custodia", "/var/run/custodia"]

# Copy default custodia conf
COPY contrib/config/custodia/custodia.conf /etc/custodia/
COPY contrib/docker/demo.conf /etc/custodia/
RUN chown custodia:custodia /etc/custodia/*.conf \
    && chmod 644 /etc/custodia/*.conf
CMD ["/usr/bin/custodia", "/etc/custodia/custodia.conf"]

# Copy and install wheel package
COPY dist/custodia*.whl /tmp
RUN pip3 install --disable-pip-version-check --no-cache-dir --no-deps \
    --upgrade --pre /tmp/custodia*.whl

USER custodia
