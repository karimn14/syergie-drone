import json
from route_generator import generate_plan
from spray_command_mapper import build_spray_commands

# Fungsi ini seharusnya ada di ai_output_loader.py, tapi kita definisikan di sini untuk kemudahan
def load_ai_predictions(path="predicted_trees.geojson"):
    """Memuat dan memfilter pohon target dari file GeoJSON."""
    print(f"Membaca data dari: {path}")
    with open(path) as f:
        data = json.load(f)

    trees = []
    for feature in data["features"]:
        # Memastikan hanya pohon betina yang sedang berbunga yang diambil
        if feature["properties"].get("sex") == "female" and feature["properties"].get("bloom", False):
            trees.append({
                "id": feature["properties"]["id"],
                "lat": feature["geometry"]["coordinates"][1],
                "lon": feature["geometry"]["coordinates"][0],
                "age": feature["properties"].get("age", 7)
            })
    return trees

# --- ALUR KERJA UTAMA ---
if __name__ == "__main__":
    print("--- Memulai Pengujian Tahap 1 ---")

    # 1. Memuat data pohon target dari file GeoJSON tiruan
    target_trees = load_ai_predictions()
    if not target_trees:
        print("Tidak ada pohon target yang ditemukan. Proses berhenti.")
    else:
        print(f"Berhasil memuat {len(target_trees)} pohon target.")

        # 2. Menghasilkan file rencana penerbangan (.plan)
        print("\nMenghasilkan file rencana penerbangan (route_pollination.plan)...")
        generate_plan(target_trees, output_file="route_pollination.plan")
        print("File .plan berhasil dibuat!")

        # 3. Menghasilkan file perintah semprot (.csv)
        print("\nMenghasilkan file perintah semprot (spray_commands_linked.csv)...")
        build_spray_commands(target_trees, dosage_file="pollen_dosage_table.csv")
        print("File perintah semprot berhasil dibuat!")

        print("\n--- Pengujian Tahap 1 Selesai ---")
