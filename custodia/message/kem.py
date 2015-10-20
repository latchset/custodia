# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

import logging
import os
import time
import unittest

from jwcrypto.common import json_decode
from jwcrypto.common import json_encode
from jwcrypto.jwe import JWE
from jwcrypto.jwk import JWK
from jwcrypto.jws import JWS
from jwcrypto.jwt import JWT

from custodia.httpd.authorizers import SimplePathAuthz
from custodia.message.common import InvalidMessage
from custodia.message.common import MessageHandler
from custodia.store.sqlite import SqliteStore

logger = logging.getLogger(__name__)

KEY_USAGE_SIG = 0
KEY_USAGE_ENC = 1
KEY_USAGE_MAP = {KEY_USAGE_SIG: 'sig', KEY_USAGE_ENC: 'enc'}


class UnknownPublicKey(Exception):
    def __init__(self, message=None):
        logger.debug(message)
        super(UnknownPublicKey, self).__init__(message)


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
        self._server_keys = None
        self._alg = None
        self._enc = None

    def _db_key(self, kid):
        return os.path.join('kemkeys', kid)

    def handle(self, request):
        inpath = super(KEMKeysStore, self).handle(request)
        if inpath:
            request['KEMKeysStore'] = self
        return inpath

    def find_key(self, kid, usage):
        dbkey = self._db_key('%s/%s' % (KEY_USAGE_MAP[usage], kid))
        pubkey = self.store.get(dbkey)
        if pubkey is None:
            raise UnknownPublicKey(kid)
        return pubkey

    @property
    def server_keys(self):
        if self._server_keys is None:
            if 'server_keys' not in self.config:
                raise UnknownPublicKey("Server Keys not defined")
            skey = self.find_key(self.config['server_keys'], KEY_USAGE_SIG)
            ekey = self.find_key(self.config['server_keys'], KEY_USAGE_ENC)
            self._server_keys = [JWK(**(json_decode(skey))),
                                 JWK(**(json_decode(ekey)))]
        return self._server_keys

    @property
    def alg(self):
        if self._alg is None:
            alg = self.config.get('signing_algorithm', None)
            if alg is None:
                ktype = self.server_keys[KEY_USAGE_SIG].key_type
                if ktype == 'RSA':
                    alg = 'RS256'
                elif ktype == 'EC':
                    alg = 'ES256'
                else:
                    raise ValueError('Key type unsupported for signing')
            self._alg = alg
        return self._alg


def check_kem_claims(claims, name):
    if 'sub' not in claims:
        raise InvalidMessage('Missing subject in payload')
    if claims['sub'] != name:
        raise InvalidMessage('Key name %s does not match subject %s' % (
            name, claims['sub']))
    if 'exp' not in claims:
        raise InvalidMessage('Missing expiration time in payload')
    if claims['exp'] - (10 * 60) > int(time.time()):
        raise InvalidMessage('Message expiration too far in the future')
    if claims['exp'] < int(time.time()):
        raise InvalidMessage('Message Expired')


class KEMHandler(MessageHandler):
    """Handles 'kem' messages"""

    def __init__(self, request):
        super(KEMHandler, self).__init__(request)
        self.kkstore = self.req.get('KEMKeysStore', None)
        if self.kkstore is None:
            raise Exception('KEM KeyStore not configured')
        self.client_keys = None
        self.name = None

    def _get_key(self, header, usage):
        if 'kid' not in header:
            raise InvalidMessage("Missing key identifier")

        key = self.kkstore.find_key(header['kid'], usage)
        if key is None:
            raise UnknownPublicKey('Key found [kid:%s]' % header['kid'])
        return json_decode(key)

    def parse(self, msg, name):
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
            if isinstance(token, JWE):
                token.decrypt(self.kkstore.server_keys[KEY_USAGE_ENC])
                # If an encrypted payload is received then there must be
                # a nested signed payload to verify the provenance.
                payload = token.payload.decode('utf-8')
                token = JWS()
                token.deserialize(payload)
            elif isinstance(token, JWS):
                pass
            else:
                raise TypeError("Invalid Token type: %s" % type(jtok))

            # Retrieve client keys for later use
            self.client_keys = [
                JWK(**self._get_key(token.jose_header, KEY_USAGE_SIG)),
                JWK(**self._get_key(token.jose_header, KEY_USAGE_ENC))]

            # verify token and get payload
            token.verify(self.client_keys[KEY_USAGE_SIG])
            claims = json_decode(token.payload)
        except Exception as e:
            raise InvalidMessage('Failed to validate message: %s' % str(e))

        check_kem_claims(claims, name)
        self.name = name

        return {'type': 'kem',
                'value': {'kid': self.client_keys[KEY_USAGE_ENC].key_id,
                          'claims': claims}}

    def reply(self, output):
        if self.client_keys is None:
            raise UnknownPublicKey("Peer key not defined")

        ktype = self.client_keys[KEY_USAGE_ENC].key_type
        if ktype == 'RSA':
            enc = ('RSA1_5', 'A256CBC-HS512')
        else:
            raise ValueError("'%s' type not supported yet" % ktype)

        value = make_enc_kem(self.name, output,
                             self.kkstore.server_keys[KEY_USAGE_SIG],
                             self.kkstore.alg,
                             self.client_keys[1], enc)

        return json_encode({'type': 'kem', 'value': value})


