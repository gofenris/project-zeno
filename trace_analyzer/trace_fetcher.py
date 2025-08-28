import requests
import base64
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Any
import time

class TraceFetcher:
    def __init__(self, config):
        self.config = config
        self.auth_header = self._create_auth_header()
    
    def _create_auth_header(self):
        auth = base64.b64encode(
            f"{self.config.LANGFUSE_PUBLIC_KEY}:{self.config.LANGFUSE_SECRET_KEY}".encode()
        ).decode()
        return {"Authorization": f"Basic {auth}"}
    
    def fetch_last_n_days(self, n_days: int = 5, environment: str = "default") -> Dict[str, Any]:
        """Fetch traces for the last n days, organized by day"""
        results = {}
        
        for i in range(n_days):
            date = datetime.now(timezone.utc) - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            
            # Define day boundaries
            start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)
            
            traces = self._fetch_traces_for_period(
                start_of_day, end_of_day, environment
            )
            
            # Save traces
            self._save_traces(date_str, traces)
            
            # Generate summary
            summary = self._generate_summary(traces)
            self._save_summary(date_str, summary)
            
            results[date_str] = {
                'trace_count': len(traces),
                'summary': summary
            }
        
        return results
    
    def _fetch_traces_for_period(self, start_time: datetime, end_time: datetime, environment: str) -> List[Dict]:
        """Fetch all traces for a specific time period"""
        url = f"{self.config.LANGFUSE_BASE_URL.rstrip('/')}/api/public/traces"
        all_traces = []
        next_page = None
        
        while True:
            params = {
                "fromTimestamp": start_time.isoformat(),
                "toTimestamp": end_time.isoformat(),
                "limit": self.config.TRACES_PER_PAGE
            }
            
            if next_page:
                params["page"] = next_page
            
            # Add environment filter if specified
            if environment:
                params["environment"] = environment
            
            response = requests.get(
                url, 
                headers=self.auth_header, 
                params=params, 
                timeout=self.config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            
            data = response.json()
            batch = data.get("data", [])
            
            if not batch:
                break
                
            all_traces.extend(batch)
            
            next_page = data.get("nextPage")
            if not next_page or len(batch) < self.config.TRACES_PER_PAGE:
                break
                
            time.sleep(0.05)  # Rate limiting
        
        return all_traces
    
    def _save_traces(self, date_str: str, traces: List[Dict]):
        """Save traces to JSONL file"""
        file_path = self.config.DATA_DIR / f"{date_str}_traces.jsonl"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            for trace in traces:
                f.write(json.dumps(trace, ensure_ascii=False) + '\n')
    
    def _save_summary(self, date_str: str, summary: List[Dict]):
        """Save summary to JSON file"""
        file_path = self.config.DATA_DIR / f"{date_str}_summary.json"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
    
    def _generate_summary(self, traces: List[Dict]) -> List[Dict]:
        """Generate summary data from traces"""
        from trace_summarizer import TraceSummarizer
        summarizer = TraceSummarizer()
        return [summarizer.summarize_trace(trace) for trace in traces]
