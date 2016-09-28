# Copyright (C) 2016  Custodia Project Contributors - see LICENSE file

import yaml

from requests.exceptions import HTTPError
from custodia.client import CustodiaSimpleClient


class CustodiaSimpleConstructor(object):
    yaml_tag = u'!custodia/simple'

    def __init__(self, url):
        self.client = CustodiaSimpleClient(url)

    def __call__(self, loader, node):
        value = loader.construct_scalar(node)
        return self.client.get_secret(value)


def demo():
    constructor = CustodiaSimpleConstructor(
        'http+unix://%2E%2Fserver_socket/secrets'
    )
    constructor.client.headers['REMOTE_USER'] = 'user'

    # create entries
    try:
        c = constructor.client.list_container('test')
    except HTTPError:
        constructor.client.create_container('test')
        c = []
    if 'key' not in c:
        constructor.client.set_secret('test/key', 'secret password')

    yaml.add_constructor(CustodiaSimpleConstructor.yaml_tag,
                         constructor)
    yaml_str = 'password: !custodia/simple test/key'
    print(yaml_str)
    result = yaml.load(yaml_str)
    print(result)


if __name__ == '__main__':
    demo()
