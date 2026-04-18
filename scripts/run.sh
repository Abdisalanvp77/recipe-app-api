#!/bin/bash

set -e # Exit immediately if a command exits with a non-zero status.

python manage.py wait_for_db
python manage.py collectstatic --noinput
python manage.py migrate

# Start the uWSGI server, binding to port 9000 and using 4 worker processes to handle requests.
# The --master flag enables the master process, and --enable-threads allows for multi-threading support.
# The --module flag specifies the WSGI application to run, which is located in the app/wsgi.py file.
uwsgi --socket :9000 --workers 4  --master --enable-threads --module app.wsgi
