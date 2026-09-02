"""
Figure generation for QAOA benchmark paper.
Run after qaoa_benchmark.py has produced results/benchmark_results.json.

Usage: python plot_results.py
Figures saved to: ../figures/
"""

import os
import json
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
import networkx as nx

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_PATH = os.path.join(SCRIPT_DIR, "results", "benchmark_results.json")
FIGURES_DIR = os.path.join(SCRIPT_DIR, "..", "figures")
os.makedirs(FIGURES_DIR, exist_ok=True)

# Style
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 11,
    "axes.labelsize": 12,
    "axes.titlesize": 13,
    "legend.fontsize": 10,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "axes.grid": True,
    "grid.alpha": 0.3,
})

COLORS = {
    "noiseless": "#2166ac",
    "noisy": "#d6604d",
    "hardware": "#4dac26",
    "gw": "#762a83",
    "greedy": "#e08214",
    "random": "#999999",
}

N_VALUES = [6, 8, 10, 12]
P_VALUES = [1, 2, 3, 4, 5]


def load_results(path=RESULTS_PATH):
    if not os.path.exists(path):
        print(f"Results file not found: {path}")
        print("Run qaoa_benchmark.py first to generate data.")
        return None
    with open(path) as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    print(f"Loaded {len(df)} benchmark records.")
    return df


def ci95(series):
    """95% confidence interval half-width."""
    n = series.dropna().count()
    if n < 2:
        return 0.0
    return 1.96 * series.dropna().std() / np.sqrt(n)


def get_mean_ci(df, n, graph_type, p, col):
    subset = df[(df["n"] == n) & (df["graph_type"] == graph_type) & (df["p"] == p)][col].dropna()
    if len(subset) == 0:
        return np.nan, np.nan
    return subset.mean(), ci95(subset)


# ──────────────────────────────────────────────
# FIG 1: QAOA Circuit Diagram
# ──────────────────────────────────────────────

