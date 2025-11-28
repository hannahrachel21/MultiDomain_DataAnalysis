#!/bin/bash

echo "Starting FastAPI backend..."
# Run FastAPI in background
uvicorn main:app --reload &
FASTAPI_PID=$!

echo "Waiting 2 seconds for FastAPI to start..."
sleep 2

echo "Starting Streamlit frontend..."
streamlit run frontend_streamlit.py

echo "Shutting down FastAPI..."
kill $FASTAPI_PID

echo "Application stopped successfully."
