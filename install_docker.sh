#!/bin/bash

apt-get update && apt-get install -y git
git clone https://github.com/gianlu33/reactive-net.git

pip install reactive-net/
pip install reactive-uart2ip/
