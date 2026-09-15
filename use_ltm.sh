#!/usr/bin/env bash

if [[ "$1" != "0" && "$1" != "1" ]]; then
    echo "Usage: use_context [0|1]"
    exit 1
fi

sed -i "s/USE_CONTEXT=.*/USE_CONTEXT=$1/" .env
#echo "USE_CONTEXT set to $1 in .env"