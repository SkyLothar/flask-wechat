from .api import wechat


def init_app(app, url_prefix="/"):
    from .cipher import cipher
    from .ext import cache
    cipher.init_app(app)
    cache.init_app(app)

    app.register_blueprint(wechat, url_prefix=url_prefix)
