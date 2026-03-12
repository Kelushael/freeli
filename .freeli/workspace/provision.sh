#!/bin/bash
                    set -e
                    echo "--- Updating System ---"
                    apt-get update -qq && apt-get install -y -qq build-essential git cmake wget screen python3-pip
                    
                    echo "--- Setting up Llama.cpp ---"
                    if [ ! -d "llama.cpp" ]; then
                        git clone https://github.com/ggerganov/llama.cpp
                        cd llama.cpp
                        make -j$(nproc)
                        cd ..
                    fi
                    
                    echo "--- Downloading Model (Phi-2) ---"
                    mkdir -p models
                    if [ ! -f "models/phi-2.Q4_K_M.gguf" ]; then
                        wget -q --show-progress -O models/phi-2.Q4_K_M.gguf https://huggingface.co/TheBloke/phi-2-GGUF/resolve/main/phi-2.Q4_K_M.gguf
                    fi
                    
                    echo "--- Starting Server ---"
                    # Kill existing
                    pkill -f llama-server || true
                    
                    # Run in screen
                    screen -dmS freeli ./llama.cpp/llama-server -m models/phi-2.Q4_K_M.gguf -c 2048 --host 0.0.0.0 --port 8125
                    
                    echo "SUCCESS: Server running on port 8125"
                    