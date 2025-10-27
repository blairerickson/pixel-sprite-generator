"""
Persistent job history storage using JSON
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

class JobStorage:
    """Manages persistent job history using JSON file storage"""
    
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
    def save_job(self, job_id: str, job_data: Dict[str, Any]):
        """Save or update a job in history"""
        history = self.load_history()
        job_data['job_id'] = job_id
        job_data['saved_at'] = datetime.now().isoformat()
        
        # Update existing or append new
        existing_idx = next((i for i, j in enumerate(history) if j['job_id'] == job_id), None)
        if existing_idx is not None:
            history[existing_idx] = job_data
        else:
            history.append(job_data)
        
        with open(self.storage_path, 'w') as f:
            json.dump(history, f, indent=2)
    
    def load_history(self) -> List[Dict[str, Any]]:
        """Load all job history"""
        if not self.storage_path.exists():
            return []
        try:
            with open(self.storage_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def get_job(self, job_id: str) -> Dict[str, Any]:
        """Get specific job from history"""
        history = self.load_history()
        return next((j for j in history if j['job_id'] == job_id), None)
    
    def delete_job(self, job_id: str) -> bool:
        """Delete a job from history"""
        history = self.load_history()
        original_length = len(history)
        history = [j for j in history if j['job_id'] != job_id]
        
        if len(history) < original_length:
            with open(self.storage_path, 'w') as f:
                json.dump(history, f, indent=2)
            return True
        return False
