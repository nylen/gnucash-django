#!/bin/sh

cd "$(dirname "$0")"

while true; do
    if inotifywait -r -e create,modify,delete,move --exclude '^\./(lib|\.git)/' . ; then
        touch apache/money.wsgi
        echo "Updated `date`"
    fi
done