def fig1_circuit_diagram():
    """Draw p=1 QAOA circuit on a 4-node cycle graph."""
    from qiskit import QuantumCircuit
    import sys
    sys.path.insert(0, SCRIPT_DIR)
    from qaoa_benchmark import build_qaoa_circuit

    G = nx.cycle_graph(4)
    gamma = [np.pi / 4]
    beta = [np.pi / 8]

    qc = build_qaoa_circuit(G, 1, gamma, beta)
    qc.name = "QAOA p=1, n=4 (Cycle Graph)"

    try:
        fig = qc.draw("mpl", style="iqp", fold=-1)
        fig.suptitle("QAOA Circuit for MaxCut (p=1, n=4 cycle graph)", fontsize=13)
        out = os.path.join(FIGURES_DIR, "fig1_qaoa_circuit.png")
        fig.savefig(out, dpi=300, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved: {out}")
    except Exception as e:
        print(f"Circuit drawing failed ({e}), generating schematic instead.")
        fig, ax = plt.subplots(figsize=(10, 3))
        ax.text(0.5, 0.5, "QAOA Circuit: H → [RZZ(2γ) per edge] → [RX(2β) per qubit] → Measure",
                ha="center", va="center", fontsize=14,
                bbox=dict(boxstyle="round", fc="lightblue", ec="steelblue"))
        ax.set_title("QAOA p=1 Circuit Structure (n=4, cycle graph)", fontsize=13)
        ax.axis("off")
        out = os.path.join(FIGURES_DIR, "fig1_qaoa_circuit.png")
        fig.savefig(out, dpi=300, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved: {out}")


# ──────────────────────────────────────────────
# FIG 2: AR vs Circuit Depth p (main result)
# ──────────────────────────────────────────────

def fig2_ar_vs_depth(df, graph_type="3regular"):
    """4-panel plot: AR vs p for each n value, with noiseless/noisy/hardware."""
    fig, axes = plt.subplots(2, 2, figsize=(12, 9), sharey=False)
    axes = axes.flatten()

    for idx, n in enumerate(N_VALUES):
        ax = axes[idx]
        p_vals = P_VALUES

        nl_means, nl_cis = [], []
        nz_means, nz_cis = [], []
        hw_means, hw_cis = [], []

        for p in p_vals:
            m, c = get_mean_ci(df, n, graph_type, p, "noiseless_ar")
            nl_means.append(m); nl_cis.append(c)
            m, c = get_mean_ci(df, n, graph_type, p, "noisy_ar")
            nz_means.append(m); nz_cis.append(c)
            m, c = get_mean_ci(df, n, graph_type, p, "hardware_ar")
            hw_means.append(m); hw_cis.append(c)

        ax.errorbar(p_vals, nl_means, yerr=nl_cis, label="Noiseless (statevector)",
                    color=COLORS["noiseless"], marker="o", linewidth=2, capsize=4)

        if any(not np.isnan(v) for v in nz_means):
            ax.errorbar(p_vals, nz_means, yerr=nz_cis, label="Noisy (FakeSherbrooke)",
                        color=COLORS["noisy"], marker="s", linestyle="--", linewidth=2, capsize=4)

            # Mark divergence depth p*
            valid = [(p, nl, nz) for p, nl, nz in zip(p_vals, nl_means, nz_means)
                     if not np.isnan(nl) and not np.isnan(nz)]
            if valid:
                divs = [abs(nl - nz) for _, nl, nz in valid]
                p_star_candidates = [p for (p, _, _), d in zip(valid, divs) if d > 0.05]
                if p_star_candidates:
                    p_star = p_star_candidates[0]
                    ax.axvline(p_star, color="gray", linestyle=":", linewidth=1.5,
                               label=f"$p^*={p_star}$ (divergence)")

        if any(not np.isnan(v) for v in hw_means):
            ax.errorbar(p_vals, hw_means, yerr=hw_cis, label="IBM Hardware",
                        color=COLORS["hardware"], marker="^", linestyle="-.", linewidth=2, capsize=4)

        # Analytical p=1 reference for 3-regular
        if graph_type == "3regular":
            ax.axhline(0.6924, color="black", linestyle=":", linewidth=1, alpha=0.6,
                       label="Farhi et al. p=1 bound (0.6924)")

        ax.set_title(f"n = {n} qubits", fontweight="bold")
        ax.set_xlabel("Circuit depth p")
        ax.set_ylabel("Approximation ratio AR")
        ax.set_xticks(p_vals)
        ax.set_ylim(0.4, 1.05)
        ax.legend(fontsize=8, loc="lower right")

    fig.suptitle(f"QAOA Approximation Ratio vs. Circuit Depth\n"
                 f"(3-regular MaxCut, 30 instances per n, 95% CI shaded)",
                 fontsize=14, fontweight="bold")
    plt.tight_layout()
    out = os.path.join(FIGURES_DIR, "fig2_ar_vs_depth.png")
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}")


# ──────────────────────────────────────────────
# FIG 3: AR vs System Size n
# ──────────────────────────────────────────────

def fig3_scaling_ar_vs_n(df, graph_type="3regular"):
    """AR vs n at fixed p values, showing scaling degradation."""
    fig, ax = plt.subplots(figsize=(9, 6))

    p_plot = [1, 3, 5]
    linestyles_nl = ["-", "--", "-."]
    markers = ["o", "s", "^"]

    for i, p in enumerate(p_plot):
        nl_means, nl_cis, nz_means, nz_cis = [], [], [], []
        for n in N_VALUES:
            m, c = get_mean_ci(df, n, graph_type, p, "noiseless_ar")
            nl_means.append(m); nl_cis.append(c)
            m, c = get_mean_ci(df, n, graph_type, p, "noisy_ar")
            nz_means.append(m); nz_cis.append(c)

        ax.errorbar(N_VALUES, nl_means, yerr=nl_cis,
                    label=f"Noiseless p={p}",
                    color=COLORS["noiseless"], marker=markers[i],
                    linestyle=linestyles_nl[i], linewidth=2, capsize=4,
                    alpha=0.9)

        if any(not np.isnan(v) for v in nz_means):
            ax.errorbar(N_VALUES, nz_means, yerr=nz_cis,
                        label=f"Noisy (FakeSherbrooke) p={p}",
                        color=COLORS["noisy"], marker=markers[i],
                        linestyle=linestyles_nl[i], linewidth=2, capsize=4,
                        alpha=0.7, markerfacecolor="white")

    ax.set_xlabel("System size n (qubits)")
    ax.set_ylabel("Approximation ratio AR")
    ax.set_title("Scaling of QAOA Approximation Ratio with System Size\n"
                 "(3-regular MaxCut, mean ± 95% CI across 30 instances)", fontweight="bold")
    ax.set_xticks(N_VALUES)
    ax.set_ylim(0.4, 1.05)
    ax.legend(loc="lower left")
    plt.tight_layout()
    out = os.path.join(FIGURES_DIR, "fig3_scaling_ar_vs_n.png")
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}")


