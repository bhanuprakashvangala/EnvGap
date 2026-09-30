import sys, importlib.metadata

log_file = sys.argv[1]

# Build mapping: top-level import name -> (package_name, version)
pkg_map = {}
for dist in importlib.metadata.distributions():
    name = dist.metadata['Name']
    version = dist.metadata['Version']
    # From top_level.txt
    top = dist.read_text('top_level.txt')
    if top:
        for t in top.strip().split():
            pkg_map[t.strip()] = (name, version)
    # From RECORD
    rec = dist.read_text('RECORD')
    if rec:
        for line in rec.split('\n'):
            parts = line.split('/')[0].split('.')[0]
            if parts and parts not in pkg_map:
                pkg_map[parts] = (name, version)
    # Fallback
    key = name.replace('-','_').lower()
    if key not in pkg_map:
        pkg_map[key] = (name, version)

# Extract all package refs from provenance log
accessed = set()
with open(log_file) as f:
    for line in f:
        if '/dist-packages/' not in line:
            continue
        after = line.split('/dist-packages/')[1] if '/dist-packages/' in line else ''
        # Case 1: dist-packages/<pkg>/...
        # Case 2: dist-packages/__pycache__/<pkg>.cpython-xxx.pyc
        parts = after.strip().split('/')
        if not parts:
            continue
        first = parts[0]
        if first == '__pycache__' and len(parts) > 1:
            # Extract module name from __pycache__/six.cpython-310.pyc
            top = parts[1].split('.')[0]
        else:
            top = first.split('.')[0]
        if top and top != '__pycache__' and not top.endswith('libs'):
            accessed.add(top)

# Map to package names
runtime = {}
for d in sorted(accessed):
    if d in pkg_map:
        name, ver = pkg_map[d]
        runtime[name] = ver

for name in sorted(runtime.keys(), key=str.lower):
    print(f'{name}=={runtime[name]}')
