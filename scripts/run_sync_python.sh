#!/bin/bash

export COMPOSE_PROFILE="standalone"
export DEV_IMAGE_SUFFIX=""
export DEV_SOURCE_PATH="galaxy_ng:pulp_ansible:pulpcore"
export DEV_VOLUME_SUFFIX="${DEV_IMAGE_SUFFIX:-}"
export DJANGO_SETTINGS_MODULE="pulpcore.app.settings"
export ENABLE_SIGNING="0"
export HOME="/home/galaxy"
export HOSTNAME="a2f0f683fe2f"
export LANG="en_US.UTF-8"
export LOCK_REQUIREMENTS="0"
export PATH="/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export PULP_ANALYTICS="false"
export PULP_ANSIBLE_API_HOSTNAME="http://localhost:5001"
export PULP_ANSIBLE_CONTENT_HOSTNAME="http://localhost:24816/api/automation-hub/v3/artifacts/collections"
export PULP_CONTENT_ORIGIN="http://localhost:24816"
export PULP_CONTENT_PATH_PREFIX="/api/automation-hub/v3/artifacts/collections/"
export PULP_DB_HOST="postgres"
export PULP_DB_NAME="galaxy_ng"
export PULP_DB_PASSWORD="galaxy_ng"
export PULP_DB_USER="galaxy_ng"
export PULP_DEBUG="True"
export PULP_GALAXY_API_PATH_PREFIX="/api/automation-hub/"
export PULP_GALAXY_COLLECTION_SIGNING_SERVICE="ansible-default"
export PULP_GALAXY_CONTAINER_SIGNING_SERVICE="container-default"
export PULP_GALAXY_DEPLOYMENT_MODE="standalone"
export PULP_PRIVATE_KEY_PATH="/src/galaxy_ng/dev/common/container_auth_private_key.pem"
export PULP_PUBLIC_KEY_PATH="/src/galaxy_ng/dev/common/container_auth_public_key.pem"
export PULP_REDIS_HOST="redis"
export PULP_RH_ENTITLEMENT_REQUIRED="insights"
export PULP_SETTINGS="/etc/pulp/settings.py"
export PULP_TOKEN_AUTH_DISABLED="false"
export PULP_TOKEN_SERVER="http://localhost:5001/token/"
export PULP_TOKEN_SIGNATURE_ALGORITHM="ES256"
export PULP_X_PULP_CONTENT_HOST="content-app"
export PYTHONUNBUFFERED="1"
export TERM="xterm"
export TZ="UTC"
export VIRTUAL_ENV="/venv"
export WAIT_FOR_MIGRATIONS="1"
export WITH_DEV_INSTALL="1"
export container="oci"

source /venv/bin/activate
