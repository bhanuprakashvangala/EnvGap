"""Parse sciunit provenance log for JavaScript/Node.js runtime deps.
Extracts unique package names from node_modules/ accesses."""
import sys, json, os

log_file = sys.argv[1]
work_dir = sys.argv[2] if len(sys.argv) > 2 else "/work"

# Read package.json for version info
pkg_json_path = os.path.join(work_dir, "package.json")
versions = {}
nm_path = os.path.join(work_dir, "node_modules")
if os.path.exists(pkg_json_path):
    # Get versions from node_modules/<pkg>/package.json
    pass

# Extract all node_modules package accesses from provenance log
accessed = set()
with open(log_file) as f:
    for line in f:
        if '/node_modules/' not in line:
            continue
        after = line.split('/node_modules/')[1] if '/node_modules/' in line else ''
        parts = after.strip().split('/')
        if not parts:
            continue
        # Scoped packages: @scope/name
        if parts[0].startswith('@') and len(parts) > 1:
            pkg = parts[0] + '/' + parts[1]
        else:
            pkg = parts[0]
        if pkg and pkg != '.package-lock.json':
            accessed.add(pkg)

# Get versions from node_modules/<pkg>/package.json
runtime = {}
for pkg in sorted(accessed):
    pkg_dir = os.path.join(nm_path, pkg, "package.json")
    if os.path.exists(pkg_dir):
        try:
            with open(pkg_dir) as f:
                data = json.load(f)
                runtime[pkg] = data.get("version", "?")
        except:
            runtime[pkg] = "?"
    else:
        runtime[pkg] = "?"

for name in sorted(runtime.keys()):
    print(f"{name}@{runtime[name]}")
