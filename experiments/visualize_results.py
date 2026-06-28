"""
visualize_results.py — Result Visualization
===========================================
Generates matplotlib plots from the benchmark summary.
"""

import os
import pandas as pd
import matplotlib.pyplot as plt

def generate_plots(results_dir="experiments/results"):
    summary_path = os.path.join(results_dir, "summary.csv")
    if not os.path.exists(summary_path):
        print(f"Error: Summary file {summary_path} not found.")
        return
        
    df = pd.read_csv(summary_path)
    
    figures_dir = os.path.join(results_dir, "figures")
    os.makedirs(figures_dir, exist_ok=True)
    
    models = df['model'].unique()
    markers = ['o', 's', '^', 'D', 'v']
    
    # Format: Metric Name -> (mean column, std column, output filename, y-axis label, plot_std)
    metrics = {
        'MAPE': ('MAPE_mean', 'MAPE_std', 'mape_vs_failure_rate.png', 'MAPE (%)', True),
        'MAE': ('MAE_mean', 'MAE_std', 'mae_vs_failure_rate.png', 'MAE', True),
        'RFS': ('RFS_mean', None, 'rfs_vs_failure_rate.png', 'Recovery Fidelity Score (RFS)', False),
        'FCR': ('FCR_mean', None, 'fcr_vs_failure_rate.png', 'Failure Coverage Rate (FCR) %', False)
    }
    
    for metric_name, (mean_col, std_col, filename, ylabel, has_std) in metrics.items():
        plt.figure(figsize=(8, 6))
        
        for idx, model in enumerate(models):
            model_df = df[df['model'] == model].sort_values('failure_rate')
            
            x = model_df['failure_rate'] * 100  # Convert to percentage
            y = model_df[mean_col]
            
            if has_std and std_col in model_df.columns:
                yerr = model_df[std_col]
                plt.errorbar(x, y, yerr=yerr, label=model, marker=markers[idx % len(markers)], capsize=5, linewidth=2)
            else:
                plt.plot(x, y, label=model, marker=markers[idx % len(markers)], linewidth=2)
                
        plt.title(f"{metric_name} vs Failure Rate")
        plt.xlabel("Failure Rate (%)")
        plt.ylabel(ylabel)
        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()
        
        plt.savefig(os.path.join(figures_dir, filename), dpi=300)
        plt.close()
        print(f"Saved figure: {os.path.join(figures_dir, filename)}")

if __name__ == "__main__":
    generate_plots()
