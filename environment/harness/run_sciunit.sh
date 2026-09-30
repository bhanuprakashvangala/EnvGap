#!/bin/bash
cd /work
pip3 install -r requirements.txt 2>/dev/null 1>/dev/null

PYFILE=$(ls *.py 2>/dev/null | head -1)
if [ -z "$PYFILE" ]; then
  PYFILE=$(find . -name "*.py" -not -path "./__pycache__/*" | head -1)
fi
echo "PYFILE=$PYFILE"

# Claimed deps with versions from requirements.txt
CLAIMED=$(grep "==" requirements.txt 2>/dev/null | grep -v "^#" | tr "\n" "," | sed "s/,$//")
echo "CLAIMED_VERSIONED=$CLAIMED"

# Transitive deps with versions - only user-installed packages
# Get list of pre-installed packages first, then diff
TRANS=$(pip3 freeze 2>/dev/null | grep -vE "^(pip|setuptools|wheel|sciunit2|backports|configobj|contextlib2|decorator|hs-restclient|humanfriendly|oauthlib|py==|requests-oauthlib|requests-toolbelt|retry|scandir|tqdm==4\.67|tzlocal|utcdatetime|zipfile2|certifi|charset-normalizer|idna==|urllib3|requests==2\.32)" | tr "\n" "," | sed "s/,$//")
echo "TRANSITIVE_VERSIONED=$TRANS"

# Create sciunit and capture execution
sciunit create proj 2>&1 | tail -1
timeout 30 sciunit exec python3 "$PYFILE" 2>&1 | tail -5
EXEC_RC=$?
echo "EXEC_RC=$EXEC_RC"

# Show sciunit info
sciunit show e1 2>&1 | grep -v UserWarning
echo "---"

# Repeat for reproducibility
timeout 30 sciunit repeat e1 >/dev/null 2>&1
REPEAT_RC=$?
echo "REPEAT_RC=$REPEAT_RC"

# Extract runtime deps with versions
timeout 30 python3 /trace_deps.py "$PYFILE" >/dev/null 2>&1
echo "RUNTIME_DEPS=$(cat /tmp/runtime_deps.txt 2>/dev/null)"
echo "RUNTIME_DEPS_VERSIONED=$(cat /tmp/runtime_deps_versioned.txt 2>/dev/null)"

# Save sciunit data
cp -r ~/sciunit/proj/* /sciunit_out/ 2>/dev/null
echo "SAVED"
