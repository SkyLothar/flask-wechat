import base64
import functools
import hashlib
import socket
import struct
import string
import random

from Crypto.Cipher import AES

from . import consts
from . import compat


def setup_first(func):
    @functools.wraps(func)
    def check_setup(cryptor, *args, **kwargs):
        if cryptor._setuped is False:
            raise ValueError("cryptor not setuped yet")
        return func(cryptor, *args, **kwargs)
    return check_setup


class WechatCryptor(object):
    random_pool = string.ascii_letters + string.punctuation + string.digits
    block_size = 32
    mode = AES.MODE_CBC

    def __init__(self):
        self._key = None
        self._cropid = None
        self._token = None
        self._setuped = False

    @property
    @setup_first
    def key(self):
        return self._key

    @property
    @setup_first
    def init_vec(self):
        """first 16 bytes are init vector"""
        return self.key[:16]

    @property
    @setup_first
    def cropid(self):
        return self._cropid

    @property
    @setup_first
    def token(self):
        return self._token

    def init_app(self, app):
        self._key = compat.to_bytes(
            base64.b64decode(app.config["WECHAT_AESKEY"] + "=")
        )
        self._cropid = app.config["WECHAT_CROPID"]
        self._token = app.config["WECHAT_TOKEN"]
        self._setuped = True

    def cal_signature(self, timestamp, nonce, encrypted):
        str_to_sign = "".join(sorted([
            self.token,
            compat.to_str(timestamp),
            nonce,
            encrypted
        ]))
        signature = hashlib.sha1(compat.to_bytes(str_to_sign)).hexdigest()
        return signature

    @setup_first
    def decrypt(self, secret_msg):
        cryptor = self.get_aes_cryptor()
        message = cryptor.decrypt(base64.b64decode(secret_msg))
        # last byte indicates padding lenth
        padding = int(message[-1])
        # first PREFIX_LEN bytes are random data, drop them and padding suffix
        content = message[consts.PREFIX_LEN: -padding]
        # first 4 bytes of content is message size, (in network order)
        message_size = socket.ntohl(struct.unpack("I", content[:4])[0])
        # the following (message_size) bytes are data
        payload = compat.to_str(content[4: 4 + message_size])
        # the rest of them is cropid
        cropid = compat.to_str(content[4 + message_size:])
        if cropid != self.cropid:
            raise ValueError(
                "cropid mismatched: received cropid [{0}]".format(cropid)
            )
        return payload

    @setup_first
    def encrypt(self, text):
        text = compat.to_bytes(text)
        random_data = "".join([
            random.choice(self.random_pool)
            for __ in range(consts.PREFIX_LEN)
        ])
        data = b"".join([
            compat.to_bytes(random_data),
            struct.pack("I", socket.htonl(len(text))),  # message length
            text,  # message
            compat.to_bytes(self.cropid)
        ])
        amount = self.block_size - len(data) % self.block_size
        padding = compat.to_bytes(chr(amount)) * amount
        message = data + padding
        cryptor = self.get_aes_cryptor()
        encrypted = cryptor.encrypt(message)
        encoded = base64.b64encode(encrypted)
        return compat.to_str(encoded)

    @setup_first
    def get_aes_cryptor(self):
        return AES.new(self.key, self.mode, self.key[:16])


cryptor = WechatCryptor()
