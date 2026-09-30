#!/bin/bash
# Run sciunit on a JavaScript project that needs npm install first
# Mount: /work = project dir (with package.json), /sciunit_out = output dir
cd /work

# Install dependencies first
if [ -f package.json ] && [ ! -d node_modules ]; then
  echo "Installing npm dependencies..."
  npm install --no-audit --no-fund 2>&1 | tail -5
  echo "NPM_INSTALL_RC=$?"
fi

JSFILE=${1:-$(ls *.js 2>/dev/null | head -1)}
if [ -z "$JSFILE" ]; then
  echo "NO_JS_FILE_FOUND"
  exit 1
fi
echo "JSFILE=$JSFILE"
sciunit create proj 2>&1 | tail -1
timeout 30 sciunit exec node "$JSFILE" 2>&1 | tail -5
echo "EXEC_RC=$?"
sciunit show e1 2>&1 | grep -v UserWarning
timeout 30 sciunit repeat e1 2>&1 | tail -5
echo "REPEAT_RC=$?"
sciunit checkout e1 2>&1 | tail -1

# Extract runtime deps from provenance
echo "--- RUNTIME DEPS ---"
grep "node_modules/" /root/sciunit/proj/cde-package/provenance.cde-root.1.log | grep READ | sed 's|.*node_modules/||' | cut -d'/' -f1 | sort -u | grep -v "^\.package-lock"
echo "--- SCOPED DEPS ---"
grep "node_modules/@" /root/sciunit/proj/cde-package/provenance.cde-root.1.log | grep READ | sed 's|.*node_modules/||' | awk -F'/' '{print $1"/"$2}' | sort -u

cp -r /root/sciunit/proj/* /sciunit_out/
du -sm /sciunit_out | cut -f1
echo "DONE"
