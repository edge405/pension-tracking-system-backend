#!/bin/bash

# For Unix/Linux-based systems, set the FLASK_APP environment variable
export FLASK_APP=wsgi.py

# Run Flask database migrations and upgrades
flask db migrate
flask db upgrade