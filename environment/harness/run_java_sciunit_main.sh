#!/bin/bash
# Run sciunit on Java project with explicit main class
# Mount: /work = project dir, /sciunit_out = output dir
# Arg: $1 = main class name
cd /work
MAIN=${1:?Usage: run.sh <MainClass>}
echo "MAIN_CLASS=$MAIN"

# Copy individual dep JARs
mvn dependency:copy-dependencies -DoutputDirectory=target/dependency -q 2>&1

# Run sciunit with classpath
rm -rf /root/sciunit
sciunit create proj 2>&1 | tail -1
timeout 30 sciunit exec java -cp "target/dependency/*:target/classes" "$MAIN" 2>&1 | tail -5
echo "EXEC_RC=$?"
sciunit show e1 2>&1 | grep -v UserWarning
timeout 30 sciunit repeat e1 2>&1 | tail -5
echo "REPEAT_RC=$?"
sciunit checkout e1 2>&1 | tail -1

# Extract runtime deps
echo "--- RUNTIME DEPS ---"
grep "target/dependency/" /root/sciunit/proj/cde-package/provenance.cde-root.1.log 2>/dev/null | grep READ | sed "s|.*target/dependency/||" | sort -u
echo "--- ALL DEPS ---"
ls target/dependency/ 2>/dev/null || echo "NO_DEPS"

# Copy sciunit output
cp -r /root/sciunit/proj/* /sciunit_out/
du -sm /sciunit_out | cut -f1
echo "DONE"
