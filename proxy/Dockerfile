# Use the official Nginx image as the base image,
# which is optimized for serving static files and acting as a reverse proxy.
# The image is based on Alpine Linux, which is a lightweight distribution that helps keep the image size small.
# The "unprivileged" variant of the Nginx image is used to enhance security by running Nginx as a non-root user.
# The maintainer label is added to provide information about the author of the image.
FROM nginxinc/nginx-unprivileged:alpine-slim
LABEL maintainer="Abdisalan Mohamed"

# The following environment variable is set to ensure that Python output is not buffered,
# which is important for logging and debugging purposes when running the application in a container.
COPY ./default.conf.tpl /etc/nginx/default.conf.tpl
COPY ./uwsgi_params /etc/nginx/uwsgi_params
COPY ./run.sh /run.sh

# The application will listen on port 8000,
# and the Nginx server will be configured to proxy requests to the application running on port 9000.
# The environment variables are set to allow for easy configuration of the Nginx server and the application host and port.
ENV LISTEN_PORT=8000
ENV APP_HOST=app
ENV APP_PORT=9000

# The following commands are used to set up the application environment, install dependencies, and configure permissions.
# A Python virtual environment is created to isolate the application's dependencies from the system Python environment.
# The necessary packages for building and running the application are installed, including the PostgreSQL client and development libraries, as well as the zlib library for handling image processing.
# The application dependencies are installed using pip, and if the DEV argument is set to true, the development dependencies are also installed.
# After the dependencies are installed, the temporary build dependencies are removed to reduce the image size.
# A new user named "django-user" is created to run the application, and the necessary directories for media and static files are created with appropriate permissions.
USER root

# The following commands are used to set up the static files directory and configure permissions for Nginx.
# The /vol/static directory is created to store the static files that will be served by Nginx, and permissions are set to allow Nginx to read and serve these files.
# The default Nginx configuration file is created and permissions are set to allow Nginx to read and write to it, which is necessary for configuring the Nginx server to proxy requests to the application.
# Finally, the run.sh script is made executable, which will be used to start the Nginx server and the application when the container is run.
RUN mkdir -p /vol/static && \
    chmod -R 755 /vol/static && \
    touch /etc/nginx/conf.d/default.conf && \
    chown nginx:nginx /etc/nginx/conf.d/default.conf && \
    chmod -R +x /run.sh

VOLUME /vol/static
USER nginx

CMD ["/run.sh"]
