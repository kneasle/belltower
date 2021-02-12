""" Setup script for belltower """

import setuptools

# Read the README as the long description
with open("README.md") as fh:
    long_desc = fh.read()

# Read the README as the long description
with open("belltower/version.txt") as fh:
    version = fh.read()

setuptools.setup(
    name="belltower",
    version=version,

    author="Ben White-Horne",
    author_email="kneasle@gmail.com",

    description="A Pythonic interface to Ringing Room, an online change ringing platform.",
    long_description=long_desc,
    long_description_content_type="text/markdown",

    url="https://github.com/kneasle/belltower",

    license="MIT",
    platforms="any",

    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent"
    ],
    python_requires='>=3.6',
    install_requires=[
        "requests",
        "python-socketio<5",
        "python-engineio<4",
        "websocket-client"
    ],
)
