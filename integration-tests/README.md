# Beheeromgeving Datacatalogus - Integration Tests

These integration tests have been set up to make sure all environment variables are tested to ensure a correct
deployment of the Beheeromgeving Datacatalogus.

# Installation

Requirements:

* Python >= 3.14
* Recommended: Docker/Docker Compose (or uv for local installs)

## Beheeromgeving Datacatalogus

The easiest way to run these integration tests is by using Docker Compose. This will also start Beheeromgeving Datacatalogus.

To be able to run the tests you will need a valid token to be able to make the requests. The easiest way is to set up
direnv with an `.envrc` file or export a token from the command line:

```shell
export TOKEN="$(docker compose run web python get-token.py FP/MDW)"
```

The catalogus test container has both the `teams` and `products` endpoint available, so running the tests against the `bewoningen`. After having a valid token in your environment you'll be able to start the tests using:

```shell
docker compose run tests -e teams
docker compose run tests -e products
```

## Using Local Python

Make sure you have the environment variable `CATALOGUS_URL` set to the URL of the Catalogus.
You can use uv to start the services:

```shell
docker compose up -d -f ../docker-compose.yml
export CATALOGUS_URL=http://localhost:8096
```

```shell
uv sync
uv run catalogus-test
```
