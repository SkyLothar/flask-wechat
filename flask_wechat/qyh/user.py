class User(object):
    def __init__(self, qyh, user_info):
        self._qyh = qyh
        self._user_info = user_info

    def __str__(self):
        return "<Qyh {0}>".format(self.email)

    @property
    def email(self):
        return self._user_info["email"]

    @property
    def name(self):
        return self._user_info["name"]

    @property
    def gender(self):
        return "male" if self._user_info["gender"] == "1" else "female"
