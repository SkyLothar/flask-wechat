import json

import requests


class QYHMixin(object):
    api_url = "https://qyapi.weixin.qq.com/cgi-bin/"
    session = requests.session()

    @property
    def auth_params(self):
        """{cropid: "cropid", "cropsecret": "cropsecret"}"""
        raise NotImplementedError()

    @property
    def access_token(self):
        raise NotImplementedError()

    def set_access_token(self, token, expires_in):
        raise NotImplementedError()

    def refresh_token(self):
        res = self.get("gettoken", params=self.auth_params)
        self.set_token(res["access_token"], res["expires_in"])

    def get(self, uri, *args, **kwargs):
        return self.call("get", uri, args, kwargs)

    def post(self, uri, *args, **kwargs):
        return self.call("post", uri, args, kwargs)

    def call(self, method, uri, kwargs):
        url = "/".join([self.api_url.rstrip("/"), uri.lstrip("/")])
        params = kwargs.pop("params", {})
        params["access_token"] = self.access_token
        res = getattr(self.session, method)(url, params=params, **kwargs)
        return res.json(strict=False)

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

    def send_text_message(self, agent_id, content, to_user=None):
        return self.send(
            agent_id, "text",
            to_user=to_user, text=content
        )

    def send_news(self, agent_id, to_user, *articles):
        return self.send(
            agent_id, "news",
            to_user=to_user, news=dict(articles=articles)
        )
