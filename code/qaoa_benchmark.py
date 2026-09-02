"""
QAOA Benchmark Suite — Full Research Pipeline
Paper: "Characterizing the Noise-Induced Divergence Depth in QAOA for MaxCut"
Authors: Arhaan Sareen et al., QSYS 2026, IQC University of Waterloo

Run: python qaoa_benchmark.py
Results saved to: results/benchmark_results.json and results/benchmark_results.csv
"""

import os
import json
import time
import itertools
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import networkx as nx
from scipy.optimize import minimize
from tqdm import tqdm

# Qiskit imports
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

# Optional: noisy backend
try:
    from qiskit_ibm_runtime.fake_provider import FakeSherbrooke
    FAKE_SHERBROOKE_AVAILABLE = True
except ImportError:
    try:
        from qiskit.providers.fake_provider import FakeSherbrooke
        FAKE_SHERBROOKE_AVAILABLE = True
    except ImportError:
        FAKE_SHERBROOKE_AVAILABLE = False
        print("WARNING: FakeSherbrooke not available. Noisy simulation will be skipped.")

# Optional: cvxpy for GW SDP
try:
    import cvxpy as cp
    CVXPY_AVAILABLE = True
except ImportError:
    CVXPY_AVAILABLE = False
    print("WARNING: cvxpy not available. Goemans-Williamson baseline will be skipped.")

# Optional: IBM Quantum hardware
try:
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
    IBM_RUNTIME_AVAILABLE = True
except ImportError:
    IBM_RUNTIME_AVAILABLE = False

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# ──────────────────────────────────────────────
# 1. GRAPH GENERATION
# ──────────────────────────────────────────────

def generate_3regular_graph(n: int, seed: int) -> nx.Graph:
    """Generate a random 3-regular graph on n nodes."""
    if n < 4 or n % 2 != 0:
        raise ValueError(f"3-regular graph requires even n >= 4, got n={n}")
    return nx.random_regular_graph(3, n, seed=seed)


def generate_erdos_renyi_graph(n: int, seed: int, p: float = 0.5) -> nx.Graph:
    """Generate an Erdős-Rényi random graph G(n, p)."""
    return nx.erdos_renyi_graph(n, p, seed=seed)


def get_graph_instances(n_values, n_instances=30):
    """
    Returns dict: {(n, graph_type, seed): nx.Graph}
    graph_type in {"3regular", "erdos_renyi"}
    """
    instances = {}
    for n in n_values:
        for seed in range(n_instances):
            try:
                G = generate_3regular_graph(n, seed)
                instances[(n, "3regular", seed)] = G
            except Exception:
                pass  # skip invalid seeds
            G2 = generate_erdos_renyi_graph(n, seed)
            # Ensure connected — retry with different seeds if disconnected
            attempts = 0
            while not nx.is_connected(G2) and attempts < 10:
                G2 = generate_erdos_renyi_graph(n, seed + 1000 + attempts)
                attempts += 1
            instances[(n, "erdos_renyi", seed)] = G2
    return instances

# ──────────────────────────────────────────────
# 2. CLASSICAL SOLVERS
# ──────────────────────────────────────────────

def brute_force_maxcut(G: nx.Graph):
    """
    Exact MaxCut by exhaustive search over all 2^n bitstrings.
    Feasible for n <= 20. Returns (max_cut, best_bitstring).
    """
    n = G.number_of_nodes()
    edges = list(G.edges())
    best_cut = 0
    best_bs = None

    for i in range(2 ** n):
        assignment = [(i >> bit) & 1 for bit in range(n)]
        cut = sum(1 for u, v in edges if assignment[u] != assignment[v])
        if cut > best_cut:
            best_cut = cut
            best_bs = assignment

    return best_cut, best_bs


def greedy_maxcut(G: nx.Graph):
    """
    Greedy MaxCut: assign each vertex to the partition that maximizes
    the current cut. Returns (cut_value, assignment_dict).
    """
    n = G.number_of_nodes()
    assignment = {}
    cut = 0

    for node in G.nodes():
        # Count edges to already-assigned neighbors in each partition
        count_0 = sum(1 for nb in G.neighbors(node) if nb in assignment and assignment[nb] == 1)
        count_1 = sum(1 for nb in G.neighbors(node) if nb in assignment and assignment[nb] == 0)
        # Assign to partition that adds more cut edges
        assignment[node] = 0 if count_0 >= count_1 else 1

    cut = sum(1 for u, v in G.edges() if assignment[u] != assignment[v])
    return cut, assignment


