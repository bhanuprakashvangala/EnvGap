#!/bin/bash
for p in $(seq -w 1 50); do
    pid="p_$p"
    dir=~/TMLR/sciunit_results/claude_trial_3/javascript/$pid
    if [ -d "$dir" ] && [ -f "$dir/cde-package/provenance.cde-root.1.log" ]; then
        size=$(du -sm "$dir" | cut -f1)
        deps=$(grep "node_modules/" "$dir/cde-package/provenance.cde-root.1.log" | grep READ | sed 's|.*node_modules/||' | cut -d'/' -f1 | sort -u | grep -v '^\.package-lock' | grep -v '^@' | tr '\n' ',')
        scoped=$(grep "node_modules/@" "$dir/cde-package/provenance.cde-root.1.log" | grep READ | sed 's|.*node_modules/||' | awk -F'/' '{print $1"/"$2}' | sort -u | tr '\n' ',')
        all="${deps}${scoped}"
        all=$(echo "$all" | sed 's/,*$//; s/^,//')
        if [ -z "$all" ]; then all="none"; fi
        echo "$pid: size=$size, deps=$all"
    else
        echo "$pid: N/A"
    fi
done
