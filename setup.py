import setuptools
import os

# Note: release commands
#    $ python3 setup.py bdist_wheel
#    $ python3 -m twine upload dist/python_audio_autotest-1.2.4-py3-none-any.whl

with open("README.md", "r") as fh:
    long_description = fh.read()

os.system("mkdir -p ./pyaatlibs/apk/")
os.system("cp ./apk/debug/*.apk ./pyaatlibs/apk/")

packages = setuptools.find_packages()
packages = [package for package in packages if package.startswith("pyaat")]

install_reqs = [
    "androidviewclient>=20.0.0b3",
    "numpy>=1.19.4",
    "scipy>=1.5.4",
    "scikit-learn>=0.23.2",
    "matplotlib>=3.3.2",
    "librosa>=0.8.0",
    "sounddevice>=0.4.1"
]

setuptools.setup(
    name="python-audio-autotest",
    version="1.2.12",
    scripts=[] ,
    author="Hao-Wei Lee",
    author_email="hwinnerlee@gmail.com, hwlee@google.com",
    description="This is a auto-testing framework of audio functions for Android devices.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/HW-Lee/AudioAutoTest",
    install_requires=install_reqs,
    packages=packages,
    include_package_data=True,
    package_data={
        "pyaatlibs": ["apk/*.apk"]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
)

os.system("rm -rf ./pyaatlibs/apk/")
