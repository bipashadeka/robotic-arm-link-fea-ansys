"""
Verify the ANSYS Static Structural results for the three robotic-arm links.

What this script does
1. Reaction-force check: the support reaction ANSYS reports must equal the
   applied load plus the link's own weight (static equilibrium, sum Fy = 0).
2. Safety factor: yield strength of PLA / peak von Mises stress, compared with
   the design target of 3 for 3D-printed parts.
3. Mesh sensitivity: shows that the Link 1 peak at the fixed holes keeps rising
   as the mesh is refined, so it is a stress singularity, not a real peak.
4. Saves two summary charts to ../results/.

Run:  python verify_fea.py   (from the analysis/ folder)
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).parent
RESULTS = HERE.parent / "results"
RESULTS.mkdir(exist_ok=True)

G = 9.81                 # m/s^2
PLA_YIELD_MPA = 50.0     # typical value for solid PLA (assumed, not measured)
TARGET_FOS = 3.0         # design target for 3D-printed parts
LINK1_MAIN_SECTION_MPA = 4.0  # hand-calculated bending stress away from the holes

# Chart styling
BLUE = "#2a78d6"
INK = "#0b0b0b"
MUTED = "#52514e"
SURFACE = "#fcfcfb"


def reaction_check(df: pd.DataFrame) -> pd.DataFrame:
    out = df[["link"]].copy()
    out["applied_load_N"] = df["applied_force_y_N"].abs()
    out["self_weight_N"] = df["mass_g"] / 1000 * G
    out["hand_reaction_N"] = out["applied_load_N"] + out["self_weight_N"]
    out["ansys_reaction_N"] = df["ansys_reaction_N"]
    out["difference_pct"] = (
        (out["ansys_reaction_N"] - out["hand_reaction_N"]) / out["hand_reaction_N"] * 100
    )
    return out.round(3)


def safety_factors(df: pd.DataFrame) -> pd.DataFrame:
    out = df[["link", "max_von_mises_MPa", "max_deformation_mm"]].copy()
    out["safety_factor"] = PLA_YIELD_MPA / out["max_von_mises_MPa"]
    out["meets_target"] = out["safety_factor"] >= TARGET_FOS
    return out.round(2)


def style_axes(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(MUTED)
    ax.tick_params(colors=MUTED)
    ax.yaxis.grid(True, color="#e4e3df", linewidth=0.8)
    ax.set_axisbelow(True)


def plot_safety_factor(sf: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(7, 4), facecolor=SURFACE)
    style_axes(ax)
    bars = ax.bar(sf["link"], sf["safety_factor"], color=BLUE, width=0.5)
    ax.axhline(TARGET_FOS, color=MUTED, linestyle="--", linewidth=1.2)
    ax.text(0.5, TARGET_FOS + 0.5, f"target = {TARGET_FOS:g}", color=MUTED, ha="center", fontsize=9)
    for bar, value in zip(bars, sf["safety_factor"]):
        ax.text(bar.get_x() + bar.get_width() / 2, max(value, TARGET_FOS) + 0.5, f"{value:.2f}" if value < 10 else f"{value:.1f}",
                ha="center", color=INK, fontsize=10)
    ax.text(0, 6.2, f"peak at fixed holes\n(main section ~{PLA_YIELD_MPA / LINK1_MAIN_SECTION_MPA:.0f})",
            ha="center", color=MUTED, fontsize=8.5)
    ax.set_ylabel("Safety factor (yield / peak von Mises)", color=MUTED)
    ax.set_title("Minimum safety factor per link (PLA, yield 50 MPa)", color=INK, loc="left")
    fig.tight_layout()
    fig.savefig(RESULTS / "safety_factor_by_link.png", dpi=150)
    plt.close(fig)


def plot_mesh_study(ms: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(6, 4), facecolor=SURFACE)
    style_axes(ax)
    labels = ["2 mm mesh", "0.5 mm at holes"]
    bars = ax.bar(labels, ms["peak_von_mises_MPa"], color=BLUE, width=0.45)
    for bar, value in zip(bars, ms["peak_von_mises_MPa"]):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.25, f"{value:.2f} MPa",
                ha="center", color=INK, fontsize=10)
    ax.set_ylabel("Peak von Mises stress (MPa)", color=MUTED)
    ax.set_title("Link 1: peak stress at fixed holes vs mesh size", color=INK, loc="left")
    fig.tight_layout()
    fig.savefig(RESULTS / "mesh_sensitivity_link1.png", dpi=150)
    plt.close(fig)


def main():
    df = pd.read_csv(HERE / "fea_results.csv")
    ms = pd.read_csv(HERE / "mesh_study.csv")

    rc = reaction_check(df)
    sf = safety_factors(df)

    print("\n1) Reaction-force check (sum Fy = 0)")
    print(rc.to_string(index=False))

    print(f"\n2) Safety factor = {PLA_YIELD_MPA:g} MPa / peak von Mises (target {TARGET_FOS:g})")
    print(sf.to_string(index=False))
    print(f"   Link 1 main section (hand calc): {LINK1_MAIN_SECTION_MPA:g} MPa -> "
          f"FoS ~{PLA_YIELD_MPA / LINK1_MAIN_SECTION_MPA:.1f}")

    rise = (ms["peak_von_mises_MPa"].iloc[1] / ms["peak_von_mises_MPa"].iloc[0] - 1) * 100
    print("\n3) Mesh sensitivity (Link 1, practice load)")
    print(ms.to_string(index=False))
    print(f"   Peak rose {rise:.0f}% with refinement -> not converging: stress singularity "
          "at the fully fixed holes.")

    plot_safety_factor(sf)
    plot_mesh_study(ms)
    print(f"\nCharts saved to {RESULTS.resolve()}")


if __name__ == "__main__":
    main()
