# Characterizing the Noise-Induced Divergence Depth in QAOA for MaxCut

**Authors:** Arhaan Sareen, Aditya Saxena

**Affiliation:** QSYS 2026 Participant, Institute for Quantum Computing, University of Waterloo

**Status:** [arXiv link TBD] · [JSR submission TBD]

---

## Overview

This repository contains the full benchmark codebase, LaTeX manuscript, and supporting materials for our paper studying how hardware noise limits QAOA performance on near-term quantum devices.

We introduce the **divergence depth** p*(n) — the maximum QAOA circuit depth before noise-induced performance degradation dominates — and measure it empirically across qubit sizes n ∈ {6, 8, 10, 12} and circuit depths p ∈ {1, 2, 3, 4, 5} on IBM superconducting hardware.

## Research Question

**Primary:** How does the QAOA approximation ratio for MaxCut scale with circuit depth p and problem size n on near-term noisy IBM hardware, compared to ideal simulation — and at what depth p* does hardware performance diverge below noiseless simulation?

**Sub-questions:**
1. At what circuit depth does real hardware approximation ratio peak and then decline?
2. How does p* change as n increases from 6 to 12 qubits?
3. How accurately does Qiskit's FakeSherbrooke noise model predict real hardware results?
4. Where does noisy QAOA fall relative to classical baselines (GW SDP, greedy, random)?

## Repository Structure

```
qsys-paper/
├── code/
│   ├── qaoa_benchmark.py    # Full benchmark suite (graph gen, solvers, QAOA, optimization)
│   ├── plot_results.py      # Figure generation (6 publication-quality plots)
│   ├── requirements.txt     # Python dependencies
│   └── results/             # Benchmark output (JSON + CSV, generated at runtime)
├── paper/
│   ├── main.tex             # Complete LaTeX manuscript
│   └── bibliography.bib    # BibTeX references (15 entries)
├── figures/                 # Generated plots at 300 DPI (populated by plot_results.py)
├── notes/
│   ├── literature_review.md # Annotated notes on 14 key papers
│   ├── research_questions.md
│   ├── meeting_notes.md
│   ├── email_patterson.txt  # Draft mentor cold emails
│   ├── email_anand.txt
│   └── email_donohue.txt
└── README.md
```

## Environment Setup

```bash
git clone [repo-url]
cd qsys-paper
pip install -r code/requirements.txt
```

**IBM Quantum hardware access** (optional): Set the `IBM_QUANTUM_TOKEN` environment variable to your IBM Quantum API token. Without it, noiseless and noisy simulations run fully — only hardware jobs are skipped.

```bash
export IBM_QUANTUM_TOKEN="your_token_here"
```

Free-tier access: create an account at quantum.ibm.com. Expect 1–12 hour queue times.

## Running the Benchmark

```bash
python code/qaoa_benchmark.py
```

This runs the full experiment sweep:
- **Graph families:** 3-regular (primary), Erdős-Rényi G(n, 0.5) (secondary)
- **System sizes:** n ∈ {6, 8, 10, 12} qubits
- **Circuit depths:** p ∈ {1, 2, 3, 4, 5}
- **Instances:** 30 per (n, graph type) with deterministic seeds
- **Classical baselines:** brute-force MaxCut, greedy, Goemans-Williamson SDP
- **Noise conditions:** noiseless (statevector), FakeSherbrooke, real hardware (if token set)

**Estimated runtimes:**

| Condition | Estimated time |
|-----------|----------------|
| Noiseless only | ~2–4 hours |
| + FakeSherbrooke noisy sim | ~8–16 hours |
| + Hardware (n=6,8, p=1,2) | +variable (queue dependent) |

Results save incrementally to `code/results/benchmark_results.json` and `.csv`. Benchmark resumes from the last checkpoint if interrupted.

## Generating Figures

```bash
python code/plot_results.py
```

Generates 6 figures (300 DPI) in `figures/`:

| Figure | Description |
|--------|-------------|
| `fig1_qaoa_circuit.png` | QAOA circuit diagram (p=1, n=4 cycle graph) |
| `fig2_ar_vs_depth.png` | AR vs p: noiseless vs noisy vs hardware (main result) |
| `fig3_scaling_ar_vs_n.png` | AR vs n at fixed p (scaling degradation) |
| `fig4_fake_vs_hardware.png` | FakeSherbrooke vs real hardware validation |
| `fig5_baselines_comparison.png` | QAOA vs classical baselines at n=10 |
| `fig6_divergence_heatmap.png` | AR heatmap over (p, n) grid |

## Compiling the Paper

```bash
cd paper
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

Or open `paper/main.tex` in Overleaf with `bibliography.bib` in the same project.

## Key Results

| Condition | n=6, p=1 AR | n=10, p=3 AR | p* (n=10) |
|-----------|-------------|--------------|-----------|
| Noiseless | TBD | TBD | N/A |
| FakeSherbrooke | TBD | TBD | TBD |
| IBM Hardware | TBD | TBD | TBD |
| GW SDP (classical) | ~0.94 | ~0.94 | N/A |

*(Populated after experiments complete)*

## Timeline

| Date | Milestone |
|------|-----------|
| Sep 1–7, 2026 | Send mentor cold emails (drafts in notes/) |
| Sep 8–21 | Run all simulations |
| Sep 22 – Oct 1 | Push to GitHub, run IBM Quantum hardware jobs |
| Oct 1–15 | Data analysis, all figures, send to mentor |
| Nov 1 | First full draft (hard deadline — ED applications) |
| Jan 1, 2027 | arXiv submission |
| Mar 1, 2027 | Journal of Student Research submission |

## Citation

```bibtex
@misc{sareen2027qaoa,
  title         = {Characterizing the Noise-Induced Divergence Depth in QAOA for MaxCut},
  author        = {Sareen, Arhaan and {[Co-Author]}},
  year          = {2027},
  eprint        = {[arXiv ID TBD]},
  archivePrefix = {arXiv},
  primaryClass  = {quant-ph}
}
```

## License

- Code: MIT License
- Paper text: CC BY 4.0
