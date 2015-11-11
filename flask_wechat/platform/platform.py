import json
import requests

from ..utils import get_n


class Platform(object):
    base_url = "https://api.weixin.qq.com/cgi-bin/"
    session = requests.session()

    def __init__(self, access_token):
        self._access_token = access_token

    def call(self, uri, **kwargs):
        url = requests.compat.urljoin(self.base_url, uri)
        params = kwargs.setdefault("params", {})
        params.update(access_token=self._access_token)

        res = self.session.post(url, **kwargs).json()
        errcode = res.get("errcode", 0)
        if errcode != 0:
            raise ValueError("calling {0} error[{1}]: {2}".format(
                url, errcode, res.get("errmsg")
            ))
        return res

    def get_material_count(self):
        return self.call("material/get_materialcount")

    def get_material(self, media_id):
        return self.call("material/get_material", json=dict(media_id=media_id))

    def upload_material(self, material_type, data, temporary):
        uri = "media/upload" if temporary else "material/add_material"
        return self.call(
            uri,
            json={"type": material_type}, files={"media": data}
        )

    def upload_thumb(self, data, temporary=False):
        return self.upload_material("thumb", data, temporary)["media_id"]

    def upload_image(self, data, temporary=False):
        return self.upload_material("image", data, temporary)["url"]

    def upload_news(self, news):
        # wechat has poor utf8 json support
        data = json.dumps(dict(articles=news), ensure_ascii=False)
        return self.call(
            "material/add_news",
            data=data.encode("utf8"),
            headers={"content-type": "application/json"}
        )["media_id"]

    def preview_news(self, openid, news_id):
        return self.call(
            "message/mass/preview",
            json=dict(
                touser=openid,
                mpnews=dict(media_id=news_id),
                msgtype="mpnews"
            )
        )

    def get_all_subscriber_info(self):
        yield from self.get_subscriber_info(self.get_subscribers())

    def get_subscribers(self, next_openid=None):
        """*Iterator*
        """
        res = self.call("user/get", json=dict(next_openid=next_openid))
        for openid in res["data"]["openid"]:
            yield openid
        # wechat claims that next_openid will be empty if no more data is
        # availeble, but it's not true
        # 10000 is wechat max return, if count < 10000, there's no more data
        if res["count"] < 10000 or res["total"] == 10000:
            return
        yield from self.get_subscribers(res["next_openid"])

    def get_subscriber_info(self, subscribers, lang="zh_CN"):
        """*Iterator*
        can take str, list, tuple or generator
        """
        if isinstance(subscribers, str):
            subscribers = iter([subscribers])
        elif isinstance(subscribers, (list, tuple)):
            subscribers = iter(subscribers)

        part = get_n(subscribers, 100)
        for openids in part:
            res = self.call(
                "user/info/batchget",
                json=dict(
                    user_list=[
                        dict(openid=openid, lang=lang) for openid in openids
                    ]
                )
            )
            for info in res["user_info_list"]:
                yield info["openid"], info
