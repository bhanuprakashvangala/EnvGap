#!/bin/bash
# Process all specified Python projects for sciunit
TRIAL=$1
shift
for PID in "$@"; do
    echo "=== START $PID ==="
    DIR=~/TMLR/code_generation/claude_generated/$PID/trial_$TRIAL/python
    OUT=~/TMLR/sciunit_results/claude_trial_$TRIAL/python/$PID
    mkdir -p $OUT
    
    RESULT=$(docker run --rm \
        -v $DIR:/work \
        -v $OUT:/sciunit_out \
        -v ~/TMLR/run_py_sciunit.sh:/run.sh \
        tmlr-python-eval bash /run.sh 2>&1)
    
    TRANS=$(echo "$RESULT" | grep "^TRANSITIVE=" | sed 's/TRANSITIVE=//')
    SIZE=$(echo "$RESULT" | grep "^SIZE=" | sed 's/SIZE=//')
    EXEC_RC=$(echo "$RESULT" | grep "^EXEC_RC=" | sed 's/EXEC_RC=//')
    HAS_DONE=$(echo "$RESULT" | grep "^REPEAT_DONE")
    
    echo "PID=$PID"
    echo "SIZE=$SIZE"
    echo "TRANS=$TRANS"
    echo "EXEC_RC=$EXEC_RC"
    if [ -n "$HAS_DONE" ]; then
        echo "REPEAT=True"
    else
        echo "REPEAT=False"
    fi
    echo "=== END $PID ==="
done
