#!/bin/bash
set -x

###################################################################
# This script will get executed *once* the Docker container has 
# been built. Commands that need to be executed with all available
# tools and the filesystem mount enabled should be located here. 
###################################################################

cd /app 

make bootstrap-with-docker

# Bubble up the main Docker command to container.
exec "$@"