#!/usr/bin/env python3
"""Recompute the paper's tables and figure values from data/results/*.csv.

    python scripts/reproduce.py

Standard library only. matplotlib is optional and only used for figures.
Writes CSVs to results/ and prints every recomputed value beside the value
published in the paper. Exits non-zero if any checked value differs.
"""
import csv
import glob
import os
import re
import statistics
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_IN = os.path.join(ROOT, "data", "results")
PROMPTS = os.path.join(ROOT, "data", "prompts", "prompt_overview.csv")
OUT = os.path.join(ROOT, "results")

LANGS = ["python", "java", "javascript", "cpp"]
AGENTS = ["claude", "codex", "gemini"]

# ---------------------------------------------------------------------------
# Values printed in the paper (AI Magazine submission, 16 pages).
# ---------------------------------------------------------------------------
PAPER = {
    # Figure 4 / Figure 6: first-attempt success rate SR(0), %
    "sr0": {("claude", "python"): 86, ("claude", "java"): 18, ("claude", "javascript"): 96, ("claude", "cpp"): 36,
            ("codex", "python"): 88, ("codex", "java"): 68, ("codex", "javascript"): 88, ("codex", "cpp"): 44,
            ("gemini", "python"): 32, ("gemini", "java"): 50, ("gemini", "javascript"): 84, ("gemini", "cpp"): 80},
    # Section 6.1: final success rate after repair, %
    "srf": {("claude", "python"): 100, ("claude", "java"): 100, ("claude", "javascript"): 100, ("claude", "cpp"): 100,
            ("codex", "python"): 100, ("codex", "java"): 100, ("codex", "javascript"): 100, ("codex", "cpp"): 94,
            ("gemini", "python"): 100, ("gemini", "java"): 96, ("gemini", "javascript"): 100, ("gemini", "cpp"): 98},
    # Figure 5: share of failed first attempts repaired within budget, %
    "repair": {("claude", "python"): 100, ("claude", "java"): 100, ("claude", "javascript"): 100, ("claude", "cpp"): 100,
               ("codex", "python"): 100, ("codex", "java"): 100, ("codex", "javascript"): 100, ("codex", "cpp"): 89,
               ("gemini", "python"): 100, ("gemini", "java"): 92, ("gemini", "javascript"): 100, ("gemini", "cpp"): 90},
    # Figure 8: inflation ratio rho = |D2|/|D1| (mean, median)
    "rho": {"python": (2.06, 1.5), "java": (3.97, 1.7), "javascript": (11.40, 8.5), "cpp": (1.00, 1.0)},
    # Section 6.2 text: JavaScript phantom / hidden / bloat rates (approx., "about")
    "js_rates": (0.49, 0.62, 0.22),
    # Table 4: precision, recall, F1 of D1 against D3
    "prf": {("claude", "python"): (.990, .642, .733), ("claude", "java"): (.935, .739, .758),
            ("claude", "javascript"): (.929, .406, .493), ("claude", "cpp"): (.037, .781, .031),
            ("codex", "python"): (.938, .827, .837), ("codex", "java"): (.939, .684, .735),
            ("codex", "javascript"): (.214, .143, .143), ("codex", "cpp"): (.062, .658, .004),
            ("gemini", "python"): (.899, .721, .756), ("gemini", "java"): (.947, .523, .624),
            ("gemini", "javascript"): (.040, .182, .005), ("gemini", "cpp"): (.059, .708, .004),
            ("all", "python"): (.944, .713, .765), ("all", "java"): (.940, .653, .708),
            ("all", "javascript"): (.413, .258, .219), ("all", "cpp"): (.049, .729, .018)},
    # Section 6.3: complete disjointness rate (%) and Codex-Gemini JS Jaccard
    "cdr": {"python": 36.0, "java": 56.2, "javascript": 63.3, "cpp": 57.7, "macro": 53.3},
    "jaccard_codex_gemini_js": 0.073,
    # Table 5: mean intra-agent J, median J, n, UCR count, mean |union|, mean |core|
    "t5": {"python": (0.113, 0.083, 50, 0, 5.5, 0.2), "java": (0.138, 0.111, 48, 0, 5.6, 0.1),
           "javascript": (0.068, 0.000, 50, 0, 5.9, 0.0), "cpp": (0.093, 0.067, 35, 0, 5.3, 0.1)},
    # Table 6: C++ first-attempt failures, SysLib count, SLAR %, recovered, EGAR %
    "t6": {"claude": (32, 28, 87.5, 28, 100.0), "codex": (28, 5, 17.9, 5, 100.0), "gemini": (10, 0, 0.0, 0, None)},
    # Section 6.5: unnecessary dependency rate, Claude macro average %
    "udr_claude_macro": 91.8,
    # Section 6.5: weakest first-attempt domain per agent (pooled over languages), %
    "domain_min": {"claude": ("System/Generation", 40), "codex": ("Image Processing", 50),
                   "gemini": ("Data Processing", 48)},
    "domain_sr0_range": (40, 88),
    "domain_final_min": 95,
    # Section 4.2: C++ successful manifests declaring nlohmann_json
    "nlohmann_json": 65,
}

