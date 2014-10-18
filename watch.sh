#!/bin/sh

cd "$(dirname "$0")"

something_changed() {
    touch apache/money.wsgi
    echo "Updated `date`"
}

something_changed

while true; do
    if inotifywait -r -e create,modify,delete,move --exclude '^\./(lib|\.git)/' . ; then
        something_changed
    fi
done
