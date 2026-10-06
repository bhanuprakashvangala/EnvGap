# Code That Works, Environments That Don't

Data and analysis code for **Code That Works, Environments That Don't: Measuring Environment Reproducibility in AI-Generated Software**
Bhanu Prakash Vangala, Tanu Malik. University of Missouri.
AI Magazine (under review). Preprint: [arXiv:2610.00425](https://arxiv.org/abs/2610.00425).

Coding agents are usually scored on whether their code works, not on whether they declare the environment that code
needs. We ran Claude Code, Codex and Gemini Code Assist on 50 tasks in Python, Java, JavaScript and C++ (600 primary
runs plus 400 repeated Claude Code runs, 1,000 in total), let each agent repair its own failures, and compared three
dependency sets per project: what the agent declared, what the package manager installed, and what Sciunit traced at
runtime. This repository has the per-run results and the script that recomputes the paper's tables from them.

## Layout

```
data/prompts/        the 50 task prompts for each language and the prompt template
environment/         Dockerfiles and the Sciunit tracing / dependency extraction scripts
scripts/             reproduce.py, which recomputes the paper's numbers
results/raw/         the recorded runs: 20 CSVs, one per agent x language (x trial), 50 rows each, and run_matrix.csv
results/             tables and figures written by reproduce.py, plus verification.csv (see Results files below)
```

## Setup

The script only needs Python 3.8+. matplotlib is optional and is used for two figures.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt  # optional, for figures
```

## Reproduce

```bash
python scripts/reproduce.py
```

This takes about a second. It writes `results/*.csv`, `results/figures/*.png` and `results/verification.csv`, prints
each recomputed value next to the value in the paper, and exits with status 1 if any of them differ. All 160 checked
values match.

| Result | Where in the paper | Reproduced |
|---|---|---|
| First-attempt and final success, share of failures repaired (12 agent x language cells) | Figs. 4-6, Sec. 6.1 | yes |
| Inflation ratio \|D2\|/\|D1\|, mean and median per ecosystem | Fig. 8 | yes |
| Phantom, hidden and bloat rates (JavaScript 0.49 / 0.62 / 0.22; Python and Java phantom about 5%) | Fig. 7, Sec. 6.2 | yes |
| Precision, recall and F1 of the declared manifest against the runtime trace, including C++ | Table 4 | yes |
| Codex-Gemini JavaScript Jaccard 0.073; complete disjointness 36.0 / 56.2 / 63.3 / 57.7%, macro 53.3% | Fig. 9, Sec. 6.3 | yes |
| Claude Code's three trials: mean and median Jaccard, unanimous rate 0%, union and core size | Table 5 | yes |
| C++ system-library assumption rate (87.5 / 17.9 / 0%) and recovery | Table 6 | yes |
| Weakest task domain per agent, domain range 40-88%, final success at least 95% | Fig. 10, Sec. 6.5 | yes |
| Unnecessary dependency rate, Claude Code macro average 91.8% | Fig. 11 | yes |

Selected numbers (successful projects, primary runs):

| | Python | Java | JavaScript | C++ |
|---|---|---|---|---|
| First-attempt success, Claude / Codex / Gemini (%) | 86 / 88 / 32 | 18 / 68 / 50 | 96 / 88 / 84 | 36 / 44 / 80 |
| Final success, Claude / Codex / Gemini (%) | 100 / 100 / 100 | 100 / 100 / 96 | 100 / 100 / 100 | 100 / 94 / 98 |
| Mean inflation ratio | 2.06 | 3.97 | 11.40 | 1.00 |
| Manifest F1 vs. runtime trace (all agents) | 0.765 | 0.708 | 0.219 | 0.018 |
| Mean Jaccard across Claude's three trials | 0.113 | 0.138 | 0.068 | 0.093 |

Notes and differences from the paper:
- The CSVs are the recorded outcomes of the manual runs. Re-running the agents will not give the same projects: the
  paper's point is that dependency choices change from one generation to the next.
- For C++, runtime entries are shared-object names (`libcrypto`, `libz`). Table 4 is reproduced by dropping the `lib`
  prefix from runtime names and comparing them with the declared CMake names as written. Both `none` and `N/A` in
  `runtime_deps` mean an empty traced set.
- The paper describes the Table 6 labels and the standard-library-only tasks as manual annotations. In the data, a
  system-library failure is a first-attempt C++ failure labelled `MissingDep` or `SystemLib`, and a task counts as
  standard-library sufficient in a language if any run finished successfully with an empty manifest. These rules
  give the published numbers. Four of Codex's five such failures are mbedtls archive problems, not missing system
  packages, so the Codex row depends on the recorded label.
- The paper calls the last task domain "System Utilities"; the prompt table uses `System/Generation`. Codex's weakest
  domain is a tie at 50% between Image Processing (reported) and System/Generation.
- The Dockerfiles copy a Sciunit checkout into the build context (`COPY sciunit /opt/sciunit`); get it from
  [radiant-systems-lab/sciunit](https://github.com/radiant-systems-lab/sciunit). The C++ file does not pin G++ 12 or install
  `zlib1g-dev`, which the paper lists for its C++ image.
- Not included: the generated projects and the 927 Sciunit provenance logs (about 400 MB compressed). No number
  computed here needs them. They are available from the authors on request.

## Results files

Every file is a CSV, which opens in Excel or any spreadsheet program.

| File | Contents |
|---|---|
| `results/raw/{agent}[_trial_N]_{language}_reproducibility_analysis.csv` | 20 files, 50 rows each, one per task: the project and its manifest, the declared (`claimed_deps`), installed (`transitive_deps`) and traced (`runtime_deps`) dependencies with their counts, the first attempt (`initial_execution`) and its error, the agent's fix, the final outcome and its error, the dependency gap, and the Sciunit package size and repeat result. Claude Code has three trials; Codex and Gemini have one |
| `results/raw/run_matrix.csv` | all 1,000 runs in one table, one row per run: agent, trial, task, language, first-attempt and final success, error type, whether a fix was applied, declared and installed dependency counts, the gap, and whether a Sciunit package and a provenance log exist |
| `results/convergence.csv` | Figs. 4-6: first-attempt and final success per agent and language, and the share of first-attempt failures repaired |
| `results/inflation.csv` | Fig. 8: the ratio of installed to declared dependencies, mean and median per language |
| `results/mismatch_rates.csv` | Fig. 7: phantom, hidden and bloat rates per language |
| `results/table4_manifest_accuracy.csv` | Table 4: precision, recall and F1 of the declared manifest against the runtime trace, per agent and language |
| `results/cross_agent_agreement.csv` | Fig. 9: mean Jaccard similarity of the agents' dependency sets, and the share of tasks where they share nothing, per language and agent pair |
| `results/table5_stochastic.csv` | Table 5: agreement across Claude Code's three trials: mean and median Jaccard, unanimous tasks, union and core sizes |
| `results/table6_cpp_syslib.csv` | Table 6: C++ first-attempt failures, the share labelled as system-library problems (`slar_pct`), and the share of those later recovered (`egar_pct`) |
| `results/domains.csv` | Fig. 10: first-attempt and final success per agent and task domain |
| `results/unnecessary_dependency_rate.csv` | Fig. 11: on tasks that a run solved with no declared dependencies, the share of each agent's successful runs that declared one anyway |
| `results/figures/` | the success and mismatch figures as PNG |
| `results/verification.csv` | each of the 160 recomputed values next to the paper's, and whether they match |

`scripts/reproduce.py` writes everything except `results/raw/`.

## Related

- The earlier study that this paper extends: *AI-Generated Code Is Not Reproducible (Yet): An Empirical Study of
  Dependency Gaps in LLM-Based Coding Agents*, RAI Workshop at AAAI 2026, [arXiv:2512.22387](https://arxiv.org/abs/2512.22387);
  extended version at ACM REP 2026, [doi:10.1145/3820002.3828581](https://doi.org/10.1145/3820002.3828581).
- [EnvGap on Hugging Face](https://huggingface.co/datasets/bhanuprakashvangala/EnvGap), a follow-up benchmark in which
  agents repair the environment of real GitHub issues. It does not contain the data in this repository.
  The lite version in the benchmarks is the dataset that we have used here for the study of above.

## Citation

```bibtex
@misc{vangala2026codeworksenvironmentsdont,
      title={Code That Works, Environments That Don't: Measuring Environment Reproducibility in AI-Generated Software},
      author={Bhanu Prakash Vangala and Tanu Malik},
      year={2026},
      eprint={2610.00425},
      archivePrefix={arXiv},
      primaryClass={cs.SE},
      url={https://arxiv.org/abs/2610.00425},
}
```

## License

Code: MIT. Data and prompts: CC BY 4.0.