# ---------------------------------------------------------------------------
# Loading and normalisation
# ---------------------------------------------------------------------------


def truthy(v):
    return (v or "").strip().lower() in ("true", "1", "yes", "success")


def norm_dep(tok, lang, runtime=False):
    """Canonical package name for every manifest dialect in the CSVs."""
    t = tok.strip()
    if not t or t.lower() in ("none", "n/a", "-"):
        return None
    if lang == "python":
        t = re.split(r"[=<>!~\[]", t)[0]                   # pandas==2.2.2 -> pandas
    elif lang == "java":
        t = re.sub(r"\.jar$", "", t)                       # commons-csv-1.10.0.jar
        t = t.split(":")[0] if ":" in t else re.sub(r"-\d[\w.\-]*$", "", t)
    elif lang == "cpp" and runtime:
        # runtime entries are shared objects (libcrypto, libz.so.1); drop the lib prefix
        t = re.sub(r"\.so.*$", "", t.lower())
        t = re.sub(r"^lib", "", t)
    return t.strip().lower().replace("_", "-") or None


def depset(s, lang, runtime=False):
    return {d for d in (norm_dep(p, lang, runtime) for p in (s or "").split(",")) if d}


def load():
    pat = re.compile(r"(claude|codex|gemini)(?:_trial_(\d))?_(python|java|javascript|cpp)_")
    rows = []
    for f in sorted(glob.glob(os.path.join(RESULTS_IN, "*.csv"))):
        m = pat.match(os.path.basename(f))
        if not m:
            continue
        with open(f, encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                r["_agent"], r["_trial"], r["_lang"] = m.group(1), m.group(2) or "1", m.group(3)
                r["_ok0"] = truthy(r["initial_execution"])
                r["_ok"] = truthy(r["final_execution"])
                rows.append(r)
    return rows


def as_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Comparison bookkeeping
# ---------------------------------------------------------------------------
CHECKS = []


def check(claim, paper, mine, tol, fmt="{:.3f}"):
    ok = paper is None and mine is None or (paper is not None and mine is not None and abs(mine - paper) <= tol)
    f = lambda x: "-" if x is None else fmt.format(x)
    CHECKS.append((claim, f(paper), f(mine), "yes" if ok else "NO"))
    return ok


def write_csv(name, header, rows):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


def mean(xs):
    return statistics.mean(xs) if xs else 0.0


# ---------------------------------------------------------------------------
# Section 6.1 protocol convergence
# ---------------------------------------------------------------------------


def convergence(primary):
    out = []
    for a in AGENTS:
        for l in LANGS:
            sub = [r for r in primary if r["_agent"] == a and r["_lang"] == l]
            n = len(sub)
            sr0 = 100 * sum(r["_ok0"] for r in sub) / n
            srf = 100 * sum(r["_ok"] for r in sub) / n
            failed = [r for r in sub if not r["_ok0"]]
            rep = 100 * sum(r["_ok"] for r in failed) / len(failed) if failed else 100.0
            out.append((a, l, n, round(sr0, 1), round(srf, 1), len(failed), round(rep, 1)))
            check(f"SR0 {a} {l} (%)", PAPER["sr0"][(a, l)], sr0, 0.5, "{:.0f}")
            check(f"Final SR {a} {l} (%)", PAPER["srf"][(a, l)], srf, 0.5, "{:.0f}")
            check(f"Repaired share of failed first attempts {a} {l} (%)", PAPER["repair"][(a, l)], rep, 0.5, "{:.0f}")
    write_csv("convergence.csv", ["agent", "language", "n", "sr0_pct", "final_sr_pct", "first_attempt_failures",
                                  "repaired_pct"], out)
    return out


# ---------------------------------------------------------------------------
# Section 6.2 specification quality
# ---------------------------------------------------------------------------


def inflation(primary):
    out = []
    for l in LANGS:
        vals = []
        for r in primary:
            if r["_lang"] != l or not r["_ok"]:
                continue
            c, t = as_int(r["claimed_count"]), as_int(r["transitive_count"])
            if c and t is not None:
                vals.append(t / c)
        mu, med = mean(vals), statistics.median(vals)
        out.append((l, len(vals), round(mu, 2), round(med, 2)))
        pm, pmed = PAPER["rho"][l]
        check(f"Inflation rho mean {l}", pm, mu, 0.005, "{:.2f}")
        check(f"Inflation rho median {l}", pmed, med, 0.05, "{:.2f}")
    write_csv("inflation.csv", ["language", "n_successful", "rho_mean", "rho_median"], out)


def mismatch_rates(primary):
    """Phantom |D1\\D3|/|D1|, hidden |D3\\D1|/|D3|, bloat |D2\\D3|/|D2|; 0 when the denominator is 0."""
    out = []
    for l in LANGS:
        ph, hi, bl = [], [], []
        for r in primary:
            if r["_lang"] != l or not r["_ok"]:
                continue
            d1 = depset(r["claimed_deps"], l)
            d2 = depset(r["transitive_deps"], l)
            d3 = depset(r["runtime_deps"], l, runtime=True)
            ph.append(len(d1 - d3) / len(d1) if d1 else 0.0)
            hi.append(len(d3 - d1) / len(d3) if d3 else 0.0)
            bl.append(len(d2 - d3) / len(d2) if d2 else 0.0)
        out.append((l, len(ph), round(mean(ph), 3), round(mean(hi), 3), round(mean(bl), 3)))
    write_csv("mismatch_rates.csv", ["language", "n_successful", "phantom", "hidden", "bloat"], out)
    for r in out:
        if r[0] in ("python", "java"):
            check(f"{r[0].capitalize()} phantom rate (text says 'about 5%')", 0.05, r[2], 0.01, "{:.2f}")
    js = [r for r in out if r[0] == "javascript"][0]
    for name, p, m in zip(("phantom", "hidden", "bloat"), PAPER["js_rates"], js[2:]):
        check(f"JavaScript {name} rate (text says 'about')", p, m, 0.015, "{:.2f}")
    return out


def prf(rows):
    P, R, F = [], [], []
    for r in rows:
        l = r["_lang"]
        d1, d3 = depset(r["claimed_deps"], l), depset(r["runtime_deps"], l, runtime=True)
        n1, n3 = len(d1), len(d3)
        if n1 == 0 and n3 == 0:
            continue
        i = len(d1 & d3)
        p = 1.0 if n1 == 0 else i / n1
        rc = 1.0 if n3 == 0 else i / n3
        P.append(p)
        R.append(rc)
        F.append(0.0 if p + rc == 0 else 2 * p * rc / (p + rc))
    return len(P), mean(P), mean(R), mean(F)


def table4(primary):
    out = []
    for a in AGENTS + ["all"]:
        for l in LANGS:
            sub = [r for r in primary if r["_lang"] == l and r["_ok"] and (a == "all" or r["_agent"] == a)]
            n, p, rc, f1 = prf(sub)
            out.append((a, l, n, round(p, 3), round(rc, 3), round(f1, 3)))
            pp = PAPER["prf"][(a, l)]
            for name, q, m in zip(("P", "R", "F1"), pp, (p, rc, f1)):
                check(f"Table 4 {name} {a} {l}", q, m, 0.0015)
    write_csv("table4_manifest_accuracy.csv", ["agent", "language", "n", "precision", "recall", "f1"], out)


# ---------------------------------------------------------------------------
# Section 6.3 cross- and intra-agent agreement
# ---------------------------------------------------------------------------


def jac(a, b):
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def cross_agent(primary):
    idx = {(r["_agent"], r["_lang"], r["prompt_id"]): r for r in primary}
    out, cdrs = [], {}
    for l in LANGS:
        allj = []
        for a, b in (("claude", "codex"), ("claude", "gemini"), ("codex", "gemini")):
            js = []
            for pid in sorted({r["prompt_id"] for r in primary if r["_lang"] == l}):
                ra, rb = idx.get((a, l, pid)), idx.get((b, l, pid))
                if ra and rb and ra["_ok"] and rb["_ok"]:
                    js.append(jac(depset(ra["claimed_deps"], l), depset(rb["claimed_deps"], l)))
            allj += js
            out.append((l, f"{a}-{b}", len(js), round(mean(js), 3), round(100 * sum(j == 0 for j in js) / len(js), 1)))
            if l == "javascript" and (a, b) == ("codex", "gemini"):
                check("Cross-agent Jaccard Codex-Gemini JavaScript", PAPER["jaccard_codex_gemini_js"], mean(js), 0.0015)
        cdrs[l] = 100 * sum(j == 0 for j in allj) / len(allj)
        out.append((l, "all pairs", len(allj), round(mean(allj), 3), round(cdrs[l], 1)))
        check(f"Complete disjointness rate {l} (%)", PAPER["cdr"][l], cdrs[l], 0.05, "{:.1f}")
    macro = mean(list(cdrs.values()))
    check("Complete disjointness rate, macro average (%)", PAPER["cdr"]["macro"], macro, 0.05, "{:.1f}")
    write_csv("cross_agent_agreement.csv", ["language", "pair", "n_tasks", "mean_jaccard", "cdr_pct"], out)


def table5(rows):
    out = []
    for l in LANGS:
        by_task = defaultdict(dict)
        for r in rows:
            if r["_agent"] == "claude" and r["_lang"] == l:
                by_task[r["prompt_id"]][r["_trial"]] = r
        js, uni, core, n, unanimous = [], [], [], 0, 0
        for trials in by_task.values():
            if len(trials) < 3 or not all(t["_ok"] for t in trials.values()):
                continue
            n += 1
            sets = [depset(trials[t]["claimed_deps"], l) for t in ("1", "2", "3")]
            unanimous += sets[0] == sets[1] == sets[2]
            js.append(mean([jac(sets[i], sets[j]) for i in range(3) for j in range(i + 1, 3)]))
            uni.append(len(sets[0] | sets[1] | sets[2]))
            core.append(len(sets[0] & sets[1] & sets[2]))
        row = (l, n, round(mean(js), 3), round(statistics.median(js), 3), unanimous,
               round(mean(uni), 1), round(mean(core), 1))
        out.append(row)
        pj, pmed, pn, pu, pv, pc = PAPER["t5"][l]
        check(f"Table 5 mean intra-agent J {l}", pj, mean(js), 0.0015)
        check(f"Table 5 median J {l}", pmed, statistics.median(js), 0.0015)
        check(f"Table 5 tasks with 3 successful trials {l}", pn, n, 0, "{:.0f}")
        check(f"Table 5 unanimous (UCR count) {l}", pu, unanimous, 0, "{:.0f}")
        check(f"Table 5 mean vocabulary union {l}", pv, mean(uni), 0.05, "{:.1f}")
        check(f"Table 5 mean unanimous core {l}", pc, mean(core), 0.05, "{:.1f}")
    write_csv("table5_stochastic.csv", ["language", "n_tasks", "mean_jaccard", "median_jaccard", "unanimous",
                                        "mean_union", "mean_core"], out)


# ---------------------------------------------------------------------------
# Section 6.4 C++ environment gap (Table 6)
# ---------------------------------------------------------------------------
# The CSVs label a missing system library at the first attempt as MissingDep or SystemLib.
SYSLIB_LABELS = {"MissingDep", "SystemLib"}


def table6(primary):
    out = []
    for a in AGENTS:
        fails = [r for r in primary if r["_agent"] == a and r["_lang"] == "cpp" and not r["_ok0"]]
        sys_ = [r for r in fails if r["initial_error_type"].strip() in SYSLIB_LABELS]
        rec = [r for r in sys_ if r["_ok"]]
        slar = 100 * len(sys_) / len(fails) if fails else 0.0
        egar = 100 * len(rec) / len(sys_) if sys_ else None
        out.append((a, len(fails), len(sys_), round(slar, 1), len(rec), "" if egar is None else round(egar, 1)))
        pf, ps, pslar, prec, pegar = PAPER["t6"][a]
        check(f"Table 6 C++ first-attempt failures {a}", pf, len(fails), 0, "{:.0f}")
        check(f"Table 6 SysLib failures {a}", ps, len(sys_), 0, "{:.0f}")
        check(f"Table 6 SLAR {a} (%)", pslar, slar, 0.05, "{:.1f}")
        check(f"Table 6 recovered {a}", prec, len(rec), 0, "{:.0f}")
        check(f"Table 6 EGAR {a} (%)", pegar, egar, 0.05, "{:.1f}")
    write_csv("table6_cpp_syslib.csv", ["agent", "first_attempt_failures", "syslib", "slar_pct", "recovered",
                                        "egar_pct"], out)


# ---------------------------------------------------------------------------
# Section 6.5 task sensitivity
# ---------------------------------------------------------------------------


def domains(primary):
    cat = {}
    with open(PROMPTS, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            cat[r["prompt_id"]] = r["category"]
    out = defaultdict(dict)
    rows = []
    for a in AGENTS:
        for d in sorted(set(cat.values())):
            sub = [r for r in primary if r["_agent"] == a and cat.get(r["prompt_id"]) == d]
            sr0 = 100 * sum(r["_ok0"] for r in sub) / len(sub)
            srf = 100 * sum(r["_ok"] for r in sub) / len(sub)
            out[a][d] = (sr0, srf)
            rows.append((a, d, len(sub), round(sr0, 1), round(srf, 1)))
    write_csv("domains.csv", ["agent", "domain", "n", "sr0_pct", "final_sr_pct"], rows)
    for a in AGENTS:
        d, v = PAPER["domain_min"][a]
        worst = min(out[a], key=lambda k: out[a][k][0])
        check(f"Weakest first-attempt domain {a}: {d} (%)", v, out[a][d][0] if worst == d else None, 0.5, "{:.0f}")
    all0 = [v[0] for a in AGENTS for v in out[a].values()]
    allf = [v[1] for a in AGENTS for v in out[a].values()]
    check("Domain SR0 range, low (%)", PAPER["domain_sr0_range"][0], min(all0), 0.5, "{:.0f}")
    check("Domain SR0 range, high (%)", PAPER["domain_sr0_range"][1], max(all0), 0.5, "{:.0f}")
    check("Lowest final SR over agent-domain pairs, at least (%)", PAPER["domain_final_min"],
          PAPER["domain_final_min"] if min(allf) >= PAPER["domain_final_min"] else min(allf), 0, "{:.0f}")


def udr(rows, primary):
    # A task is standard-library sufficient in a language if any run (any agent/trial)
    # succeeded with an empty manifest.
    stdlib = defaultdict(set)
    for r in rows:
        if r["_ok"] and as_int(r["claimed_count"]) == 0:
            stdlib[r["_lang"]].add(r["prompt_id"])
    out = []
    macro = {}
    for a in AGENTS:
        pct = []
        for l in LANGS:
            sub = [r for r in primary if r["_agent"] == a and r["_lang"] == l and r["_ok"]
                   and r["prompt_id"] in stdlib[l]]
            num = sum((as_int(r["claimed_count"]) or 0) >= 1 for r in sub)
            p = 100 * num / len(sub) if sub else 0.0
            pct.append(p)
            out.append((a, l, len(sub), num, round(p, 1)))
        macro[a] = mean(pct)
        out.append((a, "macro", "", "", round(macro[a], 1)))
    check("Unnecessary dependency rate, Claude macro average (%)", PAPER["udr_claude_macro"], macro["claude"], 0.05,
          "{:.1f}")
    write_csv("unnecessary_dependency_rate.csv", ["agent", "language", "n_tasks", "with_external_dep", "udr_pct"], out)


def misc(rows, primary):
    n = sum(1 for r in primary if r["_lang"] == "cpp" and r["_ok"] and "nlohmann-json" in depset(r["claimed_deps"], "cpp"))
    check("C++ successful manifests declaring nlohmann_json", PAPER["nlohmann_json"], n, 0, "{:.0f}")
    check("Total evaluation runs", 1000, len(rows), 0, "{:.0f}")
    check("Primary runs", 600, len(primary), 0, "{:.0f}")
    with open(os.path.join(ROOT, "data", "run_matrix.csv"), encoding="utf-8", newline="") as fh:
        traced = sum(truthy(r["has_provenance_log"]) for r in csv.DictReader(fh))
    print(f"runs with a runtime provenance log (run_matrix.csv): {traced}")
    with open(PROMPTS, encoding="utf-8", newline="") as fh:
        counts = defaultdict(int)
        for r in csv.DictReader(fh):
            counts[r["category"]] += 1
    table1 = {"Data Processing": 10, "Cryptography": 7, "Image Processing": 6, "Networking": 6,
              "Text Processing": 6, "Compression": 5, "Math/Scientific": 5, "System/Generation": 5}
    for d, v in table1.items():
        check(f"Table 1 tasks in domain {d}", v, counts[d], 0, "{:.0f}")


# ---------------------------------------------------------------------------
# Optional figures
# ---------------------------------------------------------------------------


def figures(conv, rates):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed; skipping figures")
        return
    fig_dir = os.path.join(OUT, "figures")
    os.makedirs(fig_dir, exist_ok=True)
    labels = {"python": "Python", "java": "Java", "javascript": "JavaScript", "cpp": "C++"}
    colors = {"claude": "#4E79A7", "codex": "#F28E2B", "gemini": "#59A14F"}

    fig, ax = plt.subplots(figsize=(7, 3.5))
    w = 0.26
    for i, a in enumerate(AGENTS):
        sr0 = [r[3] for r in conv if r[0] == a]
        srf = [r[4] for r in conv if r[0] == a]
        xs = [j + (i - 1) * w for j in range(len(LANGS))]
        ax.bar(xs, sr0, w, color=colors[a], label=a.capitalize())
        ax.bar(xs, [f - s for f, s in zip(srf, sr0)], w, bottom=sr0, color=colors[a], alpha=0.35, hatch="//")
    ax.set_xticks(range(len(LANGS)))
    ax.set_xticklabels([labels[l] for l in LANGS])
    ax.set_ylabel("Success rate (%)")
    ax.set_title("Protocol convergence (solid: first attempt, hatched: repair gain)")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(fig_dir, "fig6_convergence_by_language.png"), dpi=200)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 3.2))
    w = 0.26
    for i, (name, col) in enumerate((("Phantom", 2), ("Hidden", 3), ("Bloat", 4))):
        ax.bar([j + (i - 1) * w for j in range(len(LANGS))], [r[col] * 100 for r in rates], w, label=name)
    ax.set_xticks(range(len(LANGS)))
    ax.set_xticklabels([labels[l] for l in LANGS])
    ax.set_ylabel("Mean rate (%)")
    ax.set_title("Phantom, hidden and bloat rates (successful projects)")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(fig_dir, "fig7_mismatch_rates.png"), dpi=200)
    plt.close(fig)


def main():
    rows = load()
    if not rows:
        sys.exit(f"no result CSVs found in {RESULTS_IN}")
    primary = [r for r in rows if r["_trial"] == "1"]
    print(f"loaded {len(rows)} runs ({len(primary)} primary, {len(rows) - len(primary)} stochastic)")

    conv = convergence(primary)
    inflation(primary)
    rates = mismatch_rates(primary)
    table4(primary)
    cross_agent(primary)
    table5(rows)
    table6(primary)
    domains(primary)
    udr(rows, primary)
    misc(rows, primary)
    figures(conv, rates)

    write_csv("verification.csv", ["claim", "paper", "reproduced", "match"], CHECKS)
    width = max(len(c[0]) for c in CHECKS)
    print(f"\n{'claim':<{width}}  {'paper':>7}  {'ours':>7}  match")
    for c in CHECKS:
        print(f"{c[0]:<{width}}  {c[1]:>7}  {c[2]:>7}  {c[3]}")
    bad = [c for c in CHECKS if c[3] != "yes"]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} values match the paper. Tables written to results/.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
