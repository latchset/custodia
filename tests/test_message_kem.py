# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

import os
import time
import unittest

from jwcrypto.common import json_decode
from jwcrypto.common import json_encode
from jwcrypto.jwk import JWK
from jwcrypto.jws import JWS
from jwcrypto.jwt import JWT

from custodia.compat import configparser
from custodia.message import kem
from custodia.store.sqlite import SqliteStore


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
                        kem.KEY_USAGE_MAP[usage],
                        keys[usage]['kid'])
    keystore.set(name, json_encode(keys[usage]), True)


CONFIG = u"""
[store:sqlite]
dburi = kemtests.db
"""


class KEMTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.parser = configparser.ConfigParser(
            interpolation=configparser.ExtendedInterpolation()
        )
        cls.parser.read_string(CONFIG)

        config = {'server_keys': test_keys[0]['kid']}
        with open('examples/client_enc.key') as f:
            data = f.read()
            cls.client_keys = json_decode(data)

        cls.kk = kem.KEMKeysStore(config)
        cls.kk.store = SqliteStore(cls.parser, 'store:sqlite')

        _store_keys(cls.kk.store, kem.KEY_USAGE_SIG, test_keys)
        _store_keys(cls.kk.store, kem.KEY_USAGE_ENC, test_keys)
        _store_keys(cls.kk.store, kem.KEY_USAGE_SIG, cls.client_keys)
        _store_keys(cls.kk.store, kem.KEY_USAGE_ENC, cls.client_keys)

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
        jtok = kem.make_sig_kem("mykey", None, cli_skey, "RS256")
        kh = kem.KEMHandler({'KEMKeysStore': self.kk})
        kh.parse(jtok, "mykey")
        msg = kh.reply('output')
        self.assertEqual(msg, json_decode(json_encode(msg)))
        jtok = JWT(jwt=msg['value'])
        cli_ekey = JWK(**self.client_keys[1])
        jtok.token.decrypt(cli_ekey)
        nested = jtok.token.payload
        jtok = JWT(jwt=nested.decode('utf-8'))
        jtok.token.verify(JWK(**test_keys[0]))
        payload = json_decode(jtok.token.payload)['value']
        self.assertEqual(payload, 'output')

    def test_2_KEMClient(self):
        server_keys = [JWK(**test_keys[kem.KEY_USAGE_SIG]), None]
        client_keys = [JWK(**self.client_keys[kem.KEY_USAGE_SIG]),
                       JWK(**self.client_keys[kem.KEY_USAGE_ENC])]
        cli = kem.KEMClient(server_keys, client_keys)
        kh = kem.KEMHandler({'KEMKeysStore': self.kk})
        req = cli.make_request("key name")
        kh.parse(req, "key name")
        msg = kh.reply('key value')
        self.assertEqual(msg, json_decode(json_encode(msg)))
        rep = cli.parse_reply("key name", msg['value'])
        self.assertEqual(rep, 'key value')

    def test_3_KEMClient(self):
        server_keys = [JWK(**test_keys[kem.KEY_USAGE_SIG]),
                       JWK(**test_keys[kem.KEY_USAGE_ENC])]
        client_keys = [JWK(**self.client_keys[kem.KEY_USAGE_SIG]),
                       JWK(**self.client_keys[kem.KEY_USAGE_ENC])]
        cli = kem.KEMClient(server_keys, client_keys)
        kh = kem.KEMHandler({'KEMKeysStore': self.kk})
        req = cli.make_request("key name",
                               encalg=('RSA-OAEP', 'A256CBC-HS512'))
        kh.parse(req, "key name")
        msg = kh.reply('key value')
        self.assertEqual(msg, json_decode(json_encode(msg)))
        rep = cli.parse_reply("key name", msg['value'])
        self.assertEqual(rep, 'key value')

    def test_4_KEMClient_SET(self):
        server_keys = [JWK(**test_keys[kem.KEY_USAGE_SIG]), None]
        client_keys = [JWK(**self.client_keys[kem.KEY_USAGE_SIG]),
                       JWK(**self.client_keys[kem.KEY_USAGE_ENC])]
        cli = kem.KEMClient(server_keys, client_keys)
        kh = kem.KEMHandler({'KEMKeysStore': self.kk})
        req = cli.make_request("key name", "key value")
        kh.parse(req, "key name")
        self.assertEqual(kh.payload, "key value")
