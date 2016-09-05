# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

import requests

from custodia import log
from custodia.plugin import HTTPAuthorizer, PluginOption

DEFAULT_API_SERVER = 'http://localhost:8080'

log.warn_provisional(__name__)


class KubeAuthz(HTTPAuthorizer):
    path = PluginOption(str, '/nodes', None)
    secrets = PluginOption(str, '/secrets', None)
    secrets_label = PluginOption(str, 'secrets_namespace', None)
    kube_api_server = PluginOption(str, DEFAULT_API_SERVER, None)

    def handle(self, request):
        reqpath = path = request.get('path', '')
        prefix = path

        while prefix.startswith('/'):
            if prefix == self.path:
                break
            else:
                prefix, _ = prefix.rsplit('/', 1)

        if prefix != self.path:
            self.logger.debug("Prefix %s does not match path %s",
                              prefix, reqpath)
            return None

        trail = path[len(prefix) + 1:]

        (namespace, podname, secret) = trail.split('/', 2)
        self.logger.debug("Checking if pod %s/%s has access to secret %s",
                          namespace, podname, secret)

        try:
            r = requests.get('%s/api/v1/namespaces/%s/pods/%s' % (
                             self.kube_api_server, namespace, podname))
            r.raise_for_status()
            data = r.json()
            node_id = data["spec"]["nodeName"]
            secrets_namespace = data["metadata"]["labels"][self.secrets_label]
        except Exception:  # pylint: disable=broad-except
            self.logger.exception("Failed to fecth data from Kube API Server")
            self.audit_svc_access(log.AUDIT_SVC_AUTHZ_FAIL,
                                  request['client_id'], path)
            return False

        self.logger.debug(
            "Pod %s/%s runs on node %s with secret namespace %s.",
            namespace, podname, node_id, secrets_namespace)

        if node_id != request.get("remote_user"):
            self.logger.debug("Node authenticated as %s, but pod is believed "
                              "to be running on %s",
                              request.get("remote_user"), node_id)
            self.audit_svc_access(log.AUDIT_SVC_AUTHZ_FAIL,
                                  request['client_id'], path)
            return False

        request['path'] = '/'.join([self.secrets, secrets_namespace, secret])
        self.audit_svc_access(log.AUDIT_SVC_AUTHZ_PASS, request['client_id'],
                              "%s -> %s" % (path, request['path']))
        return True
