import json
import time

import requests

from .user import User


class Qyh(object):
    api_url = "https://qyapi.weixin.qq.com/cgi-bin/"
    expires_leeway = 60

    def __init__(
        self,
        cropid=None, cropsecret=None,
        cache=None, cache_prefix=None
    ):
        self.init(cropid, cropsecret, cache, cache_prefix)
        self._token = None
        self._expires = None
        self._session = requests.session()

    def init(self, cropid, cropsecret, cache, cache_prefix="qyh"):
        self._auth_params = dict(corpid=cropid, corpsecret=cropsecret)
        self._cachekey = "-".join([cache_prefix, cropid])
        self.cache = cache

    @property
    def cachekey(self):
        return self._cachekey

    @property
    def auth_params(self):
        return self._auth_params.copy()

    def get_token(self):
        cached = self.cache.get(self.cachekey)
        if cached is None:
            return (None, None)
        return self._token, self._expires

    def set_token(self, token, expires_in):
        expires_in = expires_in - self.expires_leeway
        expires = int(time.time() + expires_in)

        self._token = token
        self._expires = expires

        self.cache.set((token, expires), expires_in)

    @property
    def token_expired(self):
        return self._expires is None or self._expires < time.time()

    @property
    def token(self):
        if self._token is None:
            self.get_token()
        if self.token_expired:
            self.refresh_token()
        return self._token

    def refresh_token(self):
        res = self.get("gettoken", params=self.auth_params)
        self.set_token(res["access_token"], res["expires_in"])

    def get(self, uri, *args, **kwargs):
        return self.call("get", uri, args, kwargs)

    def post(self, uri, *args, **kwargs):
        return self.call("post", uri, args, kwargs)

    def call(self, method, uri, args, kwargs):
        url = requests.compat.urljoin(self.api_url, uri)

        params = kwargs.setdefault("params", {})
        params["access_token"] = self.token
        res = getattr(self.session, method)(url, *args, **kwargs)
        res.raise_for_status()
        return res.json()

    def find_user(self, userid):
        res = self.get("/user/get", params=dict(userid=userid))
        return User(self, res.json())

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
        res = self.post(
            "/message/send",
            data=message.encode("utf8"),
            headers={"content-type": "application/json"}
        )
        if res.ok:
            return res.json()

    def send_text_message(self, agent_id, content, to_user=None):
        return self.send(
            agent_id, "text",
            to_user=to_user, text=content
        )

    def send_news(self, agent_id, articles, to_user=None):
        return self.send(
            agent_id, "news",
            to_user=to_user, news=dict(articles=articles)
        )
