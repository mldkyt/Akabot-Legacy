#!/bin/bash


GIT_VERSION=$(git describe --long --tags || "dirty")

echo "Git version is: $GIT_VERSION"

sed -i "s/@VERSION@/$GIT_VERSION/g" main.py
