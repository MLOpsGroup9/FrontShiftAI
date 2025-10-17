"""
Plotting utilities for dataflow statistics.
Reduces matplotlib boilerplate.
"""

import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Optional, Dict, Any

# Set style once
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (10, 6)


def save_plot(fig, filename: str, output_dir: str = "logs", dpi: int = 100):
    """Save plot to file and close."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    filepath = Path(output_dir) / filename
    fig.savefig(filepath, dpi=dpi, bbox_inches='tight')
    plt.close(fig)
    return str(filepath)


def quick_hist(data, title: str, xlabel: str, bins: int = 30, output_dir: str = "logs", 
               filename: Optional[str] = None) -> str:
    """Create and save histogram in one call."""
    fig, ax = plt.subplots()
    ax.hist(data, bins=bins, edgecolor='black', alpha=0.7)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel('Frequency')
    ax.grid(True, alpha=0.3)
    return save_plot(fig, filename or f"{title.lower().replace(' ', '_')}.png", output_dir)


def quick_bar(categories, values, title: str, xlabel: str, ylabel: str,
              output_dir: str = "logs", filename: Optional[str] = None) -> str:
    """Create and save bar chart in one call."""
    fig, ax = plt.subplots()
    ax.bar(categories, values, edgecolor='black', alpha=0.7)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3, axis='y')
    plt.xticks(rotation=45, ha='right')
    return save_plot(fig, filename or f"{title.lower().replace(' ', '_')}.png", output_dir)


def quick_box(data_dict: Dict[str, Any], title: str, ylabel: str,
              output_dir: str = "logs", filename: Optional[str] = None) -> str:
    """Create and save box plot in one call."""
    fig, ax = plt.subplots()
    ax.boxplot(data_dict.values(), labels=data_dict.keys())
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3, axis='y')
    plt.xticks(rotation=45, ha='right')
    return save_plot(fig, filename or f"{title.lower().replace(' ', '_')}.png", output_dir)

