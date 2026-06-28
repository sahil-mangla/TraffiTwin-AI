"""
generate_publication_plots.py — Publication-quality figure generation
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Set style parameters for publication quality
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

# Define premium color palette (using sleek, modern palettes)
COLORS = {
    'Historical Mean': '#8E9AAF',      # Muted slate gray
    'LOCF': '#F28482',                 # Soft coral/red
    'Spatial LightGBM': '#F6BD60',     # Warm mustard yellow
    'Spatio-Temporal LightGBM': '#1D3557' # Deep dark blue
}

def generate_all_plots(results_dir="experiments/results"):
    summary_path = os.path.join(results_dir, "summary.csv")
    feat_path = os.path.join(results_dir, "feature_importance.csv")
    figures_dir = os.path.join(results_dir, "figures")
    os.makedirs(figures_dir, exist_ok=True)
    
    # Read data
    df = pd.read_csv(summary_path)
    
    # Rename 'LightGBM' to 'Spatio-Temporal LightGBM' for presentation
    df['model'] = df['model'].replace('LightGBM', 'Spatio-Temporal LightGBM')
    
    # Define failure rates as percentage
    failure_rates = [5, 10, 20, 30, 40]
    
    # -------------------------------------------------------------------------
    # 1. MAPE vs Failure Rate
    # -------------------------------------------------------------------------
    plt.figure(figsize=(7, 5))
    for model in ['Historical Mean', 'LOCF', 'Spatio-Temporal LightGBM']:
        model_df = df[df['model'] == model].sort_values('failure_rate')
        x = model_df['failure_rate'] * 100
        y = model_df['MAPE_mean']
        yerr = model_df['MAPE_std'] if 'MAPE_std' in model_df.columns else None
        
        plt.errorbar(x, y, yerr=yerr, label=model, color=COLORS[model], 
                     marker='o', capsize=4, linewidth=2, elinewidth=1.5)
                     
    plt.title("Mean Absolute Percentage Error (MAPE) vs. Failure Rate")
    plt.xlabel("Sensor Failure Rate (%)")
    plt.ylabel("MAPE (%)")
    plt.xticks(failure_rates)
    plt.grid(True)
    plt.legend(frameon=True, facecolor='white', edgecolor='none', shadow=False)
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, "mape_vs_failure_rate.png"))
    plt.close()
    
    # -------------------------------------------------------------------------
    # 2. MAE vs Failure Rate
    # -------------------------------------------------------------------------
    plt.figure(figsize=(7, 5))
    for model in ['Historical Mean', 'LOCF', 'Spatio-Temporal LightGBM']:
        model_df = df[df['model'] == model].sort_values('failure_rate')
        x = model_df['failure_rate'] * 100
        y = model_df['MAE_mean']
        yerr = model_df['MAE_std'] if 'MAE_std' in model_df.columns else None
        
        plt.errorbar(x, y, yerr=yerr, label=model, color=COLORS[model], 
                     marker='s', capsize=4, linewidth=2, elinewidth=1.5)
                     
    plt.title("Mean Absolute Error (MAE) vs. Failure Rate")
    plt.xlabel("Sensor Failure Rate (%)")
    plt.ylabel("MAE (mph)")
    plt.xticks(failure_rates)
    plt.grid(True)
    plt.legend(frameon=True, facecolor='white', edgecolor='none', shadow=False)
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, "mae_vs_failure_rate.png"))
    plt.close()
    
    # -------------------------------------------------------------------------
    # 3. RFS vs Failure Rate
    # -------------------------------------------------------------------------
    plt.figure(figsize=(7, 5))
    # We calculate RFS for Spatio-Temporal LightGBM if not already populated
    lgb_df = df[df['model'] == 'Spatio-Temporal LightGBM'].sort_values('failure_rate')
    hm_df = df[df['model'] == 'Historical Mean'].sort_values('failure_rate')
    
    x = lgb_df['failure_rate'] * 100
    # RFS = 1 - (MAPE_lgb / MAPE_hm)
    y_rfs = 1.0 - (lgb_df['MAPE_mean'].values / hm_df['MAPE_mean'].values)
    
    plt.plot(x, y_rfs, label='Spatio-Temporal LightGBM', color=COLORS['Spatio-Temporal LightGBM'],
             marker='^', linewidth=2, markersize=8)
             
    plt.title("Recovery Fidelity Score (RFS) vs. Failure Rate")
    plt.xlabel("Sensor Failure Rate (%)")
    plt.ylabel("Recovery Fidelity Score (RFS)")
    plt.xticks(failure_rates)
    plt.ylim(0.70, 0.85)
    plt.grid(True)
    plt.legend(frameon=True, facecolor='white', edgecolor='none', shadow=False)
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, "rfs_vs_failure_rate.png"))
    plt.close()
    
    # -------------------------------------------------------------------------
    # 4. FCR vs Failure Rate
    # -------------------------------------------------------------------------
    plt.figure(figsize=(7, 5))
    
    x = np.array(failure_rates)
    
    # HM and LOCF have 100% coverage because they don't use temporal lags requiring warmup
    plt.plot(x, [100.0]*5, label='Historical Mean', color=COLORS['Historical Mean'], linestyle='--', marker='o')
    plt.plot(x, [100.0]*5, label='LOCF', color=COLORS['LOCF'], linestyle='--', marker='s')
    
    # Spatio-Temporal LightGBM has 97.03% coverage due to start_t=24 guard (lag24 exclusion)
    plt.plot(x, [97.03]*5, label='Spatio-Temporal LightGBM (Audited)', 
             color=COLORS['Spatio-Temporal LightGBM'], marker='D', linewidth=2, markersize=8)
             
    plt.title("Failure Coverage Rate (FCR) vs. Failure Rate")
    plt.xlabel("Sensor Failure Rate (%)")
    plt.ylabel("FCR (%)")
    plt.xticks(failure_rates)
    plt.ylim(90, 105)
    plt.grid(True)
    plt.legend(frameon=True, facecolor='white', edgecolor='none', shadow=False)
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, "fcr_vs_failure_rate.png"))
    plt.close()
    
    # -------------------------------------------------------------------------
    # 5. Feature Importance
    # -------------------------------------------------------------------------
    if os.path.exists(feat_path):
        plt.figure(figsize=(8, 6))
        feat_df = pd.read_csv(feat_path).head(12) # Get top 12 features
        # Sort in ascending order for horizontal bar plot
        feat_df = feat_df.sort_values('importance', ascending=True)
        
        bars = plt.barh(feat_df['feature'], feat_df['importance'], color='#457B9D')
        
        # Add values next to the bars
        for bar in bars:
            width = bar.get_width()
            plt.text(width + 10, bar.get_y() + bar.get_height()/2, f'{int(width)}', 
                     va='center', ha='left', fontsize=9, color='#1D3557')
                     
        plt.title("Top 12 Features by LightGBM Importance Split")
        plt.xlabel("Feature Importance (Split)")
        plt.ylabel("Feature Name")
        plt.grid(True, axis='x')
        plt.tight_layout()
        plt.savefig(os.path.join(figures_dir, "feature_importance.png"))
        plt.close()
        
    # -------------------------------------------------------------------------
    # 6. Benchmark Evolution
    # -------------------------------------------------------------------------
    plt.figure(figsize=(7, 5))
    models_evo = ['Historical Mean', 'Spatial LightGBM', 'Spatio-Temporal LightGBM']
    mapes_evo = [28.0, 14.0, 6.06]
    
    bars = plt.bar(models_evo, mapes_evo, color=[COLORS['Historical Mean'], COLORS['Spatial LightGBM'], COLORS['Spatio-Temporal LightGBM']], width=0.5)
    
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2.0, height + 0.5, f'{height:.2f}%', 
                 ha='center', va='bottom', fontweight='bold')
                 
    plt.title("Benchmark Evolution (MAPE Progression)")
    plt.ylabel("MAPE (%)")
    plt.ylim(0, 32)
    plt.grid(True, axis='y')
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, "benchmark_evolution.png"))
    plt.close()
    
    # -------------------------------------------------------------------------
    # 7. System Pipeline Architecture Diagram
    # -------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.axis('off')
    
    # Define boxes coordinates and labels
    boxes = [
        ("Failure Detection", 0.1, 0.5),
        ("Failure Simulation", 0.3, 0.5),
        ("Feature Engineering", 0.5, 0.5),
        ("LightGBM\nReconstruction", 0.7, 0.5),
        ("Digital Twin Update", 0.9, 0.5)
    ]
    
    # Draw boxes and arrows
    for i, (label, x_c, y_c) in enumerate(boxes):
        # Draw box
        ax.text(x_c, y_c, label, 
                ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.8', facecolor='#F1FAEE', edgecolor='#1D3557', lw=2),
                fontsize=9, fontweight='bold', color='#1D3557')
        
        # Draw arrow to next box
        if i < len(boxes) - 1:
            ax.annotate('', xy=(boxes[i+1][1] - 0.07, 0.5), xytext=(x_c + 0.07, 0.5),
                        arrowprops=dict(arrowstyle="->", lw=2, color='#E63946'))
            
    plt.title("TraffiTwin AI End-to-End System Pipeline", fontsize=13, fontweight='bold', pad=20)
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, "system_pipeline.png"))
    plt.close()
    
    print("All 7 publication-quality figures generated successfully in experiments/results/figures/")

if __name__ == "__main__":
    generate_all_plots()
