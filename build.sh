#!/bin/bash
# Smart build script that handles caching and template issues
# Usage: ./build.sh [fresh|rebuild|quick|dev]
#
# Commands:
#   fresh    - Full clean build (removes all volumes/images, starts fresh)
#   rebuild  - Rebuild without removing data (cleans static files)
#   quick    - Fast restart with new code (default)
#   dev      - Run in development mode with watch

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

BUILD_TYPE="${1:-quick}"

echo "🔨 OpenSourceHouseProject Build Script"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

case "$BUILD_TYPE" in
    fresh)
        echo "🗑️  FRESH BUILD - Removing all containers, volumes, and images..."
        docker compose down -v --remove-orphans 2>/dev/null || true
        echo "🏗️  Building fresh containers..."
        docker compose build --no-cache
        docker compose up -d
        echo "⏳ Waiting for services to be healthy..."
        sleep 15
        docker compose exec web python manage.py migrate
        docker compose exec web python manage.py load_test_data
        echo "✅ Fresh build complete!"
        ;;

    rebuild)
        echo "🔄 REBUILD - Keeping data, rebuilding code and static files..."
        docker compose down --remove-orphans
        echo "🗑️  Cleaning static files..."
        rm -rf staticfiles/* 2>/dev/null || true
        echo "🏗️  Building containers..."
        docker compose build
        docker compose up -d
        echo "⏳ Waiting for services to be healthy..."
        sleep 12
        docker compose exec web python manage.py collectstatic --noinput --clear
        echo "✅ Rebuild complete!"
        ;;

    quick)
        echo "⚡ QUICK BUILD - Just pull new code and restart..."
        # Stop without removing volumes (keeps DB)
        docker compose stop web nginx 2>/dev/null || true
        # Copy new code to container
        docker compose build --no-cache --progress=plain web 2>&1 | tail -20
        docker compose up -d
        echo "⏳ Waiting for service to be ready..."
        sleep 8
        docker compose exec web python manage.py collectstatic --noinput
        echo "✅ Quick build complete!"
        ;;

    dev)
        echo "👨‍💻 DEVELOPMENT MODE - Running with hot reload..."
        docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
        ;;

    *)
        echo "❌ Unknown build type: $BUILD_TYPE"
        echo ""
        echo "Usage: ./build.sh [fresh|rebuild|quick|dev]"
        echo ""
        echo "Commands:"
        echo "  fresh    - Full clean build (removes all volumes/images, starts fresh)"
        echo "  rebuild  - Rebuild without removing data (cleans static files)"
        echo "  quick    - Fast restart with new code (default)"
        echo "  dev      - Run in development mode with watch"
        exit 1
        ;;
esac

echo ""
echo "🎉 Build complete!"
echo "📊 View your project at: http://localhost:8000/project-items/board/"
echo ""