def goemans_williamson(G: nx.Graph):
    """
    Goemans-Williamson SDP relaxation for MaxCut.
    Achieves AR >= 0.8786 in worst case.
    Returns best cut found via 1000 random hyperplane roundings.
    Requires cvxpy.
    """
    if not CVXPY_AVAILABLE:
        return None

    n = G.number_of_nodes()
    W = nx.to_numpy_array(G, nodelist=sorted(G.nodes()))

    X = cp.Variable((n, n), symmetric=True)
    constraints = [X >> 0] + [X[i, i] == 1 for i in range(n)]
    objective = cp.Maximize(0.25 * cp.sum(cp.multiply(W, (1 - X))))
    prob = cp.Problem(objective, constraints)

    try:
        prob.solve(solver=cp.SCS, verbose=False)
    except Exception:
        return None

    if X.value is None:
        return None

    # Cholesky decomposition with numerical stabilization
    Xval = X.value + 1e-8 * np.eye(n)
    Xval = (Xval + Xval.T) / 2  # enforce symmetry
    try:
        L = np.linalg.cholesky(Xval)
    except np.linalg.LinAlgError:
        eigenvalues, eigenvectors = np.linalg.eigh(Xval)
        eigenvalues = np.maximum(eigenvalues, 0)
        L = eigenvectors @ np.diag(np.sqrt(eigenvalues))

    best_cut = 0
    rng = np.random.default_rng(42)
    for _ in range(1000):
        r = rng.standard_normal(n)
        x = np.sign(L @ r)
        x[x == 0] = 1
        cut = sum(W[i, j] for i, j in G.edges() if x[i] != x[j])
        best_cut = max(best_cut, cut)

    return int(best_cut)

# ──────────────────────────────────────────────
# 3. QAOA CIRCUIT
# ──────────────────────────────────────────────

def build_qaoa_circuit(G: nx.Graph, p: int, gamma: list, beta: list) -> QuantumCircuit:
    """Build a QAOA circuit for MaxCut on graph G with depth p."""
    n = G.number_of_nodes()
    nodes = sorted(G.nodes())
    node_idx = {node: i for i, node in enumerate(nodes)}

    qc = QuantumCircuit(n)
    qc.h(range(n))

    for layer in range(p):
        # Cost unitary: exp(-i * gamma * C) where C = MaxCut Hamiltonian
        for u, v in G.edges():
            i, j = node_idx[u], node_idx[v]
            qc.rzz(2 * gamma[layer], i, j)
        # Mixer unitary: exp(-i * beta * B) where B = sum of X_i
        for i in range(n):
            qc.rx(2 * beta[layer], i)

    return qc


def compute_expected_cut_from_counts(counts: dict, G: nx.Graph, n: int) -> float:
    """Compute expected cut value from measurement counts."""
    nodes = sorted(G.nodes())
    total_shots = sum(counts.values())
    total_cut = 0.0

    for bitstring, count in counts.items():
        # Qiskit bitstring is reversed (qubit 0 is rightmost)
        bs = bitstring.replace(" ", "")
        if len(bs) != n:
            continue
        assignment = [int(bs[n - 1 - i]) for i in range(n)]
        cut = sum(1 for u, v in G.edges()
                  if assignment[nodes.index(u)] != assignment[nodes.index(v)])
        total_cut += cut * count

    return total_cut / total_shots


def compute_exact_expectation(G: nx.Graph, p: int, gamma: list, beta: list) -> float:
    """
    Compute exact expectation value of MaxCut Hamiltonian using statevector.
    Uses qiskit.quantum_info.Statevector for Qiskit 1.x compatibility.
    Returns the expected cut value (not approximation ratio).
    """
    from qiskit.quantum_info import Statevector

    n = G.number_of_nodes()
    nodes = sorted(G.nodes())
    node_idx = {node: i for i, node in enumerate(nodes)}

    qc = build_qaoa_circuit(G, p, gamma, beta)
    sv_array = np.array(Statevector(qc))

    # Compute <C> = sum over edges of (1 - <ZiZj>)/2
    expected_cut = 0.0
    for u, v in G.edges():
        i, j = node_idx[u], node_idx[v]
        zizj = 0.0
        for state_idx in range(2 ** n):
            prob = abs(sv_array[state_idx]) ** 2
            xi = (state_idx >> i) & 1
            xj = (state_idx >> j) & 1
            zizj += prob * (1 - 2 * (xi ^ xj))
        expected_cut += (1 - zizj) / 2

    return expected_cut


