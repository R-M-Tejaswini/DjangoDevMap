import json
from pathlib import Path
from typing import Dict, Optional

class LogStore:
    """Store and retrieve analysis and runtime data"""
    
    def __init__(self, file_path: Path):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
    
    def save(self, data: Dict):
        """Save data to JSON file"""
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving data: {e}")
    
    def load(self) -> Optional[Dict]:
        """Load data from JSON file"""
        if not self.file_path.exists():
            return None
        
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading data: {e}")
            return None
    
    def append(self, data: Dict):
        """Append data to existing file (for logs)"""
        try:
            with open(self.file_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(data, default=str) + '\n')
        except Exception as e:
            print(f"Error appending data: {e}")