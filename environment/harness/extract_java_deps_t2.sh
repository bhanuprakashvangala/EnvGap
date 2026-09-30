#!/bin/bash
for p in $(seq -w 1 50); do
    pid="p_$p"
    dir=~/TMLR/sciunit_results/claude_trial_2/java/$pid
    if [ -d "$dir" ] && [ -f "$dir/cde-package/provenance.cde-root.1.log" ]; then
        size=$(du -sm "$dir" | cut -f1)
        deps=$(grep "target/dependency/" "$dir/cde-package/provenance.cde-root.1.log" | grep READ | sed 's|.*target/dependency/||' | sort -u | tr '\n' ',')
        deps=$(echo "$deps" | sed 's/,*$//; s/^,//')
        if [ -z "$deps" ]; then deps="none"; fi
        echo "$pid: size=$size, deps=$deps"
    else
        echo "$pid: N/A"
    fi
done
