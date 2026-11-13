#!/usr/bin/env bash
# Copyright (c) The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://opensource.org/license/mit.
export LC_ALL=C.UTF-8
set -o errexit -o pipefail

# shellcheck source=setup.sh
source "$(dirname "${BASH_SOURCE[0]}")/setup.sh"

# setup mingw-w64 toolchain
mingw_w64_toolchain

BASE_CACHE="${BASE_CACHE:-$PWD/depends/built}/GUIX/BUILD"

# Build the depends tree
make -C depends --jobs="$JOBS" HOST="$HOST" \
                                   ${V:+V=1} \
                                   ${SOURCES_PATH+SOURCES_PATH="$SOURCES_PATH"} \
                                   ${BASE_CACHE+BASE_CACHE="$BASE_CACHE"} \
                                   ${build_CC+build_CC="$build_CC"} \
                                   ${build_CXX+build_CXX="$build_CXX"} \
                                   NO_QT=1

# CFLAGS
HOST_CFLAGS="-O2 -g"
HOST_CFLAGS+=$(find /gnu/store -maxdepth 1 -mindepth 1 -type d -exec echo -n " -ffile-prefix-map={}=/usr" \;)
HOST_CFLAGS+=" -fdebug-prefix-map=${DISTSRC}/src=."
HOST_CFLAGS+=" -fno-ident"

# CXXFLAGS
HOST_CXXFLAGS="$HOST_CFLAGS"

# LDFLAGS
HOST_LDFLAGS="-Wl,--no-insert-timestamp -Wl,--fatal-warnings"

mkdir -p "$DISTSRC"
(
    cd "$DISTSRC"

    # Extract the source tarball
    tar --strip-components=1 -xf "${GIT_ARCHIVE}"

    # First build libbitcoinconsensus as a shared library
    env CFLAGS="${HOST_CFLAGS}" CXXFLAGS="${HOST_CXXFLAGS}" LDFLAGS="${HOST_LDFLAGS}" \
    cmake -S . -B build_libbitcoinconsensus \
          --toolchain "${BASEPREFIX}/${HOST}/toolchain.cmake" \
          -DBUILD_BENCH=OFF \
          -DBUILD_BITCOIN_BIN=OFF \
          -DBUILD_CLI=OFF \
          -DBUILD_DAEMON=OFF \
          -DBUILD_FOR_FUZZING=OFF \
          -DBUILD_FUZZ_BINARY=OFF \
          -DBUILD_GUI=OFF \
          -DBUILD_GUI_TESTS=OFF \
          -DBUILD_KERNEL_LIB=OFF \
          -DBUILD_TESTS=OFF \
          -DBUILD_TX=OFF \
          -DBUILD_UTIL=OFF \
          -DBUILD_UTIL_CHAINSTATE=OFF \
          -DBUILD_WALLET_TOOL=OFF \
          -DCMAKE_INSTALL_PREFIX="${INSTALLPATH}" \
          -DREDUCE_EXPORTS=ON \
          -DWITH_CCACHE=OFF \
          -DBUILD_SHARED_LIBS=ON \
          -DBUILD_BITCOINCONSENSUS_LIB=ON
    cmake --build build_libbitcoinconsensus -j "$JOBS"
    cmake --install build_libbitcoinconsensus
    # The linker of Core 32's Guix toolchain writes the current time into the import library's symbol index, so two
    # hosts produce different libbitcoinconsensus.dll.a files. Rebuild the index in deterministic mode (timestamp 0).
    "${HOST}-ranlib" -D "${INSTALLPATH}/lib/libbitcoinconsensus.dll.a"

    # Configure this DISTSRC for $HOST
    env CFLAGS="${HOST_CFLAGS}" CXXFLAGS="${HOST_CXXFLAGS}" LDFLAGS="${HOST_LDFLAGS}" \
    cmake -S . -B build \
          --toolchain "${BASEPREFIX}/${HOST}/toolchain.cmake" \
          -DBUILD_BENCH=OFF \
          -DBUILD_FUZZ_BINARY=OFF \
          -DBUILD_GUI=OFF \
          -DBUILD_GUI_TESTS=OFF \
          -DCMAKE_INSTALL_PREFIX="${INSTALLPATH}" \
          -DREDUCE_EXPORTS=ON \
          -DWITH_CCACHE=OFF

    # Build Bitcoin Core
    cmake --build build -j "$JOBS"

    # Install built Bitcoin Core
    cmake --install build
)

rm -rf "$DISTSRC"/build "$DISTSRC"/build_libbitcoinconsensus

exit 0
