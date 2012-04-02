#!/bin/sh

cd "$(dirname "$0")"

dnotify -MDRr . -e sh -c 'touch apache/money.wsgi && echo "Updated `date`"'
