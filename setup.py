from pathlib import Path

from setuptools import find_packages, setup

setup(
    name="sabakan",
    version="0.0.1",
    packages=find_packages(),
    install_requires=Path("requirements.txt").read_text().splitlines(),
    entry_points={
        "console_scripts": [
            "sabakan = sabakan.cmd:main",
        ],
    },
)