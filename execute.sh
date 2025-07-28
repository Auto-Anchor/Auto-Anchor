#!/bin/bash

# This script automates the startup process for the entire project.
# It installs dependencies and starts the backend, aCube API, and frontend services.

# --- Configuration ---
# Set to true to exit immediately if any command fails
set -e

# --- Functions ---
# Function to print a formatted header
print_header() {
  echo "========================================================================"
  echo "=> $1"
  echo "========================================================================"
}

# --- Main Script ---

# 2. Start the backend server (Uvicorn) in the background
print_header "Starting backend server"
cd backend/scripts/
echo "Current directory: $(pwd)"
echo "Starting Uvicorn on port 8084..."
uvicorn main:app --reload --port 8084 &
# Save the process ID (PID) of the last background command
BACKEND_PID=$!
echo "Backend server started with PID: $BACKEND_PID"
cd ../../ # Go back to the root directory
echo ""

# 3. Start the aCube Python API in the background
print_header "Starting aCube API"
cd aCube/
echo "Current directory: $(pwd)"
echo "Running api.py..."
python api.py &
# Save the process ID (PID) of the last background command
ACUBE_PID=$!
echo "aCube API started with PID: $ACUBE_PID"
cd ../ # Go back to the root directory
echo ""

# 4. Install npm dependencies and start the frontend React app
print_header "Setting up and starting frontend"
cd frontend/
echo "Current directory: $(pwd)"

# Check if node_modules directory exists
if [ ! -d "node_modules" ]; then
  echo "node_modules not found. Running 'npm install'..."
  npm install
  echo "npm dependencies installed successfully."
else
  echo "node_modules directory already exists. Skipping 'npm install'."
fi

echo "Starting React app with 'npm run start'..."
# This will run in the foreground and occupy the terminal
npm run start

# --- Cleanup ---
# This part of the script will run when you stop the frontend (e.g., with Ctrl+C)
# It will stop the background processes.
print_header "Shutting down background processes..."
kill $BACKEND_PID
kill $ACUBE_PID
echo "Backend and aCube processes terminated."
echo "Script finished."
