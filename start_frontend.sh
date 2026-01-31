#!/bin/bash

# Start Frontend Only
cd "$(dirname "$0")/drone_detection_frontend"

# Install deps if needed
if [ ! -d "node_modules" ]; then
    npm install
fi

echo "Starting frontend on http://localhost:3000"
npm run dev
