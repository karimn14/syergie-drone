# spray_command_mapper_confidence.py – Adjust spray duration using AI confidence score
import pandas as pd

def build_spray_commands(trees, dosage_file="pollen_dosage_table.csv"):
    dosage_df = pd.read_csv(dosage_file)
    commands = []
    for t in trees:
        age = t.get("age", 7)
        confidence = t.get("confidence", 0.9)  # default if not given
        match = dosage_df.iloc[(dosage_df["Tree Age (Years)"] - age).abs().argsort()[:1]]
        base_duration = int(match["Spray Duration (ms)"].values[0])
        # Scale duration by confidence (e.g., linear scaling)
        duration = int(base_duration * confidence)
        commands.append({
            "tree_id": t["id"],
            "lat": t["lat"],
            "lon": t["lon"],
            "duration_ms": duration,
            "command": f"S,{duration}"
        })
    pd.DataFrame(commands).to_csv("spray_commands_linked.csv", index=False)
    return commands
