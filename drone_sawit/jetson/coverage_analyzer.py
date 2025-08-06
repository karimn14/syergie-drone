# coverage_analyzer.py – Analyze post-mission spray effectiveness
import pandas as pd
import matplotlib.pyplot as plt

def analyze_coverage(log_file="spray_log.csv"):
    df = pd.read_csv(log_file)
    sprayed = df[df["status"] == "sprayed"]
    plt.figure(figsize=(8, 6))
    plt.scatter(sprayed["lon"], sprayed["lat"], c=sprayed["duration_ms"], cmap="viridis", label="Sprayed")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.title("Spray Coverage Heatmap")
    plt.colorbar(label="Spray Duration (ms)")
    plt.legend()
    plt.tight_layout()
    plt.savefig("coverage_report.png")
    print("\U0001F4CA Coverage heatmap saved to coverage_report.png")
