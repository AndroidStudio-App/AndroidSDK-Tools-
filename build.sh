#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

NDK_PATH=/data/data/com.neonide.studio/files/home/android-sdk/ndk/29.0.14206865
PROTOC_PATH=$SCRIPT_DIR/src/protobuf/build/protoc-3.21.12.0
BUILD_DIR=$SCRIPT_DIR/build/arm64-v8a
ABI=arm64-v8a
API=35

echo "Building Android SDK Tools..."
echo "NDK: $NDK_PATH"
echo "Protoc: $PROTOC_PATH"
echo "Build Dir: $BUILD_DIR"
echo "ABI: $ABI"
echo "API: $API"

python build.py \
    --ndk="$NDK_PATH" \
    --abi="$ABI" \
    --api="$API" \
    --build="$BUILD_DIR" \
    --protoc="$PROTOC_PATH"

echo "Build complete!"
echo "Output: $BUILD_DIR/bin/"
