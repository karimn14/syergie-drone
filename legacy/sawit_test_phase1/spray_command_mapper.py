import pandas as pd

def build_spray_commands(trees, dosage_file="pollen_dosage_table.csv"):
    dosage_df = pd.read_csv(dosage_file)
    commands = []
    for t in trees:
        age = t.get("age", 7)
        match = dosage_df.iloc[(dosage_df["Tree Age (Years)"] - age).abs().argsort()[:1]]
        duration = int(match["Spray Duration (ms)"].values[0])
        commands.append({
            "tree_id": t["id"],
            "lat": t["lat"],
            "lon": t["lon"],
            "duration_ms": duration,
            "command": f"S,{duration}"
        })
    pd.DataFrame(commands).to_csv("spray_commands_linked.csv", index=False)
    return commands
