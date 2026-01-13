import os
import json

def load_json(filename, default_value={}):
    if default_value is None:
        default_value = {}
    if not os.path.exists(filename):
        print(f"File {filename} not found. Returning default value.")
        return default_value
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = f.read().strip()
            if not data:  # If the file is empty
                return default_value
            return json.loads(data)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON file: {filename}. Returning default value. Error: {e}")
        return default_value
    
def save_json(file_path, data):
    """Save data in a JSON file."""
    try:
        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)
    except IOError as e:
        print(f"Failed to save JSON data to {file_path}. Error: {e}")
