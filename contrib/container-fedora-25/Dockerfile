FROM registry.fedoraproject.org/fedora:25

RUN cd /etc/yum.repos.d && curl -O https://copr.fedorainfracloud.org/coprs/adelton/custodia/repo/fedora-25/adelton-custodia-fedora-25.repo
RUN dnf -y install custodia python2-custodia python2-ipaclient python-pip && dnf clean all
RUN pip install --no-deps 'custodia.ipa < 0.3'
COPY custodia.conf /etc/custodia/custodia.conf

ENTRYPOINT /usr/bin/python2 /usr/sbin/custodia /etc/custodia/custodia.conf
