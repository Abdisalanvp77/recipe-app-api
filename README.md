# recipe-app-api

A recipe API project

## Clear any running containers

`docker-compose down`

## run container

`docker-compose up`

## Build with Docker

`docker build .`

## Build and Depoloy to docker image using compose

`docker-compose build`

## Linting

`docker-compose run --rm app sh -c "flake8"`

## Testing

`docker-compose run --rm app sh -c "python manage.py test"`

## Check the docker volume

`docker volume ls`

## Remove a docker volume

- copy the name of the volume from the above ls output
- ensure the volume is not in use by typing `docker-compose down`
- remove it by typing `docker volume rm <volume_name>`

## Make Migrations

`docker-compose run --rm app sh -c "python manage.py makemigrations"`

## Migrate

`docker-compose run --rm app sh -c "python manage.py migrate"`

## create the project with docker compose

`docker-compose run --rm app sh -c "django-admin startproject app ."`

## run development server

`docker-compose up`

## Authenticate with Docker Hub

- register your account
- use `docker login` during our job
- add secrets to github project in the settings
