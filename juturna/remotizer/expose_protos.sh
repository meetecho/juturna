#!/bin/bash
# compile_protos.sh

PROTO_DIR="./protos"
OUT_DIR="./c_protos"

mkdir -p $OUT_DIR

protol\
  --create-package \
  --in-place \
  --python-out $OUT_DIR \
  protoc --proto-path=$PROTO_DIR payloads.proto messaging_service.proto

echo "protobuf compilation exposed!"
