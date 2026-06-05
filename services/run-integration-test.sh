#!/bin/bash
# Phase 3 Task 5: Run cross-domain integration smoke test
# Starts both services and runs the integration test

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=================================================================================${NC}"
echo -e "${BLUE}Phase 3 Task 5: Cross-Domain Integration Smoke Test${NC}"
echo -e "${BLUE}=================================================================================${NC}\n"

# Check if services are already running
check_service() {
    local port=$1
    local service=$2
    if curl -s "http://localhost:$port/health" > /dev/null; then
        echo -e "${GREEN}✓${NC} $service is already running on port $port"
        return 0
    else
        echo -e "${YELLOW}→${NC} $service not running on port $port"
        return 1
    fi
}

# Start service in background
start_service() {
    local service_path=$1
    local port=$2
    local service_name=$3

    echo -e "${YELLOW}→${NC} Starting $service_name on port $port..."

    # Kill any existing process on the port (optional)
    lsof -ti:$port | xargs kill -9 2>/dev/null || true

    cd "$service_path"
    uv run uvicorn app.main:app --port $port > "/tmp/${service_name}.log" 2>&1 &
    SERVICE_PID=$!
    echo $SERVICE_PID > "/tmp/${service_name}.pid"

    # Wait for service to be ready
    local max_attempts=30
    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        if curl -s "http://localhost:$port/health" > /dev/null; then
            echo -e "${GREEN}✓${NC} $service_name started successfully (PID: $SERVICE_PID)"
            return 0
        fi
        echo -n "."
        sleep 1
        attempt=$((attempt + 1))
    done

    echo -e "${RED}✗${NC} Failed to start $service_name"
    cat "/tmp/${service_name}.log"
    return 1
}

# Kill service by PID file
stop_service() {
    local pid_file=$1
    local service_name=$2

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 $pid 2>/dev/null; then
            kill $pid
            sleep 1
            echo -e "${GREEN}✓${NC} $service_name stopped"
        fi
        rm -f "$pid_file"
    fi
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if services are running
SALES_RUNNING=0
INVENTORY_RUNNING=0

if check_service 8002 "Sales Service"; then
    SALES_RUNNING=1
fi

if check_service 8003 "Inventory Service"; then
    INVENTORY_RUNNING=1
fi

# Start services if not running
if [ $SALES_RUNNING -eq 0 ]; then
    if ! start_service "$SCRIPT_DIR/sales-service" 8002 "sales-service"; then
        echo -e "${RED}✗${NC} Failed to start Sales Service"
        exit 1
    fi
    STARTED_SALES=1
fi

if [ $INVENTORY_RUNNING -eq 0 ]; then
    if ! start_service "$SCRIPT_DIR/inventory-service" 8003 "inventory-service"; then
        echo -e "${RED}✗${NC} Failed to start Inventory Service"
        [ $STARTED_SALES -eq 1 ] && stop_service "/tmp/sales-service.pid" "sales-service"
        exit 1
    fi
    STARTED_INVENTORY=1
fi

echo ""
echo -e "${BLUE}Both services are running. Running integration test...${NC}\n"

# Run the integration test
if python3 "$SCRIPT_DIR/integration-smoke-test.py"; then
    echo -e "${GREEN}✓ Integration test passed${NC}"
    TEST_RESULT=0
else
    echo -e "${RED}✗ Integration test failed${NC}"
    TEST_RESULT=1
fi

# Clean up if we started the services
if [ $STARTED_SALES -eq 1 ]; then
    stop_service "/tmp/sales-service.pid" "sales-service"
fi

if [ $STARTED_INVENTORY -eq 1 ]; then
    stop_service "/tmp/inventory-service.pid" "inventory-service"
fi

echo ""
echo -e "${BLUE}=================================================================================${NC}"
if [ $TEST_RESULT -eq 0 ]; then
    echo -e "${GREEN}✓ TEST SUITE COMPLETED SUCCESSFULLY${NC}"
else
    echo -e "${RED}✗ TEST SUITE FAILED${NC}"
fi
echo -e "${BLUE}=================================================================================${NC}"

exit $TEST_RESULT
