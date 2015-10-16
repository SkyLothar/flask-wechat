import hashlib
import time
import uuid


from .compat import ET, to_bytes
from .utils import snake_to_camel, render_template


class WechatMessage(object):
    def __init__(self, cipher, request):
        self.cipher = cipher

        signature = request.values.get("msg_signature")
        self._encrypted = signature is not None

        self._reason = None
        self._data = None
        self._xml = None
        self._cache = {}

        hash_list = [
            cipher.token, request.args["timestamp"], request.args["nonce"]
        ]

        if request.method == "GET":
            payload = request.values["echostr"]
            if not self._encrypted:
                # for legcay wechat platform compatibility
                signature = request.values["signature"]
        elif self._encrypted:
            # POST and encrypted
            e_element = ET.fromstring(request.data).find("Encrypt")
            if e_element is None:
                self._reason = "missing `Encrypt`"
                return
            payload = e_element.text
            hash_list.append(payload)
        else:
            # POST and not encrypted (legacy wechat)
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
    def msg_type(self):
        msg_type = self.xml.find("MsgType").text
        if msg_type == "event":
            msg_type = self.xml.find("Event").text
        if msg_type == "click":
            msg_type = self.xml.find("EventKey").text
        return msg_type

    def __getattr__(self, attr):
        if attr in self._cache:
            return self._cache[attr]

        element = self.xml.find(snake_to_camel(attr))
        if element is not None:
            self._cache[attr] = element.text
            return element.text
        raise AttributeError(
            "{0} has no attribute {1}".format(self.__class__, attr)
        )

    @property
    def msg_id(self):
        msgid = self.xml.find("MsgId")
        if msgid is None:
            return "{0}-{1}@{2}".format(
                self.from_user_name, self.msg_type, self.create_time
            )
        else:
            return msgid.text

    @property
    def xml(self):
        if self._xml is None:
            self._xml = ET.fromstring(self.data)
        return self._xml

    @property
    def data(self):
        return self._data

    @property
    def signature(self):
        return self._signature

    def make_text_response(self, text):
        return self.render("text", text=text)

    def render(self, msg_type, **msg_info):
        nonce = uuid.uuid4().hex
        timestamp = int(time.time())

        plain_result = render_template(
            "{0}.j2".format(msg_type),
            from_user=self.from_user_name,
            to_user=self.to_user_name,
            timestamp=timestamp,
            **msg_info
        )
        if not self.encrypted:
            return plain_result

        encrypted_result = self.cipher.encrypt(plain_result)
        signature = self.cipher.cal_signature(
            timestamp, nonce, encrypted_result
        )
        final_response = render_template(
            "encrypt.j2",
            encrypted=encrypted_result, signature=signature,
            nonce=nonce, timestamp=timestamp
        )
        return final_response
