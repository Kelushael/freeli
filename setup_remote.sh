#!/bin/bash
set -e

# Fix line endings just in case
sed -i "s/\r$//" "$0"

echo "--- Updating System ---"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq build-essential cmake git python3-pip curl

echo "--- Installing Python Libs ---"
pip3 install httpx uvicorn fastapi --break-system-packages

echo "--- Building llama.cpp (CMake) ---"
if [ ! -d "llama.cpp" ]; then
    git clone https://github.com/ggerganov/llama.cpp
fi

cd llama.cpp
cmake -B build -DGGML_NATIVE=OFF
cmake --build build --config Release -j$(nproc)
cd ..

echo "--- Setup Complete ---"

