# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

from custodia.httpd.authorizers import SimplePathAuthz
from custodia.message.common import InvalidMessage
from custodia.message.common import MessageHandler
from jwcrypto.common import json_decode
from jwcrypto.common import json_encode
from jwcrypto.jwe import JWE
from jwcrypto.jwk import JWK
from jwcrypto.jws import JWS
from jwcrypto.jwt import JWT
import os
import time


class UnknownPublicKey(Exception):
    pass


class KEMKeysStore(SimplePathAuthz):
    """A KEM Keys Store.

    This is a store that holds public keys of registered
    clients allowed to use KEM messages. It takes the form
    of an authorizer merely for the purpose of attaching
    itself to a 'request' so that later on the KEM Parser
    can fetch the appropariate key to verify/decrypt an
    incoming request and make the payload available.

    The KEM Parser will actually pergorm additional
    authorization checks in this case.

    SimplePathAuthz is extended here as we ant to attach the
    store only to requests on paths we are configured to
    manage.
    """

    def __init__(self, config=None):
        super(KEMKeysStore, self).__init__(config)
        self.paths = []
        if 'paths' in self.config:
            self.paths = self.config['paths'].split()
        self._server_key = None
        self._alg = None
        self._enc = None

    def _db_key(self, kid):
        return os.path.join('kemkeys', kid)

    def handle(self, request):
        inpath = super(KEMKeysStore, self).handle(request)
        if inpath:
            request['KEMKeysStore'] = self
        return inpath

    def find_key(self, kid):
        dbkey = self._db_key(kid)
        pubkey = self.store.get(dbkey)
        if pubkey is None:
            raise UnknownPublicKey(kid)
        return pubkey

    @property
    def server_key(self):
        if self._server_key is None:
            if 'server_key' not in self.config:
                raise UnknownPublicKey("Server Key not defined")
            key = self.find_key(self.config['server_key'])
            self._server_key = JWK(**(json_decode(key)))
        return self._server_key

    @property
    def alg(self):
        if self._alg is None:
            alg = self.config.get('signing_algorithm', None)
            if alg is None:
                raise ValueError('Signing algorithm not configured')
            self._alg = alg
        return self._alg


class KEMHandler(MessageHandler):
    """Handles 'kem' messages"""

    def __init__(self, request):
        super(KEMHandler, self).__init__(request)
        self.kkstore = self.req.get('KEMKeysStore', None)
        if self.kkstore is None:
            raise Exception('KEM KeyStore not configured')
        self.client_key = None
        self.name = None

    def _get_key(self, header):
        if 'kid' not in header:
            raise InvalidMessage("Missing key identifier")

        key = self.kkstore.find_key(header['kid'])
        if key is None:
            raise UnknownPublicKey('Key found [kid:%s]' % header['kid'])
        return json_decode(key)

    def parse(self, msg):
        """Parses the message.

        We check that the message is properly formatted.

        :param msg: a json-encoded value containing a JWS or JWE+JWS token

        :raises InvalidMessage: if the message cannot be parsed or validated

        :returns: A verified payload
        """

        try:
            jtok = JWT(jwt=msg)
        except Exception as e:
            raise InvalidMessage('Failed to parse message: %s' % str(e))

        try:
            token = jtok.token
            if isinstance(token, JWS):
                key = self._get_key(token.jose_header)
                self.client_key = JWK(**key)
                token.verify(self.client_key)
                payload = token.payload
            elif isinstance(token, JWE):
                token.decrypt(self.kkstore.server_key)
                # If an ecnrypted payload is received then there must be
                # a nestd signed payload to verify the provenance.
                nested = JWS()
                nested.deserialize(token.payload)
                key = self._get_key(nested.jose_header)
                self.client_key = JWK(**key)
                nested.verify(self.client_key)
                payload = nested.payload
            else:
                raise TypeError("Invalid Token type: %s" % type(jtok))
        except Exception as e:
            raise InvalidMessage('Failed to validate message: %s' % str(e))

        # FIXME: check name/time

        return {'type': 'kem',
                'value': {'kid': self.client_key.key_id,
                          'payload': payload}}

    def reply(self, output):
        if self.client_key is None:
            raise UnknownPublicKey("Peer key not defined")

        ktype = self.client_key.key_type
        if ktype == 'RSA':
            enc = ('RSA1_5', 'A256CBC-HS512')
        else:
            raise ValueError("'%s' type not supported yet" % ktype)

        value = make_enc_kem(self.name, output,
                             self.kkstore.server_key,
                             self.kkstore.alg,
                             self.client_key, enc)

        return json_encode({'type': 'kem', 'value': value})


def make_sig_kem(name, value, key, alg):
    payload = {'name': name, 'time': int(time.time())}
    if value is not None:
        payload['value'] = value
    S = JWS(json_encode(payload))
    prot = {'kid': key.key_id, 'alg': alg}
    S.add_signature(key, protected=json_encode(prot))
    return S.serialize(compact=True)


def make_enc_kem(name, value, sig_key, alg, enc_key, enc):
    plaintext = make_sig_kem(name, value, sig_key, alg)
    eprot = {'kid': enc_key.key_id, 'alg': enc[0], 'enc': enc[1]}
    E = JWE(plaintext, json_encode(eprot))
    E.add_recipient(enc_key)
    return E.serialize(compact=True)


# unit tests
import unittest
from custodia.store.sqlite import SqliteStore


