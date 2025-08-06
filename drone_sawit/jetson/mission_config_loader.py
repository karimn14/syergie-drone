# mission_config_loader.py – Load mission-wide YAML config
import yaml

def load_config(path="mission_config.yaml"):
    with open(path) as f:
        config = yaml.safe_load(f)
    return config