# ──────────────────────────────────────────────
# FIG 4: Noise Model vs Hardware Validation
# ──────────────────────────────────────────────

def fig4_fake_vs_hardware(df):
    """Scatter: noiseless AR vs noisy AR per instance, coloured by p."""
    hw_data = df[df["hardware_ar"].notna() & df["noisy_ar"].notna()]

    # Use noiseless vs noisy scatter (meaningful even without real hardware)
    plot_data = df[df["noisy_ar"].notna() & df["noiseless_ar"].notna() &
                   (df["graph_type"] == "3regular")].copy()

    if len(hw_data) > 0:
        # Real hardware data available — original scatter
        fig, ax = plt.subplots(figsize=(7, 7))
        palette = sns.color_palette("tab10", n_colors=5)
        for i, p in enumerate(sorted(hw_data["p"].unique())):
            subset = hw_data[hw_data["p"] == p]
            ax.scatter(subset["noisy_ar"], subset["hardware_ar"],
                       label=f"p={p}", alpha=0.8, s=70, color=palette[i], zorder=3)
        lims = [min(df["noisy_ar"].min(), df["hardware_ar"].min()) - 0.02,
                max(df["noisy_ar"].max(), df["hardware_ar"].max()) + 0.02]
        ax.plot(lims, lims, "k--", lw=1.5, label="y = x (perfect agreement)", zorder=2)
        mae = (hw_data["hardware_ar"] - hw_data["noisy_ar"]).abs().mean()
        ax.text(0.05, 0.92, f"MAE = {mae:.4f}", transform=ax.transAxes,
                fontsize=11, bbox=dict(boxstyle="round", fc="white", ec="gray"))
        ax.set_xlabel("Noisy Simulation AR", fontsize=13)
        ax.set_ylabel("Real IBM Hardware AR", fontsize=13)
        ax.set_title("Noise Model Fidelity: Simulation vs. IBM Hardware\n"
                     "(n∈{6,8}, p∈{1,2}, 4096 shots)", fontweight="bold")
        ax.legend(); ax.set_aspect("equal")
    else:
        # Show noiseless vs noisy scatter coloured by p — real data, no placeholder
        fig, ax = plt.subplots(figsize=(7, 7))
        palette = sns.color_palette("tab10", n_colors=5)
        p_vals = sorted(plot_data["p"].unique())
        for i, p in enumerate(p_vals):
            sub = plot_data[plot_data["p"] == p]
            ax.scatter(sub["noiseless_ar"], sub["noisy_ar"],
                       label=f"p={p}", alpha=0.55, s=30, color=palette[i], zorder=3)

        # Per-(n,p) means
        means = plot_data.groupby(["n", "p"])[["noiseless_ar", "noisy_ar"]].mean().reset_index()
        for i, p in enumerate(p_vals):
            m = means[means["p"] == p]
            ax.scatter(m["noiseless_ar"], m["noisy_ar"],
                       s=160, color=palette[i], edgecolors="black", linewidths=1.2,
                       marker="D", zorder=5)

        lo = min(plot_data["noiseless_ar"].min(), plot_data["noisy_ar"].min()) - 0.02
        hi = max(plot_data["noiseless_ar"].max(), plot_data["noisy_ar"].max()) + 0.01
        ax.plot([lo, hi], [lo, hi], "k--", lw=1.5, label="y = x (no noise)", zorder=2)

        mae = (plot_data["noiseless_ar"] - plot_data["noisy_ar"]).abs().mean()
        ax.text(0.05, 0.93, f"Mean |AR gap| = {mae:.3f}", transform=ax.transAxes,
                fontsize=11, bbox=dict(boxstyle="round", fc="white", ec="gray", alpha=0.9))

        ax.set_xlabel("Noiseless Simulation AR", fontsize=13)
        ax.set_ylabel("Noisy Simulation AR", fontsize=13)
        ax.set_title("Noise Impact: Noiseless vs. Noisy AR per Instance\n"
                     "(3-regular graphs, n∈{6,8,10,12}, p∈{1–5})", fontweight="bold")
        ax.legend(title="Depth p", fontsize=10)
        ax.set_aspect("equal")

    plt.tight_layout()
    out = os.path.join(FIGURES_DIR, "fig4_fake_vs_hardware.png")
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}")


