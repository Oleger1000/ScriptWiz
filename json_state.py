import json
import os

def load_state(file_path, default=True):
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f).get('enabled', default)
    return default

def save_state(file_path, enabled):
    with open(file_path, 'w') as f:
        json.dump({'enabled': enabled}, f)
