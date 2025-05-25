# setup.py
# author: ByteWyrm
# date: 2025.5.251.37
from setuptools import setup

setup(
    name="blog_friends",
    version="0.1",
    packages=["config", "generator", "check_flinks"],  # 显式指定包名
    install_requires=[
        "requests",
        "beautifulsoup4",
        "pyyaml",
        "pygithub"
    ],
)