class KEMClient(object):

    def __init__(self, server_keys, client_keys):
        self.server_keys = server_keys
        self.client_keys = client_keys

    def make_request(self, name, value=None, alg="RS256", encalg=None):
        if encalg is None:
            return make_sig_kem(name, value,
                                self.client_keys[KEY_USAGE_SIG], alg)
        else:
            return make_enc_kem(name, value,
                                self.client_keys[KEY_USAGE_SIG], alg,
                                self.server_keys[KEY_USAGE_ENC], encalg)

    def parse_reply(self, name, message):
        jwe = JWT(jwt=message,
                  key=self.client_keys[KEY_USAGE_ENC])
        jws = JWT(jwt=jwe.claims,
                  key=self.server_keys[KEY_USAGE_SIG])
        claims = json_decode(jws.claims)
        check_kem_claims(claims, name)
        return claims['value']


def make_sig_kem(name, value, key, alg):
    header = {'kid': key.key_id, 'alg': alg}
    claims = {'sub': name, 'exp': int(time.time() + (5 * 60))}
    if value is not None:
        claims['value'] = value
    jwt = JWT(header, claims)
    jwt.make_signed_token(key)
    return jwt.serialize(compact=True)


def make_enc_kem(name, value, sig_key, alg, enc_key, enc):
    plaintext = make_sig_kem(name, value, sig_key, alg)
    eprot = {'kid': enc_key.key_id, 'alg': enc[0], 'enc': enc[1]}
    jwe = JWE(plaintext, json_encode(eprot))
    jwe.add_recipient(enc_key)
    return jwe.serialize(compact=True)


# unit tests
test_keys = ({
    "kty": "RSA",
    "kid": "65d64463-7448-499e-8acc-55db2ce67039",
    "use": "sig",
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
          "2bQ_mM"}, {
    "kty": "RSA",
    "kid": "65d64463-7448-499e-8acc-55db2ce67039",
    "use": "enc",
    "n": "t6Q8PWSi1dkJj9hTP8hNYFlvadM7DflW9mWepOJhJ66w7nyoK1gPNq"
         "FMSQRyO125Gp-TEkodhWr0iujjHVx7BcV0llS4w5ACGgPrcAd6ZcSR"
         "0-Iqom-QFcNP8Sjg086MwoqQU_LYywlAGZ21WSdS_PERyGFiNnj3QQ"
         "lO8Yns5jCtLCRwLHL0Pb1fEv45AuRIuUfVcPySBWYnDyGxvjYGDSM-"
         "AqWS9zIQ2ZilgT-GqUmipg0XOC0Cc20rgLe2ymLHjpHciCKVAbY5-L"
         "32-lSeZO-Os6U15_aXrk9Gw8cPUaX1_I8sLGuSiVdt3C_Fn2PZ3Z8i"
         "744FPFGGcG1qs2Wz-Q",
    "e": "AQAB",
    "d": "GRtbIQmhOZtyszfgKdg4u_N-R_mZGU_9k7JQ_jn1DnfTuMdSNprTea"
         "STyWfSNkuaAwnOEbIQVy1IQbWVV25NY3ybc_IhUJtfri7bAXYEReWa"
         "Cl3hdlPKXy9UvqPYGR0kIXTQRqns-dVJ7jahlI7LyckrpTmrM8dWBo"
         "4_PMaenNnPiQgO0xnuToxutRZJfJvG4Ox4ka3GORQd9CsCZ2vsUDms"
         "XOfUENOyMqADC6p1M3h33tsurY15k9qMSpG9OX_IJAXmxzAh_tWiZO"
         "wk2K4yxH9tS3Lq1yX8C1EWmeRDkK2ahecG85-oLKQt5VEpWHKmjOi_"
         "gJSdSgqcN96X52esAQ",
    "p": "2rnSOV4hKSN8sS4CgcQHFbs08XboFDqKum3sc4h3GRxrTmQdl1ZK9u"
         "w-PIHfQP0FkxXVrx-WE-ZEbrqivH_2iCLUS7wAl6XvARt1KkIaUxPP"
         "SYB9yk31s0Q8UK96E3_OrADAYtAJs-M3JxCLfNgqh56HDnETTQhH3r"
         "CT5T3yJws",
    "q": "1u_RiFDP7LBYh3N4GXLT9OpSKYP0uQZyiaZwBtOCBNJgQxaj10RWjs"
         "Zu0c6Iedis4S7B_coSKB0Kj9PaPaBzg-IySRvvcQuPamQu66riMhjV"
         "tG6TlV8CLCYKrYl52ziqK0E_ym2QnkwsUX7eYTB7LbAHRK9GqocDE5"
         "B0f808I4s",
    "dp": "KkMTWqBUefVwZ2_Dbj1pPQqyHSHjj90L5x_MOzqYAJMcLMZtbUtwK"
          "qvVDq3tbEo3ZIcohbDtt6SbfmWzggabpQxNxuBpoOOf_a_HgMXK_l"
          "hqigI4y_kqS1wY52IwjUn5rgRrJ-yYo1h41KR-vz2pYhEAeYrhttW"
          "txVqLCRViD6c",
    "dq": "AvfS0-gRxvn0bwJoMSnFxYcK1WnuEjQFluMGfwGitQBWtfZ1Er7t1"
          "xDkbN9GQTB9yqpDoYaN06H7CFtrkxhJIBQaj6nkF5KKS3TQtQ5qCz"
          "kOkmxIe3KRbBymXxkb5qwUpX5ELD5xFc6FeiafWYY63TmmEAu_lRF"
          "COJ3xDea-ots",
    "qi": "lSQi-w9CpyUReMErP1RsBLk7wNtOvs5EQpPqmuMvqW57NBUczScEo"
          "PwmUqqabu9V0-Py4dQ57_bapoKRu1R90bvuFnU63SHWEFglZQvJDM"
          "eAvmj4sm-Fp0oYu_neotgQ0hzbI5gry7ajdYy9-2lNx_76aBZoOUu"
          "9HCJ-UsfSOI8"})