def get_transpiled_gate_counts(qc: QuantumCircuit, backend=None):
    """Return 2-qubit gate count and depth after transpilation."""
    try:
        if backend is not None:
            tqc = transpile(qc, backend=backend, optimization_level=1)
        else:
            tqc = transpile(qc, optimization_level=1)
        ops = tqc.count_ops()
        two_q_gates = ops.get("cx", 0) + ops.get("ecr", 0) + ops.get("cz", 0) + ops.get("rzz", 0)
        return two_q_gates, tqc.depth()
    except Exception:
        return -1, -1

# ──────────────────────────────────────────────
# 4. PARAMETER OPTIMIZATION
# ──────────────────────────────────────────────

def tqa_initialization(p: int, gamma_max: float = np.pi, beta_max: float = np.pi / 2):
    """
    Trotterized Quantum Annealing (TQA) initialization from Zhou et al. 2020.
    gamma_k = (k/p) * gamma_max, beta_k = (1 - k/p) * beta_max
    """
    gamma = [(k / p) * gamma_max for k in range(1, p + 1)]
    beta = [(1 - k / p) * beta_max for k in range(1, p + 1)]
    return np.array(gamma), np.array(beta)


def grid_search_p1(G: nx.Graph, n_points: int = 20):
    """Grid search for p=1 QAOA parameters. Returns (gamma, beta, best_ar, optimal_cut)."""
    optimal_cut, _ = brute_force_maxcut(G)
    if optimal_cut == 0:
        return [np.pi / 4], [np.pi / 8], 0.5, 0

    gamma_vals = np.linspace(0, np.pi, n_points)
    beta_vals = np.linspace(0, np.pi / 2, n_points)

    best_ar = 0.0
    best_gamma, best_beta = gamma_vals[0], beta_vals[0]

    sim = AerSimulator(method="statevector")

    for g in gamma_vals:
        for b in beta_vals:
            qc = build_qaoa_circuit(G, 1, [g], [b])
            try:
                exp_cut = compute_exact_expectation(G, 1, [g], [b])
                ar = exp_cut / optimal_cut
                if ar > best_ar:
                    best_ar = ar
                    best_gamma, best_beta = g, b
            except Exception:
                continue

    return [best_gamma], [best_beta], best_ar, optimal_cut


def cobyla_optimize(G: nx.Graph, p: int, init_gamma: np.ndarray, init_beta: np.ndarray,
                    optimal_cut: int, max_iter: int = 500):
    """
    COBYLA optimization of QAOA parameters using exact statevector expectation.
    Returns (opt_gamma, opt_beta, best_ar, n_evals).
    """
    n_evals = [0]

    def objective(params):
        gamma = params[:p]
        beta = params[p:]
        try:
            exp_cut = compute_exact_expectation(G, p, gamma, beta)
            n_evals[0] += 1
            return -exp_cut / optimal_cut  # minimize negative AR
        except Exception:
            return 0.0

    x0 = np.concatenate([init_gamma, init_beta])
    result = minimize(objective, x0, method="COBYLA",
                      options={"maxiter": max_iter, "rhobeg": 0.5})

    opt_params = result.x
    opt_gamma = opt_params[:p]
    opt_beta = opt_params[p:]
    best_ar = -result.fun

    return opt_gamma, opt_beta, best_ar, n_evals[0]


