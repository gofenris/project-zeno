import os
from pathlib import Path
from dotenv import load_dotenv

class Config:
    def __init__(self):
        load_dotenv()
        
        self.LANGFUSE_SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY")
        self.LANGFUSE_PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY")
        self.LANGFUSE_BASE_URL = os.environ.get("LANGFUSE_BASE_URL")
        
        # Data storage
        self.DATA_DIR = Path("trace_data")
        self.DATA_DIR.mkdir(exist_ok=True)
        
        # API settings
        self.TRACES_PER_PAGE = 100
        self.REQUEST_TIMEOUT = 30
