#!/bin/bash
cd /work
MAIN=${1:?Usage: run.sh <MainClass>}
echo "MAIN_CLASS=$MAIN"

# If no src/ directory but .java files exist in root, create Maven structure
if [ ! -d "src/main/java" ] && ls *.java 2>/dev/null | head -1 >/dev/null; then
    echo "No src/ dir found, creating Maven structure..."
    # Check if there's a package declaration
    PKG=$(grep -h "^package " *.java 2>/dev/null | head -1 | sed 's/package //;s/;//;s/\r//')
    if [ -n "$PKG" ]; then
        PKG_DIR=$(echo "$PKG" | tr '.' '/')
        mkdir -p "src/main/java/$PKG_DIR"
        cp *.java "src/main/java/$PKG_DIR/"
        echo "Created src/main/java/$PKG_DIR/"
    else
        mkdir -p src/main/java
        cp *.java src/main/java/
        echo "Created src/main/java/ (no package)"
    fi
fi

# Build the project
mvn package -q -DskipTests 2>&1 | tail -5
echo "BUILD_RC=$?"

# Copy dependencies
mvn dependency:copy-dependencies -DoutputDirectory=target/dependency -q 2>&1
echo "DEP_COPY_RC=$?"

# Check if classes exist
find target/classes -name "*.class" 2>/dev/null | head -3

rm -rf /root/sciunit
sciunit create proj 2>&1 | tail -1
timeout 30 sciunit exec java -cp "target/dependency/*:target/classes" "$MAIN" 2>&1 | tail -5
echo "EXEC_RC=$?"
sciunit show e1 2>&1 | grep -v UserWarning
timeout 30 sciunit repeat e1 2>&1 | tail -5
echo "REPEAT_RC=$?"
sciunit checkout e1 2>&1 | tail -1

echo "--- RUNTIME DEPS ---"
grep "target/dependency/" /root/sciunit/proj/cde-package/provenance.cde-root.1.log 2>/dev/null | grep READ | sed "s|.*target/dependency/||" | sort -u
echo "--- ALL DEPS ---"
ls target/dependency/ 2>/dev/null || echo "NO_DEPS"

cp -r /root/sciunit/proj/* /sciunit_out/
du -sm /sciunit_out | cut -f1
echo "DONE"
