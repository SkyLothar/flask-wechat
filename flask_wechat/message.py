import functools
import hashlib
import time
import uuid

try:
    from lxml.etree import ElementTree as ET
except ImportError:
    import xml.etree.cElementTree as ET

from flask import render_template

from . import consts
from .cryptor import cryptor
from . import compat


def encrypt(func):
    @functools.wraps(func)
    def encrypt_message(message, *args, **kwargs):
        msg_type, msg_info = func(message, *args, **kwargs)
        timestamp = int(time.time())
        nonce = uuid.uuid4().hex

        plain_result = render_template(
            "{0}.j2".format(msg_type),
            from_user=message.from_user,
            cropid=cryptor.cropid,
            timestamp=timestamp,
            **msg_info
        )
        encrypted_result = cryptor.encrypt(plain_result)
        signature = cryptor.cal_signature(timestamp, nonce, encrypted_result)
        final_response = render_template(
            "encrypt.j2",
            encrypted=encrypted_result,
            nonce=nonce,
            signature=signature,
            timestamp=timestamp
        )
        return final_response
    return encrypt_message


class WechatMessage(object):
    def __init__(self, request):
        if request.method == "GET":
            encrypted = request.args.get("echostr")
        else:
            encrypted = ET.fromstring(request.data).find("Encrypt").text

        str_to_hash = "".join(sorted([
            cryptor.token,
            encrypted,
            request.args["timestamp"],
            request.args["nonce"]
        ]))

        self._signature = hashlib.sha1(compat.to_bytes(str_to_hash)).hexdigest()
        self._verified = self._signature == request.values[consts.MSG_SIG]
        if self._verified is False:
            return

        self._data = cryptor.decrypt(encrypted)

    @property
    def type(self):
        msg_type = self.xml.find("MsgType").text
        if msg_type == "event":
            msg_type = self.xml.find("Event").text
        if msg_type == "click":
            msg_type = self.xml.find("EventKey").text
        return msg_type

    @property
    def from_user(self):
        return self.xml.find("FromUserName").text

    @property
    def xml(self):
        return ET.fromstring(self.data)

    @property
    def verified(self):
        return self._verified

    @property
    def data(self):
        return self._data

    @property
    def agent_id(self):
        return self.xml.find("AgentID").text

    @property
    def signature(self):
        return self._signature

    @encrypt
    def make_text_response(self, text):
        return "text", dict(text=text)
