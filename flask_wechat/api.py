from flask import Blueprint
from flask import current_app, g, request

from .message import WechatMessage


wechat = Blueprint("wechat", __name__, template_folder="templates")


@wechat.before_request
def verify_request():
    """verify the request, de-dup retring request"""
    g.msg = WechatMessage(request)
    if g.msg.verified is False:
        current_app.logger.error(g.msg.reason)
        # return success, so wechat won't retry
        return "success"
