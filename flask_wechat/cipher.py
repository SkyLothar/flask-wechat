import base64
import hashlib
import random
import socket
import struct
import string

from Crypto.Cipher import AES

from .compat import to_bytes, to_str


class WechatCipher(object):
    random_pool = string.ascii_letters + string.punctuation + string.digits
    block_size = 32
    prefix_len = 16
    vector_len = 16
    mode = AES.MODE_CBC

    def __init__(self, appid=None, token=None, aeskey=None):
        self.init_cipher(appid, token, aeskey)

    def init_cipher(self, appid, token, aeskey=None):
        self.appid = appid
        self.token = token
        if aeskey is None:
            self.cipher = None
        else:
            key = to_bytes(base64.b64decode(aeskey + "="))
            # the first 16 bytes of key are init vector
            init_vec = key[:self.vector_len]
            self.cipher = AES.new(key, self.mode, init_vec)

    def cal_signature(self, timestamp, nonce, encrypted):
        str_to_sign = "".join(sorted([
            self.token,
            to_str(timestamp),
            nonce,
            encrypted
        ]))
        signature = hashlib.sha1(to_bytes(str_to_sign)).hexdigest()
        return signature

    def decrypt(self, secret_msg):
        message = self.cipher.decrypt(base64.b64decode(secret_msg))
        # last byte indicates padding length
        padding = int(message[-1])
        # first prefix_len bytes are random data, drop padding data and those
        content = message[self.prefix_len: -padding]
        # first 4 bytes of content is message size, (in network order)
        message_size = socket.ntohl(struct.unpack("I", content[:4])[0])
        # the following (message_size) bytes are data
        payload = to_str(content[4: 4 + message_size])
        # the rest of them is appid
        appid = to_str(content[4 + message_size:])
        if appid != self.appid:
            raise ValueError(
                "appid mismatched: received appid is [{0}]".format(appid)
            )
        return payload

    def encrypt(self, message):
        message = to_bytes(message)
        random_data = "".join([
            random.choice(self.random_pool)
            for __ in range(self.prefix_len)
        ])
        data = b"".join([
            to_bytes(random_data),
            struct.pack("I", socket.htonl(len(message))),  # message length
            message,  # message
            to_bytes(self.appid)
        ])
        amount = self.block_size - len(data) % self.block_size
        padding = to_bytes(chr(amount)) * amount
        payload = data + padding
        encrypted = self.cipher.encrypt(payload)
        encoded = base64.b64encode(encrypted)
        return to_str(encoded)
