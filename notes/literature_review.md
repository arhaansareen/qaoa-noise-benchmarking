# Literature Review — Annotated

**Paper:** "Characterizing the Noise-Induced Divergence Depth in QAOA for MaxCut"
**Last updated:** September 2026

---

## Farhi, Goldstone, Gutmann (2014) — "A Quantum Approximate Optimization Algorithm"
**Citation:** arXiv:1411.4028
**Core Numerical Finding:** At p=1 on 3-regular MaxCut graphs, QAOA achieves an analytically proven approximation ratio AR ≥ 0.6924.
**Relevance:** This is the foundational QAOA paper that every subsequent work cites. The p=1 bound of 0.6924 serves as our primary noiseless baseline for sanity-checking simulation results; any noiseless p=1 result below this for 3-regular graphs indicates an implementation error.

---

## Zhou et al. (2020) — "Quantum Approximate Optimization Algorithm: Performance, Mechanism, and Implementation on Near-Term Devices"
**Citation:** PRX Quantum 10, 021067 (2020); arXiv:1812.01041
**Core Numerical Finding:** Simulation at p=11 achieves AR ~0.94+ on random 3-regular graphs; TQA initialization (γ_k = k/p · γ_max, β_k = (1-k/p) · β_max) significantly outperforms random initialization; optimal angles concentrate across instances of the same graph family.
**Relevance:** We directly adopt the TQA initialization strategy introduced in this paper for our COBYLA optimization at p≥2. The angle concentration result also justifies our fixed-angle hardware protocol: angles optimized on the noiseless simulator transfer reliably to hardware.

---

## Goemans & Williamson (1995) — "Improved Approximation Algorithms for Maximum Cut and Satisfiability Problems Using Semidefinite Programming"
**Citation:** Journal of the ACM, 42(6):1115–1145 (1995). DOI: 10.1145/227683.227684
**Core Numerical Finding:** SDP-based algorithm achieves AR ≥ 0.8786 for MaxCut in the worst case; typically AR ~0.93–0.95 on random graphs; this ratio is optimal for polynomial-time classical algorithms under the Unique Games Conjecture.
**Relevance:** GW is our primary classical comparison point. Every QAOA AR result in our paper is contextualized against GW performance; hardware QAOA remaining below GW (as expected at current scale) is reported honestly without overclaiming.

---

## Harrigan et al. (2021) — "Quantum Approximate Optimization of Non-Planar Graph Problems on a Planar Superconducting Processor"
**Citation:** Nature Physics 17, 332–336 (2021). DOI: 10.1038/s41567-020-01105-y
**Core Numerical Finding:** On Google Sycamore (n=23 qubits, p=3): hardware AR ≈ 0.735 versus ideal AR ≈ 0.834; essentially no AR improvement from p=2 to p=3 on hardware, suggesting noise floor around p=2–3.
**Relevance:** This is the most cited hardware QAOA experiment and directly supports our hypothesis that p*≤3 on superconducting hardware. We compare our IBM results to their Google Sycamore results to assess platform dependence of the divergence depth.

---

## Lotshaw et al. (2021) — "Empirical Performance Bounds for Quantum Optimization Algorithms"
**Citation:** arXiv:2102.04649
**Core Numerical Finding:** IBM hardware (ibmq_guadalupe, n=16, p=3): hardware AR ≈ 0.55–0.62 versus ideal 0.69; performance at p=3 is lower than p=1 on hardware, confirming superlinear noise growth with p.
**Relevance:** This paper provides the closest direct precedent to our work: IBM hardware, MaxCut QAOA, systematic depth sweep. The counterintuitive finding that p=3 underperforms p=1 on hardware is central to our divergence depth concept; we extend this analysis with statistical rigor (CI across 30 instances) and smaller, fully verified instances.

---

## Weidenfeller et al. (2022) — "Scaling of the Quantum Approximate Optimization Algorithm on Superconducting Qubit Based Hardware"
**Citation:** arXiv:2202.03459
**Core Numerical Finding:** IBM Montreal (n=6 to n=16, p=1): hardware AR ≈ 0.57 at n=16, decreasing monotonically with n; 2-qubit gate count grows with routing overhead.
**Relevance:** Establishes the n-scaling of hardware AR degradation at fixed p — a key component of our 2D (p × n) analysis. We extend their n-sweep by also sweeping p, enabling us to trace p*(n) as a curve rather than a single point.

---

## Pelofske, Bärtschi, Eidenbenz (2022) — "Quantum Annealing vs. QAOA: 127 Qubit Higher-Order Ising Problems on NISQ Computers"
**Citation:** arXiv:2301.07000
**Core Numerical Finding:** Multi-platform: IBM kolkata (n=12, p=3) AR ≈ 0.58; Quantinuum H1 (n=10, p=3) AR ≈ 0.70; IonQ (n=8, p=1) AR ≈ 0.72. Trapped-ion platforms outperform IBM superconducting at higher p due to lower 2Q error rates.
**Relevance:** Contextualizes our IBM results within the broader hardware landscape. We cite this to acknowledge that our IBM-specific divergence depth p* is not universal — lower-error-rate devices (Quantinuum, IonQ) will exhibit higher p*.

