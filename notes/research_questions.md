# Research Questions

## Working Question
How does QAOA performance scale with circuit depth (p) and problem size for 
combinatorial optimization problems (MaxCut, TSP) on near-term noisy hardware 
versus ideal simulation?

## Sub-questions
1. At what circuit depth p does QAOA begin to outperform classical approximation algorithms?
2. How does hardware noise degrade QAOA performance relative to noiseless simulation?
3. Does performance vary significantly across problem instances of the same size?

## Hypothesis
QAOA shows measurable advantage over random classical baselines at low circuit depths 
for small MaxCut instances, but noise on real hardware erodes this advantage for p > 3.

## Potential Contributions
- Systematic benchmark across multiple p values and problem sizes
- Comparison of noise models vs real hardware results
- Analysis of barren plateau effect on optimization landscape

## To Discuss With Mentor
- Is this question too broad / too narrow?
- Which combinatorial problem is most tractable for this scope?
- What hardware access do we have (IBM Quantum, IonQ, etc.)?
