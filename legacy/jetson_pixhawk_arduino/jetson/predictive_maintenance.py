"""
predictive_maintenance.py
Predictive maintenance and self-diagnostics for Drone Sawit.
"""
import os
import json
import time

COMPONENTS = {
    'motor': {'cycles': 0, 'limit': 1000},
    'battery': {'cycles': 0, 'limit': 500},
    'sensor': {'cycles': 0, 'limit': 800}
}

MAINTENANCE_FILE = 'maintenance_state.json'

def load_state():
    if os.path.exists(MAINTENANCE_FILE):
        with open(MAINTENANCE_FILE) as f:
            return json.load(f)
    return COMPONENTS.copy()

def save_state(state):
    with open(MAINTENANCE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def update_cycles(component):
    state = load_state()
    if component in state:
        state[component]['cycles'] += 1
        save_state(state)
        check_maintenance(state)

def check_maintenance(state=None):
    if state is None:
        state = load_state()
    alerts = {}
    for comp, data in state.items():
        if data['cycles'] >= data['limit']:
            alerts[comp] = 'Maintenance due!'
    return alerts

if __name__ == "__main__":
    update_cycles('motor')
    print(check_maintenance())