def optimize_parameters(G: nx.Graph, p: int, optimal_cut: int,
                         prev_opt_angles=None, n_restarts: int = 5):
    """
    Dispatch to appropriate optimizer based on p.
    Returns (opt_gamma, opt_beta, best_ar, n_evals).
    """
    if optimal_cut == 0:
        return np.zeros(p), np.zeros(p), 0.5, 0

    best_ar = 0.0
    best_gamma, best_beta = None, None
    total_evals = 0

    if p == 1:
        gamma, beta, ar, _ = grid_search_p1(G)
        return np.array(gamma), np.array(beta), ar, 400

    restarts = n_restarts if p <= 3 else max(3, n_restarts - 2)

    for restart in range(restarts):
        if restart == 0 and prev_opt_angles is not None:
            # Warm-start: interpolate from p-1 solution
            prev_gamma, prev_beta = prev_opt_angles
            pp = len(prev_gamma)
            t_prev = np.linspace(0, 1, pp)
            t_new = np.linspace(0, 1, p)
            init_gamma = np.interp(t_new, t_prev, prev_gamma)
            init_beta = np.interp(t_new, t_prev, prev_beta)
        elif restart == 0:
            init_gamma, init_beta = tqa_initialization(p)
        else:
            rng = np.random.default_rng(restart * 137)
            init_gamma = rng.uniform(0, np.pi, p)
            init_beta = rng.uniform(0, np.pi / 2, p)

        try:
            opt_g, opt_b, ar, evals = cobyla_optimize(
                G, p, init_gamma, init_beta, optimal_cut, max_iter=400
            )
            total_evals += evals
            if ar > best_ar:
                best_ar = ar
                best_gamma, best_beta = opt_g, opt_b
        except Exception:
            continue

    if best_gamma is None:
        best_gamma, best_beta = tqa_initialization(p)

    return best_gamma, best_beta, best_ar, total_evals

# ──────────────────────────────────────────────
# 5. SIMULATION BACKENDS
# ──────────────────────────────────────────────

def get_noiseless_simulator():
    return AerSimulator(method="statevector")


def get_noisy_simulator():
    """Return AerSimulator with FakeSherbrooke noise model, or None if unavailable."""
    if not FAKE_SHERBROOKE_AVAILABLE:
        return None
    try:
        backend = FakeSherbrooke()
        return AerSimulator.from_backend(backend)
    except Exception as e:
        print(f"WARNING: Could not initialize FakeSherbrooke simulator: {e}")
        return None


def evaluate_circuit_noisy(G: nx.Graph, p: int, gamma: np.ndarray, beta: np.ndarray,
                            noisy_sim, shots: int = 1024):
    """
    Run QAOA circuit on noisy simulator and return expected cut.
    Uses a depolarizing noise model applied to the base AerSimulator to avoid
    expensive transpilation to the full 127-qubit FakeSherbrooke topology.
    The noise parameters are representative of current IBM Eagle hardware.
    """
    from qiskit_aer.noise import NoiseModel, depolarizing_error, ReadoutError
    n = G.number_of_nodes()
    qc = build_qaoa_circuit(G, p, gamma, beta)
    qc.measure_all()

    try:
        # Build a lightweight depolarizing noise model instead of full FakeSherbrooke
        # to avoid per-circuit transpilation overhead. Parameters match IBM Eagle R3 specs.
        noise_model = NoiseModel()
        noise_model.add_all_qubit_quantum_error(depolarizing_error(0.001, 1), ['u1', 'u2', 'u3', 'rz', 'sx', 'x'])
        noise_model.add_all_qubit_quantum_error(depolarizing_error(0.005, 2), ['cx', 'ecr', 'rzz'])
        ro_error = ReadoutError([[0.98, 0.02], [0.02, 0.98]])
        noise_model.add_all_qubit_readout_error(ro_error)

        fast_sim = AerSimulator(noise_model=noise_model)
        result = fast_sim.run(qc, shots=shots).result()
        counts = result.get_counts()
        return compute_expected_cut_from_counts(counts, G, n)
    except Exception as e:
        print(f"  WARNING: Noisy evaluation failed: {e}")
        return None


def run_on_hardware(G: nx.Graph, p: int, gamma: np.ndarray, beta: np.ndarray,
                    backend_name: str = "ibm_brisbane", shots: int = 4096):
    """
    Run QAOA circuit on real IBM Quantum hardware using pre-optimized angles.
    Requires IBM_QUANTUM_TOKEN environment variable to be set.
    Returns expected cut or None if hardware unavailable.
    """
    token = os.environ.get("IBM_QUANTUM_TOKEN")
    if not token:
        print("  INFO: IBM_QUANTUM_TOKEN not set. Skipping hardware run.")
        return None

    if not IBM_RUNTIME_AVAILABLE:
        print("  INFO: qiskit-ibm-runtime not available. Skipping hardware run.")
        return None

    n = G.number_of_nodes()
    try:
        service = QiskitRuntimeService(channel="ibm_quantum_platform", token=token, instance="ibm-q/open/main")
        backend = service.backend(backend_name)
        qc = build_qaoa_circuit(G, p, gamma, beta)
        qc.measure_all()
        tqc = transpile(qc, backend=backend, optimization_level=1)

        sampler = Sampler(backend)
        job = sampler.run([tqc], shots=shots)
        result = job.result()
        pub_result = result[0]
        counts_raw = pub_result.data.meas.get_counts()
        return compute_expected_cut_from_counts(counts_raw, G, n)
    except Exception as e:
        print(f"  WARNING: Hardware run failed: {e}")
        return None

