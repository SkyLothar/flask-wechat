from collections import defaultdict
from itertools import islice

import json
import requests


class Platform(object):
    base_url = "https://api.weixin.qq.com"
    session = requests.session()

    def __init__(self, access_token):
        self._access_token = access_token

    @classmethod
    def get_token(cls, appid, secret):
        url = "/".join([cls.base_url, "cgi-bin", "token"])
        res = cls.session.get(
            url, params=dict(
                grant_type="client_credential",
                appid=appid, secret=secret
            )
        )
        resjson = res.json()
        access_token = resjson["access_token"]
        expires_in = resjson["expires_in"]
        return access_token, expires_in

    def call(self, uri, prefix="cgi-bin", **kwargs):
        url = "/".join([self.base_url, prefix, uri])
        params = kwargs.setdefault("params", {})
        params.update(access_token=self._access_token)

        res = self.session.post(url, **kwargs)
        resjson = res.json()
        errcode = resjson.get("errcode", 0)
        if errcode != 0:
            raise ValueError("calling {0} error[{1}]: {2}".format(
                url, errcode, resjson.get("errmsg")
            ))
        return resjson

    def get_statistics(self, date, msg_data_id=None):
        res = self.call(
            "getarticletotal",
            prefix="datacube",
            json=dict(begin_date=date, end_date=date)
        )
        data = defaultdict(lambda: {})
        for info in res["list"]:
            msgid, article_idx = info["msgid"].split("_", 1)
            if msg_data_id is None or msgid == msg_data_id:
                latest = info["details"][-1]
                data[info["user_source"]][int(article_idx)] = latest
        return data

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

    def upload_media(self, media_type, data, temporary=False):
        if media_type == "thumb":
            return self.upload_material("thumb", data, temporary)["media_id"]
        elif media_type == "image":
            return self.upload_material("image", data, temporary)["url"]
        else:
            raise ValueError("unsupported media_type: {0}".format(media_type))

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

    def move_to_group(self, group_id, openids):
        if isinstance(openids, str):
            openids = iter([openids])
        elif isinstance(openids, (list, tuple)):
            openids = iter(openids)

        current = list(islice(openids, 50))
        if not current:
            return

        self.call(
            "groups/members/batchupdate",
            json=dict(openid_list=current, to_groupid=group_id)
        )
        return self.move_to_group(group_id, openids)

    def create_group(self, group_name):
        return self.call(
            "groups/create",
            json=dict(group=dict(name=group_name))
        )["group"]["id"]

    def delete_group(self, group_id):
        return self.call(
            "groups/delete",
            json=dict(group=dict(id=group_id))
        )

    def send_news(self, group_id, news_id, is_to_all=False):
        return self.call(
            "message/mass/sendall",
            json=dict(
                filter=dict(is_to_all=is_to_all, group_id=group_id),
                mpnews=dict(media_id=news_id),
                msgtype="mpnews"
            )
        )

    def get_all_subscribers_info(self, lang="zh_CN"):
        yield from self.batch_subscribers_info(self.get_subscribers(), lang)

    def get_subscriber(self, openid, lang="zh_CN"):
        for __, info in self.batch_subscribers_info(openid, lang):
            return info

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

    def batch_subscribers_info(self, subscribers, lang):
        """*Iterator*
        can take str, list, tuple or generator
        """
        if isinstance(subscribers, str):
            subscribers = iter([subscribers])
        elif isinstance(subscribers, (list, tuple)):
            subscribers = iter(subscribers)

        current = [
            dict(openid=oid, lang=lang)
            for oid in islice(subscribers, 100)
        ]
        if not current:
            return

        res = self.call(
            "user/info/batchget",
            json=dict(user_list=current)
        )
        for info in res["user_info_list"]:
            yield info["openid"], info
        yield from self.batch_subscribers_info(subscribers, lang)

    def get_qr(self, scene, expire_seconds=None):
        info = dict(
            expire_seconds=expire_seconds,
            action_name="QR_SCENE",
            action_info=dict(scene=dict(scene_id=scene))
        )

        if expire_seconds is None:
            del info["expire_seconds"]
            if isinstance(scene, int):
                info["action"] = "QR_LIMIT_SCENE"
            else:
                info["action"] = "QR_LIMIT_STR_SCENE"
                del info["action_info"]
                info["action_info"] = dict(scene=dict(scene_str=scene))

        res = self.call("qrcode/create", json=info)
        ticket = res["ticket"]
        query = requests.compat.urlencode(dict(ticket=ticket))
        fullurl = "https://mp.weixin.qq.com/cgi-bin/showqrcode?" + query

        return dict(
            data=res["url"],
            ticket=ticket,
            url=fullurl,
            expires_in=expire_seconds
        )
