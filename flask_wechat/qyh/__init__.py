import json

import requests


class QYHMixin(object):
    api_url = "https://qyapi.weixin.qq.com/cgi-bin/"
    session = requests.session()

    @property
    def auth_params(self):
        """{cropid: "cropid", "cropsecret": "cropsecret"}"""
        raise NotImplementedError()

    def get_access_token(self):
        raise NotImplementedError("you must implement get_access_token")

    def set_access_token(self, token, expires_in):
        raise NotImplementedError("you must implement set_access_token")

    @property
    def access_token(self):
        return self.get_access_token() or self.refresh_access_token()

    def refresh_access_token(self):
        res = self.get("gettoken", params=self.auth_params)
        token = res["access_token"]
        self.set_access_token(token, res["expires_in"])
        return token

    def get(self, uri, **kwargs):
        return self.call("get", uri, kwargs)

    def post(self, uri, **kwargs):
        return self.call("post", uri, kwargs)

    def call(self, method, uri, kwargs):
        url = "/".join([self.api_url.rstrip("/"), uri.lstrip("/")])
        params = kwargs.pop("params", {})
        if uri != "gettoken":
            params["access_token"] = self.access_token
        res = getattr(self.session, method)(url, params=params, **kwargs)
        resjson = res.json(strict=False)
        if resjson.get("errcode", 0) != 0:
            raise ValueError("calling {0} error: {1}".format(
                uri, resjson.get("errmsg") or res.text
            ))
        return resjson

    def find_user(self, userid):
        return self.get("user/get", params=dict(userid=userid))

    def send(self, agent_id, msgtype, **message):
        message = json.dumps(
            dict(
                touser=message.pop("touser", None) or "@all",
                agentid=agent_id,
                msgtype=msgtype,
                **message
            ),
            # wechat does not support ascii_safe json
            ensure_ascii=False
        )
        return self.post("message/send", json=message.encode("utf8"))

    def send_text_message(self, agent_id, to_user, content):
        return self.send(
            agent_id, "text",
            to_user=to_user, text=content
        )

    def send_news(self, agent_id, to_user, *articles):
        return self.send(
            agent_id, "news",
            to_user=to_user, news=dict(articles=articles)
        )
