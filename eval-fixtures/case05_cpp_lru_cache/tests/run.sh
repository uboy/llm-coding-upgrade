#!/usr/bin/env bash
set -euo pipefail
g++ -std=c++17 -O2 -Wall -Wextra -pedantic tests/test.cpp -o tests/test_bin
./tests/test_bin
