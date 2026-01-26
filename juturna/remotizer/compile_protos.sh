#!/bin/bash
# compile_protos.sh

PROTO_DIR="./protos"
OUT_DIR="./c_protos"

mkdir -p $OUT_DIR

# Compile payloads.proto
python -m grpc_tools.protoc \
  -I=$PROTO_DIR \
  --python_out=$OUT_DIR \
  $PROTO_DIR/payloads.proto

# Compile messaging_service.proto with gRPC support
python -m grpc_tools.protoc \
  -I=$PROTO_DIR \
  --python_out=$OUT_DIR \
  --grpc_python_out=$OUT_DIR \
  $PROTO_DIR/messaging_service.proto

protol\
  --create-package \
  --in-place \
  --python-out $OUT_DIR \
  protoc --proto-path=$PROTO_DIR payloads.proto messaging_service.proto

# touch $OUT_DIR/__init__.py

echo "protobuf compilation completed!"