# ──────────────────────────────────────────────
# FIG 5: All Baselines Comparison
# ──────────────────────────────────────────────

def fig5_baselines_comparison(df, n_target=10, graph_type="3regular"):
    """Compare all baselines at n=10: random, greedy, GW, noiseless QAOA, noisy QAOA."""
    fig, ax = plt.subplots(figsize=(10, 6))

    subset = df[(df["n"] == n_target) & (df["graph_type"] == graph_type)]

    p_vals = P_VALUES
    nl_means, nl_cis = [], []
    nz_means, nz_cis = [], []
    gw_mean = subset["gw_ar"].dropna().mean()
    greedy_mean = subset["greedy_ar"].dropna().mean()

    for p in p_vals:
        ps = subset[subset["p"] == p]
        m, c = ps["noiseless_ar"].mean(), ci95(ps["noiseless_ar"])
        nl_means.append(m); nl_cis.append(c)
        m, c = ps["noisy_ar"].dropna().mean() if ps["noisy_ar"].notna().any() else (np.nan, np.nan), \
               ci95(ps["noisy_ar"]) if ps["noisy_ar"].notna().any() else np.nan
        if isinstance(m, tuple):
            m, c = m
        nz_means.append(m); nz_cis.append(c)

    ax.axhline(0.5, color=COLORS["random"], linestyle=":", linewidth=2,
               label="Random cut (AR = 0.50)", alpha=0.8)
    ax.axhline(greedy_mean, color=COLORS["greedy"], linestyle="--", linewidth=2,
               label=f"Greedy (AR ≈ {greedy_mean:.3f})", alpha=0.8)
    if not np.isnan(gw_mean):
        ax.axhline(gw_mean, color=COLORS["gw"], linestyle="-.", linewidth=2,
                   label=f"Goemans-Williamson (AR ≈ {gw_mean:.3f})", alpha=0.8)
    ax.axhline(0.8786, color=COLORS["gw"], linestyle=":", linewidth=1.5,
               label="GW theoretical bound (0.8786)", alpha=0.5)

    ax.errorbar(p_vals, nl_means, yerr=nl_cis, label="QAOA Noiseless",
                color=COLORS["noiseless"], marker="o", linewidth=2.5, capsize=4, zorder=5)

    valid_nz = [(p, m, c) for p, m, c in zip(p_vals, nz_means, nz_cis) if not np.isnan(m)]
    if valid_nz:
        pv, mv, cv = zip(*valid_nz)
        ax.errorbar(pv, mv, yerr=cv, label="QAOA Noisy (FakeSherbrooke)",
                    color=COLORS["noisy"], marker="s", linestyle="--", linewidth=2.5, capsize=4, zorder=5)

    ax.set_xlabel("Circuit depth p")
    ax.set_ylabel("Approximation ratio AR")
    ax.set_title(f"QAOA vs. Classical Baselines for MaxCut\n"
                 f"(n={n_target}, 3-regular graphs, 30 instances, 95% CI)", fontweight="bold")
    ax.set_xticks(p_vals)
    ax.set_ylim(0.4, 1.05)
    ax.legend(loc="upper left", fontsize=9)
    plt.tight_layout()
    out = os.path.join(FIGURES_DIR, "fig5_baselines_comparison.png")
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}")


# ──────────────────────────────────────────────
# FIG 6: Divergence Heatmap (p × n)
# ──────────────────────────────────────────────