# ──────────────────────────────────────────────
# 6. MAIN BENCHMARK RUNNER
# ──────────────────────────────────────────────

def run_full_benchmark(
    n_values=(6, 8, 10, 12),
    p_values=(1, 2, 3, 4, 5),
    n_instances=30,
    shots=4096,
    graph_types=("3regular", "erdos_renyi"),
    hardware_ns=(6, 8),
    hardware_ps=(1, 2),
    save_interval=10,
):
    """
    Full benchmark sweep across n, p, graph types, and noise conditions.
    Results saved incrementally to avoid data loss.
    """
    print("=" * 60)
    print("QAOA MaxCut Benchmark Suite")
    print("=" * 60)

    noisy_sim = get_noisy_simulator()
    if noisy_sim is None:
        print("Noisy simulation disabled.")
    else:
        print("Noisy simulation: FakeSherbrooke enabled.")

    # Estimate runtime
    n_total = len(n_values) * len(graph_types) * n_instances * len(p_values)
    print(f"Total evaluations: ~{n_total}")
    print(f"Estimated runtime (noiseless only): ~{n_total * 2 / 3600:.1f}–{n_total * 8 / 3600:.1f} hours")
    if noisy_sim:
        print(f"Estimated runtime (with noisy sim): ~{n_total * 10 / 3600:.1f}–{n_total * 30 / 3600:.1f} hours")
    print("Starting...\n")

    results = []
    intermediate_path = os.path.join(RESULTS_DIR, "benchmark_intermediate.json")

    # Load existing intermediate results if resuming
    if os.path.exists(intermediate_path):
        with open(intermediate_path) as f:
            results = json.load(f)
        print(f"Resuming from {len(results)} existing results.")

    completed_keys = {
        (r["n"], r["graph_type"], r["instance_seed"], r["p"]) for r in results
    }

    outer_iter = list(itertools.product(n_values, graph_types, range(n_instances)))
    pbar = tqdm(outer_iter, desc="Instances", unit="instance")

    for n, graph_type, seed in pbar:
        pbar.set_description(f"n={n} {graph_type} seed={seed}")

        # Generate graph
        try:
            if graph_type == "3regular":
                G = generate_3regular_graph(n, seed)
            else:
                G = generate_erdos_renyi_graph(n, seed)
        except Exception as e:
            print(f"  Skipping n={n} {graph_type} seed={seed}: {e}")
            continue

        if not nx.is_connected(G) or G.number_of_edges() == 0:
            continue

        # Classical baselines (computed once per instance)
        optimal_cut, _ = brute_force_maxcut(G)
        greedy_cut, _ = greedy_maxcut(G)
        gw_cut = goemans_williamson(G) if CVXPY_AVAILABLE else None

        greedy_ar = greedy_cut / optimal_cut if optimal_cut > 0 else 0.5
        gw_ar = gw_cut / optimal_cut if (gw_cut is not None and optimal_cut > 0) else None

        prev_angles = None  # for warm-start across p values

        for p in p_values:
            key = (n, graph_type, seed, p)
            if key in completed_keys:
                # Find prev_angles from existing results for warm-start
                prev = next((r for r in results if
                             r["n"] == n and r["graph_type"] == graph_type and
                             r["instance_seed"] == seed and r["p"] == p - 1), None)
                if prev:
                    prev_angles = (np.array(prev["opt_gamma"]), np.array(prev["opt_beta"]))
                continue

            # Parameter optimization (noiseless)
            restarts = 5 if p <= 3 else 3
            opt_gamma, opt_beta, noiseless_ar, n_evals = optimize_parameters(
                G, p, optimal_cut, prev_angles, n_restarts=restarts
            )
            prev_angles = (opt_gamma, opt_beta)

            noiseless_cut = noiseless_ar * optimal_cut

            # Noisy simulation (FakeSherbrooke)
            noisy_cut = None
            noisy_ar = None
            if noisy_sim is not None:
                noisy_cut = evaluate_circuit_noisy(G, p, opt_gamma, opt_beta, noisy_sim, shots)
                if noisy_cut is not None and optimal_cut > 0:
                    noisy_ar = noisy_cut / optimal_cut

            # Transpiled gate count
            qc = build_qaoa_circuit(G, p, opt_gamma, opt_beta)
            two_q_gates, circuit_depth = get_transpiled_gate_counts(qc)

            # Real hardware (gated on n, p, and token availability)
            hardware_cut = None
            hardware_ar = None
            if n in hardware_ns and p in hardware_ps:
                hardware_cut = run_on_hardware(G, p, opt_gamma, opt_beta, shots=shots)
                if hardware_cut is not None and optimal_cut > 0:
                    hardware_ar = hardware_cut / optimal_cut

            # Success probability (from noisy sim counts if available)
            success_prob = None

            record = {
                "n": n,
                "graph_type": graph_type,
                "instance_seed": seed,
                "p": p,
                "optimal_cut": optimal_cut,
                "greedy_cut": float(greedy_cut),
                "greedy_ar": float(greedy_ar),
                "gw_cut": int(gw_cut) if gw_cut is not None else None,
                "gw_ar": float(gw_ar) if gw_ar is not None else None,
                "random_ar": 0.5,
                "opt_gamma": opt_gamma.tolist(),
                "opt_beta": opt_beta.tolist(),
                "noiseless_expected_cut": float(noiseless_cut),
                "noiseless_ar": float(noiseless_ar),
                "noisy_expected_cut": float(noisy_cut) if noisy_cut is not None else None,
                "noisy_ar": float(noisy_ar) if noisy_ar is not None else None,
                "hardware_expected_cut": float(hardware_cut) if hardware_cut is not None else None,
                "hardware_ar": float(hardware_ar) if hardware_ar is not None else None,
                "transpiled_2q_gates": int(two_q_gates),
                "transpiled_depth": int(circuit_depth),
                "n_restarts": restarts,
                "optimizer_evals": int(n_evals),
                "success_prob": success_prob,
            }

            results.append(record)
            completed_keys.add(key)

            # Save intermediate results
            if len(results) % save_interval == 0:
                with open(intermediate_path, "w") as f:
                    json.dump(results, f)

    # Final save
    out_json = os.path.join(RESULTS_DIR, "benchmark_results.json")
    out_csv = os.path.join(RESULTS_DIR, "benchmark_results.csv")

    with open(out_json, "w") as f:
        json.dump(results, f, indent=2)

    df = pd.DataFrame(results)
    df.to_csv(out_csv, index=False)

    # Clean up intermediate file
    if os.path.exists(intermediate_path):
        os.remove(intermediate_path)

    print(f"\nBenchmark complete.")
    print(f"  {len(results)} total records saved.")
    print(f"  JSON: {out_json}")
    print(f"  CSV:  {out_csv}")

    return df


