import setuptools
import os

def parse_requirements(filename):
    """ load requirements from a pip requirements file """
    lineiter = (line.strip() for line in open(filename))
    return [line for line in lineiter if line and not line.startswith("#")]

with open("README.md", "r") as fh:
    long_description = fh.read()

os.system("mkdir -p ./pyaatlibs/apk/")
os.system("cp ./apk/debug/*.apk ./pyaatlibs/apk/")

packages = setuptools.find_packages()
packages = [package for package in packages if package.startswith("pyaat")]

install_reqs = parse_requirements("requirements-py3.txt")

setuptools.setup(
    name='python-audio-autotest',  
    version='1.0',
    scripts=[] ,
    author="Hao-Wei Lee",
    author_email="hwinnerlee@gmail.com",
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