server_key = {
    "kty": "RSA",
    "kid": "65d64463-7448-499e-8acc-55db2ce67039",
    "n": "maxhbsmBtdQ3CNrKvprUE6n9lYcregDMLYNeTAWcLj8NnPU9XIYegT"
         "HVHQjxKDSHP2l-F5jS7sppG1wgdAqZyhnWvXhYNvcM7RfgKxqNx_xAHx"
         "6f3yy7s-M9PSNCwPC2lh6UAkR4I00EhV9lrypM9Pi4lBUop9t5fS9W5U"
         "NwaAllhrd-osQGPjIeI1deHTwx-ZTHu3C60Pu_LJIl6hKn9wbwaUmA4c"
         "R5Bd2pgbaY7ASgsjCUbtYJaNIHSoHXprUdJZKUMAzV0WOKPfA6OPI4oy"
         "pBadjvMZ4ZAj3BnXaSYsEZhaueTXvZB4eZOAjIyh2e_VOIKVMsnDrJYA"
         "VotGlvMQ",
    "e": "AQAB",
    "d": "Kn9tgoHfiTVi8uPu5b9TnwyHwG5dK6RE0uFdlpCGnJN7ZEi963R7wy"
         "bQ1PLAHmpIbNTztfrheoAniRV1NCIqXaW_qS461xiDTp4ntEPnqcKsyO"
         "5jMAji7-CL8vhpYYowNFvIesgMoVaPRYMYT9TW63hNM0aWs7USZ_hLg6"
         "Oe1mY0vHTI3FucjSM86Nff4oIENt43r2fspgEPGRrdE6fpLc9Oaq-qeP"
         "1GFULimrRdndm-P8q8kvN3KHlNAtEgrQAgTTgz80S-3VD0FgWfgnb1PN"
         "miuPUxO8OpI9KDIfu_acc6fg14nsNaJqXe6RESvhGPH2afjHqSy_Fd2v"
         "pzj85bQQ",
    "p": "2DwQmZ43FoTnQ8IkUj3BmKRf5Eh2mizZA5xEJ2MinUE3sdTYKSLtaE"
         "oekX9vbBZuWxHdVhM6UnKCJ_2iNk8Z0ayLYHL0_G21aXf9-unynEpUsH"
         "7HHTklLpYAzOOx1ZgVljoxAdWNn3hiEFrjZLZGS7lOH-a3QQlDDQoJOJ"
         "2VFmU",
    "q": "te8LY4-W7IyaqH1ExujjMqkTAlTeRbv0VLQnfLY2xINnrWdwiQ93_V"
         "F099aP1ESeLja2nw-6iKIe-qT7mtCPozKfVtUYfz5HrJ_XY2kfexJINb"
         "9lhZHMv5p1skZpeIS-GPHCC6gRlKo1q-idn_qxyusfWv7WAxlSVfQfk8"
         "d6Et0",
    "dp": "UfYKcL_or492vVc0PzwLSplbg4L3-Z5wL48mwiswbpzOyIgd2xHTH"
          "QmjJpFAIZ8q-zf9RmgJXkDrFs9rkdxPtAsL1WYdeCT5c125Fkdg317JV"
          "RDo1inX7x2Kdh8ERCreW8_4zXItuTl_KiXZNU5lvMQjWbIw2eTx1lpsf"
          "lo0rYU",
    "dq": "iEgcO-QfpepdH8FWd7mUFyrXdnOkXJBCogChY6YKuIHGc_p8Le9Mb"
          "pFKESzEaLlN1Ehf3B6oGBl5Iz_ayUlZj2IoQZ82znoUrpa9fVYNot87A"
          "CfzIG7q9Mv7RiPAderZi03tkVXAdaBau_9vs5rS-7HMtxkVrxSUvJY14"
          "TkXlHE",
    "qi": "kC-lzZOqoFaZCr5l0tOVtREKoVqaAYhQiqIRGL-MzS4sCmRkxm5vZ"
          "lXYx6RtE1n_AagjqajlkjieGlxTTThHD8Iga6foGBMaAr5uR1hGQpSc7"
          "Gl7CF1DZkBJMTQN6EshYzZfxW08mIO8M6Rzuh0beL6fG9mkDcIyPrBXx"
          "2bQ_mM"}


class KEMTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config = {
            'server_key': server_key['kid'],
            'signing_algorithm': 'RS256',
            'encryption_algorithms': 'RSA1_5 A128CBC-HS256'}
        with open('examples/client_enc.key') as f:
            data = f.read()
            cls.client_key = json_decode(data)
        cls.kk = KEMKeysStore(config)
        cls.kk.store = SqliteStore({'dburi': 'kemtests.db'})
        cls.kk.store.set(os.path.join('kemkeys', server_key['kid']),
                         json_encode(server_key), True)
        cls.kk.store.set(os.path.join('kemkeys', cls.client_key['kid']),
                         json_encode(cls.client_key), True)

    @classmethod
    def AtearDownClass(self):
        try:
            os.unlink('kemtests.db')
        except OSError:
            pass

    def make_tok(self, key, alg, name):
        pri_key = JWK(**key)
        protected = {"typ": "JOSE+JSON",
                     "kid": key['kid'],
                     "alg": alg}
        plaintext = {"name": name,
                     "time": int(time.time())}
        S = JWS(payload=json_encode(plaintext))
        S.add_signature(pri_key, None, json_encode(protected))
        return S.serialize()

    def test_1_Parse_GET(self):
        cli_key = JWK(**self.client_key)
        jtok = make_sig_kem("mykey", None, cli_key, "RS256")
        kem = KEMHandler({'KEMKeysStore': self.kk})
        kem.parse(jtok)
        out = kem.reply('output')
        jtok = JWT(jwt=json_decode(out)['value'])
        jtok.token.decrypt(cli_key)
        nested = jtok.token.payload
        jtok = JWT(jwt=nested)
        jtok.token.verify(JWK(**server_key))
        payload = json_decode(jtok.token.payload)['value']
        self.assertEqual(payload, 'output')
