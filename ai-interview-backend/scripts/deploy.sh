#!/bin/bash

# AI Interview production deployment script
# Run this script on the production server inside ai-interview-backend/

set -e

COMPOSE_FILES="${COMPOSE_FILES:-"-f docker-compose.yml -f docker-compose.prod.yml"}"
API_PORT="${API_PORT:-8001}"
HEALTH_ENDPOINT="http://localhost:${API_PORT}/api/v1/config/health"
TIMEOUT=120

echo "Starting AI Interview deployment..."
echo "Compose files: $COMPOSE_FILES"
echo "API port: $API_PORT"
echo "Health endpoint: $HEALTH_ENDPOINT"

check_health() {
    local timeout=$1
    echo "Waiting for application health check..."

    while [ "$timeout" -gt 0 ]; do
        if curl -f "$HEALTH_ENDPOINT" >/dev/null 2>&1; then
            echo "Application is healthy."
            return 0
        fi
        sleep 5
        timeout=$((timeout - 5))
        echo "Still waiting... ${timeout}s left"
    done

    echo "Application did not become healthy in time."
    return 1
}

show_logs() {
    echo "Recent service logs:"
    docker compose $COMPOSE_FILES logs --tail=80
}

main() {
    echo "Building and starting containers..."
    docker compose $COMPOSE_FILES up -d --build

    echo "Running database migrations..."
    docker compose $COMPOSE_FILES exec -T app alembic upgrade head

    echo "Container status:"
    docker compose $COMPOSE_FILES ps

    if ! check_health "$TIMEOUT"; then
        show_logs
        exit 1
    fi

    echo "Deployment completed successfully."
}

trap 'echo "Deployment failed."; show_logs; exit 1' ERR

main "$@"
