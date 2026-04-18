#!/bin/sh

set -e # Exit immediately if a command exits with a non-zero status.
# This script is used to start the uWSGI server and the Nginx server.
# It first runs the necessary Django management commands to prepare the application,
# and then starts the uWSGI server to serve the Django application.
# Finally, it configures Nginx using environment variables and starts the Nginx server.
envsubst < /etc/nginx/default.conf.tpl > /etc/nginx/conf.d/default.conf
nginx -g 'daemon off;'
