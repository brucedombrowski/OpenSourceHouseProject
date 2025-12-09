#!/bin/bash
# Restart the development server by stopping and starting it


clear
./stopAllServers.sh && sleep 2

# Collect static files before starting server
if [ -x "./.venv/bin/python" ]; then
	echo "Collecting static files..."
	./.venv/bin/python manage.py collectstatic --noinput
else
	echo "Python virtual environment not found. Skipping collectstatic."
fi

./runserver.sh
