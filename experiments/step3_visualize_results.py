"""
visualize_results.py — Result Visualization
===========================================
Generates all benchmark plots (quick diagnostic + publication-quality) from
experiments/results/summary.csv and feature_importance.csv. Merged from the
former visualize_results.py + generate_publication_plots.py, which duplicated
plot generation from the same source CSVs.
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['DejaVu Sans', 'Arial', 'Helvetica'],
    'font.size': 11,
    'axes.labelsize': 12,
    'axes.titlesize': 13,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
    'figure.titlesize': 14,
    'savefig.dpi': 300,
    'grid.alpha': 0.3,
    'grid.linestyle': '--'
})

COLORS = {
    'Historical Mean': '#8E9AAF',
    'LOCF': '#F28482',
    'Spatial LightGBM': '#F6BD60',
    'Spatio-Temporal LightGBM': '#1D3557'
}


def plot_metric_by_failure_rate(df, mean_col, std_col, filename, ylabel, figures_dir, models=None):
    """Generic per-metric line plot across all models present in the summary."""
    plt.figure(figsize=(8, 6))
    markers = ['o', 's', '^', 'D', 'v']
    models = models if models is not None else df['model'].unique()

    for idx, model in enumerate(models):
        model_df = df[df['model'] == model].sort_values('failure_rate')
        if model_df.empty:
            continue
        x = model_df['failure_rate'] * 100
        y = model_df[mean_col]

        if std_col and std_col in model_df.columns:
            yerr = model_df[std_col]
            plt.errorbar(x, y, yerr=yerr, label=model, marker=markers[idx % len(markers)],
                         capsize=5, linewidth=2)
        else:
            plt.plot(x, y, label=model, marker=markers[idx % len(markers)], linewidth=2)

    plt.xlabel("Failure Rate (%)")
    plt.ylabel(ylabel)
    plt.legend(frameon=True, facecolor='white', edgecolor='none')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, filename))
    plt.close()
    print(f"Saved figure: {os.path.join(figures_dir, filename)}")


def plot_feature_importance(feat_path, figures_dir):
    if not os.path.exists(feat_path):
        return
    plt.figure(figsize=(8, 6))
    feat_df = pd.read_csv(feat_path).head(12).sort_values('importance', ascending=True)

    bars = plt.barh(feat_df['feature'], feat_df['importance'], color='#457B9D')
    for bar in bars:
        width = bar.get_width()
        plt.text(width + 10, bar.get_y() + bar.get_height() / 2, f'{int(width)}',
                 va='center', ha='left', fontsize=9, color='#1D3557')

    plt.title("Top 12 Features by LightGBM Importance Split")
    plt.xlabel("Feature Importance (Split)")
    plt.ylabel("Feature Name")
    plt.grid(True, axis='x')
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, "feature_importance.png"))
    plt.close()
    print(f"Saved figure: {os.path.join(figures_dir, 'feature_importance.png')}")


def plot_system_pipeline(figures_dir):
    """Static diagram of the reconstruction pipeline stages — not data-derived."""
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.axis('off')

    boxes = [
        ("Failure Detection", 0.1, 0.5),
        ("Failure Simulation", 0.3, 0.5),
        ("Feature Engineering", 0.5, 0.5),
        ("LightGBM\nReconstruction", 0.7, 0.5),
        ("Digital Twin Update", 0.9, 0.5)
    ]

    for i, (label, x_c, y_c) in enumerate(boxes):
        ax.text(x_c, y_c, label,
                ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.8', facecolor='#F1FAEE', edgecolor='#1D3557', lw=2),
                fontsize=9, fontweight='bold', color='#1D3557')
        if i < len(boxes) - 1:
            ax.annotate('', xy=(boxes[i + 1][1] - 0.07, 0.5), xytext=(x_c + 0.07, 0.5),
                        arrowprops=dict(arrowstyle="->", lw=2, color='#E63946'))

    plt.title("TraffiTwin AI End-to-End System Pipeline", fontsize=13, fontweight='bold', pad=20)
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, "system_pipeline.png"))
    plt.close()
    print(f"Saved figure: {os.path.join(figures_dir, 'system_pipeline.png')}")


def generate_plots(results_dir="experiments/results"):
    """Quick diagnostic pass over every model/metric in summary.csv — run after every sweep."""
    summary_path = os.path.join(results_dir, "summary.csv")
    if not os.path.exists(summary_path):
        print(f"Error: Summary file {summary_path} not found.")
        return

    df = pd.read_csv(summary_path)
    figures_dir = os.path.join(results_dir, "figures")
    os.makedirs(figures_dir, exist_ok=True)

    metrics = {
        'MAPE': ('MAPE_mean', 'MAPE_std', 'mape_vs_failure_rate.png', 'MAPE (%)'),
        'MAE': ('MAE_mean', 'MAE_std', 'mae_vs_failure_rate.png', 'MAE'),
        'RFS': ('RFS_mean', None, 'rfs_vs_failure_rate.png', 'Recovery Fidelity Score (RFS)'),
        'FCR': ('FCR_mean', None, 'fcr_vs_failure_rate.png', 'Failure Coverage Rate (FCR) %')
    }
    for mean_col, std_col, filename, ylabel in metrics.values():
        plot_metric_by_failure_rate(df, mean_col, std_col, filename, ylabel, figures_dir)


def generate_publication_plots(results_dir="experiments/results"):
    """Presentation-styled figures for the LightGBM sweep, using the real FCR/RFS
    values from summary.csv rather than hardcoded placeholders."""
    summary_path = os.path.join(results_dir, "summary.csv")
    feat_path = os.path.join(results_dir, "feature_importance.csv")
    figures_dir = os.path.join(results_dir, "figures")
    os.makedirs(figures_dir, exist_ok=True)

    df = pd.read_csv(summary_path)
    df['model'] = df['model'].replace('LightGBM', 'Spatio-Temporal LightGBM')

    models = ['Historical Mean', 'LOCF', 'Spatio-Temporal LightGBM']
    plot_metric_by_failure_rate(df, 'MAPE_mean', 'MAPE_std', 'mape_vs_failure_rate.png',
                                 'MAPE (%)', figures_dir, models=models)
    plot_metric_by_failure_rate(df, 'MAE_mean', 'MAE_std', 'mae_vs_failure_rate.png',
                                 'MAE (mph)', figures_dir, models=models)

    lgb_df = df[df['model'] == 'Spatio-Temporal LightGBM'].sort_values('failure_rate')
    hm_df = df[df['model'] == 'Historical Mean'].sort_values('failure_rate')

    plt.figure(figsize=(7, 5))
    x = lgb_df['failure_rate'] * 100
    if lgb_df['RFS_mean'].notna().any():
        y_rfs = lgb_df['RFS_mean']
    else:
        y_rfs = 1.0 - (lgb_df['MAPE_mean'].values / hm_df['MAPE_mean'].values)
    plt.plot(x, y_rfs, label='Spatio-Temporal LightGBM', color=COLORS['Spatio-Temporal LightGBM'],
             marker='^', linewidth=2, markersize=8)
    plt.title("Recovery Fidelity Score (RFS) vs. Failure Rate")
    plt.xlabel("Sensor Failure Rate (%)")
    plt.ylabel("Recovery Fidelity Score (RFS)")
    plt.grid(True)
    plt.legend(frameon=True, facecolor='white', edgecolor='none')
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, "rfs_vs_failure_rate.png"))
    plt.close()

    plt.figure(figsize=(7, 5))
    x = lgb_df['failure_rate'] * 100
    plt.plot(x, [100.0] * len(x), label='Historical Mean', color=COLORS['Historical Mean'],
              linestyle='--', marker='o')
    plt.plot(x, [100.0] * len(x), label='LOCF', color=COLORS['LOCF'], linestyle='--', marker='s')
    plt.plot(x, lgb_df['FCR_mean'], label='Spatio-Temporal LightGBM',
             color=COLORS['Spatio-Temporal LightGBM'], marker='D', linewidth=2, markersize=8)
    plt.title("Failure Coverage Rate (FCR) vs. Failure Rate")
    plt.xlabel("Sensor Failure Rate (%)")
    plt.ylabel("FCR (%)")
    plt.grid(True)
    plt.legend(frameon=True, facecolor='white', edgecolor='none')
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, "fcr_vs_failure_rate.png"))
    plt.close()

    plot_feature_importance(feat_path, figures_dir)
    plot_system_pipeline(figures_dir)

    print("Publication-quality figures generated in experiments/results/figures/")


if __name__ == "__main__":
    generate_plots()
    generate_publication_plots()
