#!/bin/bash
# Run sciunit on a pre-built Java project
# Mount: /work = project dir (with target/), /sciunit_out = output dir
cd /work
JAR=$(ls -S target/*.jar 2>/dev/null | head -1)
if [ -z "$JAR" ]; then
  echo "NO_JAR_FOUND"
  exit 1
fi
echo "JAR=$JAR"
sciunit create proj 2>&1 | tail -1
timeout 30 sciunit exec java -jar "$JAR" 2>&1 | tail -5
echo "EXEC_RC=$?"
sciunit show e1 2>&1 | grep -v UserWarning
timeout 30 sciunit repeat e1 2>&1 | tail -5
echo "REPEAT_RC=$?"
sciunit checkout e1 2>&1 | tail -1
cp -r /root/sciunit/proj/* /sciunit_out/
du -sm /sciunit_out | cut -f1
echo "DONE"
