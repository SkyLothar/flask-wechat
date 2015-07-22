import json
import time

import requests


from .user import User


def not_implemented(tip):
    def _raise_error(*args, **kwargs):
        raise NotImplementedError(tip)
    return _raise_error


class Qyh(object):
    token_url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
    api_url = "https://qyapi.weixin.qq.com/cgi-bin"
    expires_leeway = 60

    def __init__(self):
        self._auth_params = None

        self._get_token = not_implemented("get_token not defined")
        self._set_token = not_implemented("set_token not defnined")
        self._setuped = False
        self._token = None
        self._expires = None
        self._session = requests.session()

    @property
    def session(self):
        return self._session

    def init_app(self, app):
        self._auth_params = dict(
            corpid=app.config["WECHAT_CROPID"],
            corpsecret=app.config["WECHAT_CROPSECRET"]
        )
        self._setuped = True

    @property
    def auth_params(self):
        if self._auth_params is None:
            raise ValueError("you must setup caller first")
        return self._auth_params

    def token_setter(self, func):
        self._set_token = func
        return func

    def token_getter(self, func):
        self._get_token = func
        return func

    @property
    def token_expired(self):
        return self._expires is None or self._expires < time.time()

    @property
    def token(self):
        if self._token is None:
            self._token, self._expires = self._get_token()
        if self.token_expired:
            self.refresh_token()
        return self._token

    def refresh_token(self):
        res = self.session.get(
            self.api_url + "/gettoken",
            params=self.auth_params
        )
        if res.ok:
            self._expires = int(
                time.time() + res.json()["expires_in"] - self.expires_leeway
            )
            self._token = res.json()["access_token"]
            self._set_token(self._token, self._expires)
        else:
            raise ValueError("refresh token failed")

    def get(self, uri, *args, **kwargs):
        return self._http("get", uri, args, kwargs)

    def post(self, uri, *args, **kwargs):
        return self._http("post", uri, args, kwargs)

    def _http(self, method, uri, args, kwargs):
        url = self.api_url + uri
        params = kwargs.get("params", {})
        params["access_token"] = self.token
        kwargs["params"] = params
        res = getattr(self.session, method)(url, *args, **kwargs)
        res.raise_for_status()
        return res

    def find_user(self, userid):
        res = self.get("/user/get", params=dict(userid=userid))
        return User(self, res.json())

    def send_text_message(self, agent_id, to_user, content):
        # wechat does not support ascii_safe json
        message = json.dumps(
            dict(
                touser=to_user,
                agentid=agent_id,
                msgtype="text",
                text=dict(content=content),
            ),
            ensure_ascii=False
        )
        res = self.post(
            "/message/send",
            data=message.encode("utf8"),
            headers={"content-type": "application/json"}
        )
        if res.ok:
            return res.json()
