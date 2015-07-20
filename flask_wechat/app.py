from flask import Blueprint
from flask import current_app, g, request

from .cryptor import cryptor
from .message import WechatMessage

wechat = Blueprint("wechat", __name__, template_folder="templates")


@wechat.before_app_first_request
def setup_cryptor():
    cryptor.setup(
        current_app.config["WECHAT_AESKEY"],
        current_app.config["WECHAT_CROPID"],
        current_app.config["WECHAT_TOKEN"]
    )


@wechat.before_request
def verify_request():
    """verify the request, de-dup retring request"""
    g.msg = WechatMessage(request)
    if g.msg.verified is False:
        current_app.logger.info("signature mismatch!")
        # return empty string, so wechat won't retry
        return "", 200
