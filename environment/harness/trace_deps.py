import runpy, sys, importlib.metadata, os

# Build mapping: module top-level name -> (package_name, version)
pkg_map = {}
for dist in importlib.metadata.distributions():
    name = dist.metadata["Name"]
    version = dist.metadata["Version"]
    entry = (name, version)
    try:
        tops = dist.read_text("top_level.txt")
        if tops:
            for t in tops.strip().split():
                pkg_map[t] = entry
    except Exception:
        pass
    try:
        if dist.files:
            for fp in dist.files:
                parts = str(fp).split("/")
                if len(parts) > 1 and not parts[0].endswith(".dist-info") and "__pycache__" not in parts[0]:
                    top = parts[0].replace(".py","").split(".")[0]
                    if top and not top.startswith("_") and top not in ("bin","tests","test"):
                        pkg_map[top] = entry
    except Exception:
        pass
    pkg_map[name.replace("-","_").lower()] = entry

try:
    runpy.run_path(sys.argv[1], run_name="__main__")
except SystemExit:
    pass
except Exception as e:
    print(f"SCRIPT_ERROR: {e}", file=sys.stderr)

runtime = {}
for mod in sys.modules:
    top = mod.split(".")[0]
    if top in pkg_map:
        name, ver = pkg_map[top]
        runtime[name] = ver

with open("/tmp/runtime_deps.txt", "w") as f:
    f.write(",".join(sorted(runtime.keys(), key=str.lower)))

with open("/tmp/runtime_deps_versioned.txt", "w") as f:
    f.write(",".join(f"{k}=={runtime[k]}" for k in sorted(runtime.keys(), key=str.lower)))
