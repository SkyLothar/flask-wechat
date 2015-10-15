import functools
import hashlib
import time
import uuid


from flask import render_template

from .cipher import cipher
from .compat import ET, to_bytes


def encrypt(func):
    @functools.wraps(func)
    def encrypt_message(message, *args, **kwargs):
        msg_type, msg_info = func(message, *args, **kwargs)
        nonce = uuid.uuid4().hex
        timestamp = int(time.time())

        plain_result = render_template(
            "{0}.j2".format(msg_type),
            from_user=message.from_user,
            to_user=message.to_user,
            timestamp=timestamp,
            **msg_info
        )
        if not message.encrypted:
            return plain_result

        encrypted_result = cipher.encrypt(plain_result)
        signature = cipher.cal_signature(timestamp, nonce, encrypted_result)
        final_response = render_template(
            "encrypt.j2",
            encrypted=encrypted_result, signature=signature,
            nonce=nonce, timestamp=timestamp
        )
        return final_response
    return encrypt_message


class WechatMessage(object):
    def __init__(self, request):
        signature = request.values.get("msg_signature")
        self._encrypted = signature is not None

        self._reason = None
        self._data = None
        self._xml = None

        hash_list = [
            cipher.token, request.args["timestamp"], request.args["nonce"]
        ]

        if request.method == "GET":
            payload = request.values["echostr"]
            if not self._encrypted:
                # for legcay wechat platform compatibility
                signature = request.values["signature"]
        elif self._encrypted:
            e_element = ET.fromstring(request.data).find("Encrypt")
            if e_element is None:
                self._reason = "missing `Encrypt`"
            payload = e_element.text
            hash_list.append(payload)
        else:
            payload = request.data
            signature = request.values["signature"]

        str_to_hash = "".join(sorted(hash_list))
        calculated = hashlib.sha1(to_bytes(str_to_hash)).hexdigest()

        if calculated != signature:
            self._reason = "signature mismatch"
            return

        if self._encrypted:
            self._data = cipher.decrypt(payload)
        else:
            self._data = payload

    @property
    def encrypted(self):
        return self._encrypted

    @property
    def verified(self):
        return self._reason is None

    @property
    def reason(self):
        return self._reason

    @property
    def type(self):
        msg_type = self.xml.find("MsgType").text
        if msg_type == "event":
            msg_type = self.xml.find("Event").text
        if msg_type == "click":
            msg_type = self.xml.find("EventKey").text
        return msg_type

    @property
    def msgid(self):
        msgid = self.xml.find("MsgId")
        if msgid is None:
            return "{0}-{1}@{2}".format(
                self.from_user, self.type, self.create_time
            )
        else:
            return msgid.text

    @property
    def from_user(self):
        return self.xml.find("FromUserName").text

    @property
    def to_user(self):
        return self.xml.find("ToUserName").text

    @property
    def xml(self):
        if self._xml is None:
            self._xml = ET.fromstring(self.data)
        return self._xml

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
