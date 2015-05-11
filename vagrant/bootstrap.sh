#!/bin/bash

echo "PYTHONDONTWRITEBYTECODE=1" >> /etc/environment
mount --bind /vagrant/.packages /var/cache/apt/archives

apt-get update
apt-get install -y python3-pip

sudo pip3 install setuptools

cd /fss
python3 setup.py develop
