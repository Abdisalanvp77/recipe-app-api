# recipe-app-api

A recipe API project

## Build with Docker

`docker build .`

## Build and Depoloy to docker image using compose

`docker-compose build`

## Linting

`docker-compose run --rm app sh -c "flake8"`

## Testing

`docker-compose run --rm app sh -c "python manage.py test"`

## create the project with docker compose

`docker-compose run --rm app sh -c "django-admin startproject app ."`

## run development server

`docker-compose up`