---

## Shaydulin et al. (2023) — "Evidence of Scaling Advantage for the Quantum Approximate Optimization Algorithm on a Classically Intractable Problem"
**Citation:** Science Advances 10, eadm6170 (2023); arXiv:2308.02342
**Core Numerical Finding:** IonQ Forte (n=32, p=1): hardware AR ≈ 0.79; paper claims evidence of a scaling advantage in optimization landscape traversal.
**Relevance:** This is the most recent high-profile hardware QAOA result and sets the state of the art for large-scale hardware experiments. We cite it to frame our study as complementary: they demonstrate frontier capability on a low-noise platform; we characterize noise-induced limits on widely accessible IBM hardware.

---

## Stilck França & Garcia-Patron (2021) — "Limitations of Optimization Algorithms on Noisy Quantum Devices"
**Citation:** arXiv:2012.05766
**Core Numerical Finding:** Proved that for noisy circuits with T two-qubit gates at error rate ε, achievable optimization accuracy degrades by Ω(εT); for QAOA at depth p: additive error grows as O(ε·n·p).
**Relevance:** This is the theoretical backbone of our divergence depth concept. We use the O(ε·n·p) prediction to fit and interpret our empirical p*(n) measurements; the theoretical bound gives a principled reason why p* should decrease as n increases.

---

## Wang et al. (2021) — "Noise-Induced Barren Plateaus in Variational Quantum Algorithms"
**Citation:** arXiv:2007.14384
**Core Numerical Finding:** Under depolarizing noise, cost function gradient variance scales as O(exp(-αnp)), causing optimization to become exponentially harder with circuit depth and system size.
**Relevance:** Explains why hardware QAOA performance degrades beyond p* even if the circuit itself is error-free: noise causes gradients to vanish, making parameter optimization unreliable. This motivates our pre-optimized fixed-angle protocol rather than hardware-in-the-loop optimization.

---

## Barak et al. (2021) — "Classical Algorithms and Quantum Limitations for Maximum Cut on High-Girth Graphs"
**Citation:** arXiv:2106.05343
**Core Numerical Finding:** Classical local algorithm achieves AR ≥ 0.725 on high-girth 3-regular graphs — strictly better than the QAOA p=1 analytical bound of 0.6924 on those graph families.
**Relevance:** This is a critical paper we must acknowledge explicitly. Our 3-regular benchmark graphs include high-girth instances where classical algorithms outperform QAOA p=1; we do not claim quantum advantage and frame our GW comparison accordingly.

---

## Guerreschi & Matsuura (2019) — "QAOA for Max-Cut Requires Hundreds of Qubits for Quantum Speed-Up"
**Citation:** Scientific Reports 9, 6903 (2019). DOI: 10.1038/s41598-019-43176-9
**Core Numerical Finding:** Classical simulation can match QAOA performance on small instances; quantum speedup crossover point is estimated to require hundreds of qubits — far beyond the scale studied in most hardware experiments.
**Relevance:** This is the key paper that tempers optimistic QAOA claims. We cite it to frame our results honestly: our inability to demonstrate quantum advantage at n=6–12 is exactly what this paper predicts, not a failure of our experiment.

---

## Preskill (2018) — "Quantum Computing in the NISQ Era and Beyond"
**Citation:** Quantum 2, 79 (2018); arXiv:1801.00862. DOI: 10.22331/q-2018-08-06-79
**Core Numerical Finding:** Defined the NISQ regime as 50–1000 qubit devices with ~0.1–1% two-qubit gate errors; estimated useful circuits limited to ~1000 two-qubit gates before noise dominates.
**Relevance:** Provides the foundational vocabulary and framing for our entire paper. The 1000-gate budget estimate directly motivates why our p=3–5 circuits (which can exceed this budget for n≥10 after SWAP routing) are expected to fail on hardware.

---

## Blekos et al. (2024) — "A Review of QAOA: An Algorithmic and Practical Perspective"
**Citation:** arXiv:2310.09518
**Core Numerical Finding:** Comprehensive survey covering ~200 QAOA papers; identifies systematic noise characterization as an open problem.
**Relevance:** We cite this as the most current comprehensive review. Consulting it before finalizing related work ensures we have not missed important recent developments; its identification of noise characterization as open supports our contribution claim.

---

## Bharti et al. (2022) — "Noisy Intermediate-Scale Quantum Algorithms"
**Citation:** Reviews of Modern Physics 94, 015004 (2022). DOI: 10.1103/RevModPhys.94.015004
**Core Numerical Finding:** Comprehensive review of NISQ algorithms including VQE, QAOA, and quantum machine learning; catalogs known theoretical and practical limitations.
**Relevance:** Standard reference for the broader NISQ algorithmic landscape. We cite it alongside Preskill (2018) to establish the context that QAOA is one of the most promising NISQ candidates — motivating why systematic noise characterization of QAOA circuits is valuable.
