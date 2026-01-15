#!/bin/bash
# Run when INITIALIZE_DB parameter is set and migrations are available.
if ! ./manage.py migrate --check && "$INITIALIZE_DB" = "true";
then
    uv run ./manage.py migrate;
fi