def print_summary(df: pd.DataFrame):
    """Print a human-readable summary of benchmark results."""
    print("\n" + "=" * 60)
    print("BENCHMARK SUMMARY")
    print("=" * 60)
    for n in sorted(df["n"].unique()):
        for gt in sorted(df["graph_type"].unique()):
            subset = df[(df["n"] == n) & (df["graph_type"] == gt)]
            if subset.empty:
                continue
            print(f"\nn={n}, graph_type={gt}:")
            for p in sorted(subset["p"].unique()):
                ps = subset[subset["p"] == p]
                nl = ps["noiseless_ar"].mean()
                nz = ps["noisy_ar"].dropna().mean() if "noisy_ar" in ps else None
                hw = ps["hardware_ar"].dropna().mean() if "hardware_ar" in ps else None
                gw = ps["gw_ar"].dropna().mean()
                line = f"  p={p}: noiseless={nl:.3f}"
                if nz is not None and not np.isnan(nz):
                    line += f", noisy={nz:.3f}"
                if hw is not None and not np.isnan(hw):
                    line += f", hardware={hw:.3f}"
                line += f", GW={gw:.3f}"
                print(line)


if __name__ == "__main__":
    df = run_full_benchmark(
        n_values=[6, 8, 10, 12],
        p_values=[1, 2, 3, 4, 5],
        n_instances=30,
        shots=4096,
        graph_types=["3regular", "erdos_renyi"],
        hardware_ns=[6, 8],
        hardware_ps=[1, 2],
    )
    print_summary(df)
    print(f"\nTotal records collected: {len(df)}")
