#!/bin/bash

# Use the Python interpreter from the Rye virtual environment
./.venv/bin/python -m uvicorn src.app:app --host "0.0.0.0" --port 8000