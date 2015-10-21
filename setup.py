# -*- coding: utf-8 -*-

import os
import sys

from codecs import open

__version__ = "0.0.1"
__author__ = "SkyLothar"
__email__ = "allothar@gmail.com"
__url__ = "https://github.com/skylothar/flask-wechat"


from setuptools import setup


if sys.argv[-1] == "publish":
    os.system("python setup.py sdist upload")
    sys.exit()


with open("requirements.txt", "r", "utf-8") as f:
    requires = f.read()


with open("README.md", "r", "utf-8") as f:
    readme = f.read()


setup(
    name="flask-wechat",
    version=__version__,
    description="flask blueprint for wechat",
    long_description=readme,
    author=__author__,
    author_email=__email__,
    install_requires=requires,
    url=__url__,
    packages=["flask_wechat", "flask_wechat.qyh", "flask_wechat.platform"],
    package_data={
        "flask_wechat": ["*.j2"],
    },
    include_package_data=True,
    zip_safe=False
)
