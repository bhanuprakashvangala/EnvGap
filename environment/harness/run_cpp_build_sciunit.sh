#!/bin/bash
# Run sciunit on a C++ project - builds if needed
# Mount: /work = project dir, /sciunit_out = output dir
cd /work

# Build if no build directory or no binary
BINARY=$(find build -maxdepth 1 -executable -type f 2>/dev/null | head -1)
if [ -z "$BINARY" ]; then
    echo "No binary found, building..."
    mkdir -p build && cd build
    cmake -DCMAKE_PREFIX_PATH=/usr/local .. 2>&1 | tail -5
    echo "CMAKE_RC=$?"
    make -j$(nproc) 2>&1 | tail -10
    echo "MAKE_RC=$?"
    cd /work
    BINARY=$(find build -maxdepth 1 -executable -type f 2>/dev/null | head -1)
fi

if [ -z "$BINARY" ]; then
    echo "NO_BINARY_FOUND"
    exit 1
fi
echo "BINARY=$BINARY"

rm -rf /root/sciunit
sciunit create proj 2>&1 | tail -1
timeout 30 sciunit exec ./"$BINARY" 2>&1 | tail -5
echo "EXEC_RC=$?"
sciunit show e1 2>&1 | grep -v UserWarning
timeout 30 sciunit repeat e1 2>&1 | tail -5
echo "REPEAT_RC=$?"
sciunit checkout e1 2>&1 | tail -1

echo "--- RUNTIME DEPS ---"
grep "\.so" /root/sciunit/proj/cde-package/provenance.cde-root.1.log 2>/dev/null | grep READ | sed 's|.*/||' | sed 's|\.so\..*|.so|; s|\.so$||' | sort -u | grep -v "^ld" | grep -v "^libc$" | grep -v "^libm$" | grep -v "^libpthread" | grep -v "^libdl" | grep -v "^librt$" | grep -v "^libgcc" | grep -v "^libstdc++" | grep -v "^linux-vdso" | grep -v "^libselinux" | grep -v "^libpcre" | grep -v "^libnss" | grep -v "^libnsl" | grep -v "^libcrypt$"
echo "--- END DEPS ---"

cp -r /root/sciunit/proj/* /sciunit_out/
du -sm /sciunit_out | cut -f1
echo "DONE"
