#!/bin/bash

# Train YOLO Model for Drone Detection
cd "$(dirname "$0")/drone_detection_backend"

# Setup venv
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install -q -r requirements.txt

echo "Starting YOLO model training..."
echo "This will generate synthetic drone data and train a custom model."
echo ""

# Check for --full flag
if [ "$1" == "--full" ]; then
    echo "Running FULL training (1000 images, 50 epochs)..."
    python -m app.train_yolo --full
else
    echo "Running QUICK training (100 images, 10 epochs)..."
    echo "Use --full for complete training."
    python -m app.train_yolo
fi

echo ""
echo "Training complete! Model saved to drone_detection_backend/models/"
