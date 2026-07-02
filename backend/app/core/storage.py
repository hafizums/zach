import os
from pathlib import Path
from .config import settings

def init_storage():
    """Initialize local storage directories."""
    base_dir = Path(settings.storage_dir)
    
    directories = [
        base_dir / "projects",
        base_dir / "temp",
        base_dir / "renders",
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        
    return base_dir.exists()
