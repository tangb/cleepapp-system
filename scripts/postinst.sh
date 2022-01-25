#!/bin/sh

# install libs
python3 -m pip install --trusted-host pypi.org "psutil==5.9.0"
if [ $? -ne 0 ]; then
    exit 1
fi

