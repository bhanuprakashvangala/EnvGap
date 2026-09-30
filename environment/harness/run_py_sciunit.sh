#!/bin/bash
# Streamlined Python sciunit runner - captures key metrics
cd /work
pip3 install -r requirements.txt 2>/dev/null 1>/dev/null

PYFILE=$(ls *.py 2>/dev/null | head -1)
if [ -z "$PYFILE" ]; then
  PYFILE=$(find . -name "*.py" -not -path "./__pycache__/*" | head -1)
fi
echo "PYFILE=$PYFILE"

TRANS=$(pip3 freeze 2>/dev/null | grep -vE "^(pip|setuptools|wheel|sciunit2|backports|configobj|contextlib2|decorator|hs-restclient|humanfriendly|oauthlib|py==|requests-oauthlib|requests-toolbelt|retry|scandir|tqdm==4\.67|tzlocal|utcdatetime|zipfile2|certifi|charset-normalizer|idna==|urllib3|requests==2\.32)" | tr "\n" "," | sed "s/,$//")
echo "TRANSITIVE=$TRANS"

rm -rf /root/sciunit
sciunit create proj 2>&1 | tail -1
timeout 30 sciunit exec python3 "$PYFILE" 2>&1 | tail -3
echo "EXEC_RC=$?"
sciunit show e1 2>&1 | grep "size:" | sed 's/.*size: /SIZE=/'
timeout 60 sciunit repeat e1 2>&1 | tail -3
echo "REPEAT_DONE"

cp -r ~/sciunit/proj/* /sciunit_out/ 2>/dev/null
echo "DONE"
