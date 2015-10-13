# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

import re

from docker import Client

from custodia import log
from custodia.httpd.authenticators import HTTPAuthenticator

DEFAULT_REGEX = r'/docker-([0-9a-f]{64})\.scope'
DEFUALT_DOCKER_URI = 'unix://var/run/docker.sock'


class NodeAuth(HTTPAuthenticator):

    def __init__(self, config=None):
        super(NodeAuth, self).__init__(config)
        if self.config is not None:
            regex = self.config.get('docker_regex', DEFAULT_REGEX)
            self.docker_uri = self.config.get('docker_uri', DEFUALT_DOCKER_URI)
        else:
            regex = DEFAULT_REGEX
            self.docker_uri = DEFUALT_DOCKER_URI
        self.id_filter = re.compile(regex)

    def _pid2dockerid(self, pid):
        with open('/proc/%i/cgroup' % pid) as f:
            for line in f:
                mo = self.id_filter.search(line)
                if mo is not None:
                    return mo.group(1)
        return None

    def handle(self, request):
        creds = request.get('creds')
        if creds is None:
            self.logger.debug('Missing "creds" on request')
            return None
        dockerid = self._pid2dockerid(int(creds['pid']))
        if dockerid is None:
            self.logger.debug("Didn't find docker ID for pid %s", creds['pid'])
            return None

        try:
            dc = Client(base_url=self.docker_uri)
            data = dc.inspect_container(dockerid)
            data_id = data['Id']
            data_labels = dict(data['Config']['Labels'])
        except Exception as err:  # pylint: disable=broad-except
            self.logger.debug("Failed to query docker for [%s:%s]: %s",
                              creds['pid'], dockerid, err)
            self.audit_svc_access(log.AUDIT_SVC_AUTH_FAIL,
                                      request['client_id'], dockerid)
            return False

        if data_id != dockerid:
            self.logger.debug("Docker ID %s not found!", dockerid)
            self.audit_svc_access(log.AUDIT_SVC_AUTH_FAIL,
                                      request['client_id'], dockerid)
            return False

        podname = data_labels.get('io.kubernetes.pod.name')
        if podname is None:
            self.logger.debug("Pod Name not found for Docker ID %s", dockerid)
            self.audit_svc_access(log.AUDIT_SVC_AUTH_FAIL,
                                      request['client_id'], dockerid)
            return False

        self.audit_svc_access(log.AUDIT_SVC_AUTH_PASS,
                                  request['client_id'], dockerid)
        request['client_id'] = dockerid
        request['remote_user'] = podname
        return True
