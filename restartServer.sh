#!/bin/bash
# Restart the development server by stopping and starting it

./stopAllServers.sh && sleep 2 && ./runserver.sh