def _store_keys(keystore, usage, keys):
    name = os.path.join('kemkeys',
                        KEY_USAGE_MAP[usage],
                        keys[usage]['kid'])
    keystore.set(name, json_encode(keys[usage]), True)


class KEMTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        config = {'server_keys': test_keys[0]['kid']}
        with open('examples/client_enc.key') as f:
            data = f.read()
            cls.client_keys = json_decode(data)
        cls.kk = KEMKeysStore(config)
        cls.kk.store = SqliteStore({'dburi': 'kemtests.db'})
        _store_keys(cls.kk.store, KEY_USAGE_SIG, test_keys)
        _store_keys(cls.kk.store, KEY_USAGE_ENC, test_keys)
        _store_keys(cls.kk.store, KEY_USAGE_SIG, cls.client_keys)
        _store_keys(cls.kk.store, KEY_USAGE_ENC, cls.client_keys)

    @classmethod
    def tearDownClass(cls):
        try:
            os.unlink('kemtests.db')
        except OSError:
            pass

    def make_tok(self, key, alg, name):
        pri_key = JWK(**key)
        protected = {"typ": "JOSE+JSON",
                     "kid": key['kid'],
                     "alg": alg}
        plaintext = {"sub": name,
                     "exp": int(time.time()) + (5 * 60)}
        jws = JWS(payload=json_encode(plaintext))
        jws.add_signature(pri_key, None, json_encode(protected))
        return jws.serialize()

    def test_1_Parse_GET(self):
        cli_skey = JWK(**self.client_keys[0])
        jtok = make_sig_kem("mykey", None, cli_skey, "RS256")
        kem = KEMHandler({'KEMKeysStore': self.kk})
        kem.parse(jtok, "mykey")
        out = kem.reply('output')
        jtok = JWT(jwt=json_decode(out)['value'])
        cli_ekey = JWK(**self.client_keys[1])
        jtok.token.decrypt(cli_ekey)
        nested = jtok.token.payload
        jtok = JWT(jwt=nested.decode('utf-8'))
        jtok.token.verify(JWK(**test_keys[0]))
        payload = json_decode(jtok.token.payload)['value']
        self.assertEqual(payload, 'output')

    def test_2_KEMClient(self):
        server_keys = [JWK(**test_keys[KEY_USAGE_SIG]), None]
        client_keys = [JWK(**self.client_keys[KEY_USAGE_SIG]),
                       JWK(**self.client_keys[KEY_USAGE_ENC])]
        cli = KEMClient(server_keys, client_keys)
        kem = KEMHandler({'KEMKeysStore': self.kk})
        req = cli.make_request("key name")
        kem.parse(req, "key name")
        msg = json_decode(kem.reply('key value'))
        rep = cli.parse_reply("key name", msg['value'])
        self.assertEqual(rep, 'key value')

    def test_3_KEMClient(self):
        server_keys = [JWK(**test_keys[KEY_USAGE_SIG]),
                       JWK(**test_keys[KEY_USAGE_ENC])]
        client_keys = [JWK(**self.client_keys[KEY_USAGE_SIG]),
                       JWK(**self.client_keys[KEY_USAGE_ENC])]
        cli = KEMClient(server_keys, client_keys)
        kem = KEMHandler({'KEMKeysStore': self.kk})
        req = cli.make_request("key name", encalg=('RSA1_5', 'A256CBC-HS512'))
        kem.parse(req, "key name")
        msg = json_decode(kem.reply('key value'))
        rep = cli.parse_reply("key name", msg['value'])
        self.assertEqual(rep, 'key value')
