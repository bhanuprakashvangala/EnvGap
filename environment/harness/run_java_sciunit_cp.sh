#!/bin/bash
# Run sciunit on Java project using classpath (not fat JAR)
# This makes individual dep JARs visible in provenance
# Mount: /work = project dir, /sciunit_out = output dir
cd /work

# Step 1: Copy individual dep JARs
mvn dependency:copy-dependencies -DoutputDirectory=target/dependency -q 2>&1

# Step 2: Find main class from fat JAR manifest
JAR=$(ls -S target/*.jar 2>/dev/null | head -1)
if [ -z "$JAR" ]; then
  echo "NO_JAR_FOUND"
  exit 1
fi
jar xf "$JAR" META-INF/MANIFEST.MF 2>/dev/null
MAIN=$(grep Main-Class META-INF/MANIFEST.MF 2>/dev/null | awk '{print $2}' | tr -d '\r\n')
if [ -z "$MAIN" ]; then
  echo "NO_MAIN_CLASS"
  exit 1
fi
echo "JAR=$JAR"
echo "MAIN_CLASS=$MAIN"

# Step 3: Run sciunit with classpath
rm -rf /root/sciunit
sciunit create proj 2>&1 | tail -1
timeout 30 sciunit exec java -cp "target/dependency/*:target/classes" "$MAIN" 2>&1 | tail -5
echo "EXEC_RC=$?"
sciunit show e1 2>&1 | grep -v UserWarning
timeout 30 sciunit repeat e1 2>&1 | tail -5
echo "REPEAT_RC=$?"
sciunit checkout e1 2>&1 | tail -1

# Step 4: Extract runtime deps from provenance
echo "--- RUNTIME DEPS ---"
grep "target/dependency/" /root/sciunit/proj/cde-package/provenance.cde-root.1.log | grep READ | sed 's|.*target/dependency/||' | sort -u
echo "--- ALL DEPS ---"
ls target/dependency/

# Step 5: Copy sciunit output
cp -r /root/sciunit/proj/* /sciunit_out/
du -sm /sciunit_out | cut -f1
echo "DONE"
