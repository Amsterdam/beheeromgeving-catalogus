# Beheeromgeving Datacatalogus

This is the admin interface for the data catalogue.

# Installation

Requirements:

* Python >= 3.13
* Recommended: Docker/Docker Compose (or pyenv for local installs)

## Using Docker Compose

Run docker compose:

```shell
docker compose up
```

Navigate to `localhost:8096`.

## Using Local Python

Create a virtualenv:

```shell
python3 -m venv venv
source venv/bin/activate
```

Install all packages in it:

```shell
pip install -U wheel pip
cd src/
make install  # installs src/requirements_dev.txt
```

Start the Django application:

```shell
./manage.py runserver localhost:8000
```

# Developer Notes

Run `make` in the `src` folder to have a help-overview of all common developer tasks.

## Package Management

The packages are managed with *pip-compile*.

To add a package, update the `requirements.in` file and run `make requirements`.
This will update the "lockfile" aka `requirements.txt` that's used for pip installs.

To upgrade all packages, run `make upgrade`, followed by `make install` and `make test`.
Or at once if you feel lucky: `make upgrade install test`.

## Environment Settings

Consider using *direnv* for automatic activation of environment variables.
It automatically sources an ``.envrc`` file when you enter the directory.
This file should contain all lines in the `export VAR=value` format.

In a similar way, *pyenv* helps to install the exact Python version,
and will automatically activate the virtualenv when a `.python-version` file is found:

```shell
pyenv install 3.13.1
pyenv virtualenv 3.13.1 beheeromgeving
echo beheeromgeving > .python-version
```

A setting that may be useful is the FEATURE_FLAG_USE_AUTH, which if set to False will
prevent the application from doing any authorization checks. This is strictly for
development purposes, and will always be set to True in production.