def fig6_divergence_heatmap(df, graph_type="3regular"):
    """Side-by-side heatmaps: noiseless AR and noisy AR across (p, n) grid."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    def build_matrix(col):
        mat = np.full((len(N_VALUES), len(P_VALUES)), np.nan)
        for i, n in enumerate(N_VALUES):
            for j, p in enumerate(P_VALUES):
                m, _ = get_mean_ci(df, n, graph_type, p, col)
                mat[i, j] = m
        return mat

    nl_mat = build_matrix("noiseless_ar")
    nz_mat = build_matrix("noisy_ar")

    vmin, vmax = 0.5, 1.0
    cmap = "RdYlGn"

    for ax, mat, title in [
        (ax1, nl_mat, "Noiseless (statevector)"),
        (ax2, nz_mat, "Noisy (FakeSherbrooke)"),
    ]:
        im = ax.imshow(mat, cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
        ax.set_xticks(range(len(P_VALUES)))
        ax.set_xticklabels([f"p={p}" for p in P_VALUES])
        ax.set_yticks(range(len(N_VALUES)))
        ax.set_yticklabels([f"n={n}" for n in N_VALUES])
        ax.set_xlabel("Circuit depth p")
        ax.set_ylabel("System size n (qubits)")
        ax.set_title(title, fontweight="bold")
        plt.colorbar(im, ax=ax, label="Approximation Ratio AR", fraction=0.046, pad=0.04)

        for i in range(len(N_VALUES)):
            for j in range(len(P_VALUES)):
                val = mat[i, j]
                if not np.isnan(val):
                    ax.text(j, i, f"{val:.3f}", ha="center", va="center",
                            fontsize=9, fontweight="bold",
                            color="white" if val < 0.65 else "black")

    fig.suptitle("QAOA Approximation Ratio Heatmap: Noiseless vs. Noisy\n"
                 "(3-regular MaxCut, mean over 30 instances)", fontsize=14, fontweight="bold")
    plt.tight_layout()
    out = os.path.join(FIGURES_DIR, "fig6_divergence_heatmap.png")
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}")


# ──────────────────────────────────────────────
# DIVERGENCE DEPTH ANALYSIS
# ──────────────────────────────────────────────

def compute_divergence_depth(df, graph_type="3regular", delta=0.05):
    """
    For each n: find p* where noisy AR first drops more than delta below noiseless AR.
    Also find p_peak: the p at which noisy AR is maximized.
    Returns a summary DataFrame.
    """
    rows = []
    for n in N_VALUES:
        nl_list, nz_list = [], []
        for p in P_VALUES:
            m_nl, _ = get_mean_ci(df, n, graph_type, p, "noiseless_ar")
            m_nz, _ = get_mean_ci(df, n, graph_type, p, "noisy_ar")
            nl_list.append(m_nl)
            nz_list.append(m_nz)

        p_peak = None
        p_star = None
        valid_nz = [(p, nz) for p, nz in zip(P_VALUES, nz_list) if not np.isnan(nz)]
        valid_pair = [(p, nl, nz) for p, nl, nz in zip(P_VALUES, nl_list, nz_list)
                      if not np.isnan(nl) and not np.isnan(nz)]

        if valid_nz:
            p_peak = max(valid_nz, key=lambda x: x[1])[0]
        if valid_pair:
            for p, nl, nz in valid_pair:
                if nl - nz > delta:
                    p_star = p
                    break

        rows.append({
            "n": n,
            "graph_type": graph_type,
            "p_peak_noisy": p_peak,
            "p_star_divergence": p_star,
            "noiseless_ar_p1": nl_list[0] if nl_list else np.nan,
            "noisy_ar_p1": nz_list[0] if nz_list else np.nan,
        })

    summary = pd.DataFrame(rows)
    print("\n" + "=" * 50)
    print(f"DIVERGENCE DEPTH ANALYSIS (δ = {delta})")
    print("=" * 50)
    print(summary.to_string(index=False))
    return summary


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────

if __name__ == "__main__":
    df = load_results()
    if df is None:
        print("No data to plot. Run qaoa_benchmark.py first.")
        exit(1)

    print("Generating figures...")
    fig1_circuit_diagram()
    fig2_ar_vs_depth(df)
    fig3_scaling_ar_vs_n(df)
    fig4_fake_vs_hardware(df)
    fig5_baselines_comparison(df)
    fig6_divergence_heatmap(df)
    compute_divergence_depth(df)

    print(f"\nAll figures saved to {FIGURES_DIR}/")
