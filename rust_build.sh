#!/bin/bash

pushd ./rust_src/tile
python setup.py build
popd
rm -rf ./src/tile.py
rm -rf ./src/tile
mv ./rust_src/tile/build/lib/tile ./src

