#!/bin/bash

# Docker Compose Management Script
# This script helps manage the Docker Compose services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yml"

run_compose() {
    if command -v docker-compose &> /dev/null; then
        docker-compose -f "$COMPOSE_FILE" "$@"
    else
        docker compose -f "$COMPOSE_FILE" "$@"
    fi
}

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker and Docker Compose are installed
check_dependencies() {
    print_status "Checking dependencies..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_status "Dependencies check passed!"
}

# Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    mkdir -p "${SCRIPT_DIR}/logs"
    mkdir -p "${SCRIPT_DIR}/plugins"
    mkdir -p "${SCRIPT_DIR}/data/raw"
    mkdir -p "${SCRIPT_DIR}/data/parsed"
    mkdir -p "${SCRIPT_DIR}/data/cleaned"
    mkdir -p "${SCRIPT_DIR}/data/chunked"
    mkdir -p "${SCRIPT_DIR}/data/validated"
    mkdir -p "${SCRIPT_DIR}/data/vector_db"
    
    print_status "Directories created successfully!"
}

# Build images
build_images() {
    print_status "Building Docker images..."

    run_compose build --no-cache

    print_status "Images built successfully!"
}

# Start services
start_services() {
    print_status "Starting services..."
    
    run_compose up -d
    
    print_status "Services started! Check status with: ${0##*/} status"
}

# Stop services
stop_services() {
    print_status "Stopping services..."
    
    run_compose down
    
    print_status "Services stopped!"
}

# Show logs
show_logs() {
    local service=${1:-""}
    
    if [ -n "$service" ]; then
        print_status "Showing logs for $service..."
        run_compose logs -f "$service"
    else
        print_status "Showing logs for all services..."
        run_compose logs -f
    fi
}

# Show service status
show_status() {
    print_status "Service status:"
    run_compose ps
}

# Clean up
cleanup() {
    print_warning "This will remove all containers, networks, and volumes. Are you sure? (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        print_status "Cleaning up..."
        run_compose down -v --remove-orphans
        print_status "Cleanup completed!"
    else
        print_status "Cleanup cancelled."
    fi
}

# Main script logic
case "${1:-start}" in
    "check")
        check_dependencies
        ;;
    "build")
        check_dependencies
        create_directories
        build_images
        ;;
    "start")
        check_dependencies
        create_directories
        start_services
        ;;
    "stop")
        stop_services
        ;;
    "restart")
        stop_services
        start_services
        ;;
    "logs")
        show_logs "$2"
        ;;
    "status")
        show_status
        ;;
    "cleanup")
        cleanup
        ;;
    *)
        echo "Usage: $0 {check|build|start|stop|restart|logs|status|cleanup}"
        echo ""
        echo "Commands:"
        echo "  check    - Check if Docker and Docker Compose are installed"
        echo "  build    - Build Docker images"
        echo "  start    - Start all services"
        echo "  stop     - Stop all services"
        echo "  restart  - Restart all services"
        echo "  logs     - Show logs (optionally specify service name)"
        echo "  status   - Show service status"
        echo "  cleanup  - Remove all containers, networks, and volumes"
        echo ""
        echo "Examples:"
        echo "  $0 start"
        echo "  $0 logs vm-api"
        echo "  $0 logs airflow-scheduler"
        exit 1
        ;;
esac
