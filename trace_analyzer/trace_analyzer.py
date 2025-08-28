import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Any

class TraceAnalyzer:
    def __init__(self, config):
        self.config = config
    
    def get_basic_summary(self, days: int = 5) -> Dict[str, Any]:
        """Generate basic summary analysis for last N days"""
        daily_data = self._load_daily_summaries(days)
        
        summary_table = {}
        time_series_data = {
            'dates': [],
            'trace_counts': [],
            'success_rates': []
        }
        
        for date_str in sorted(daily_data.keys()):
            summaries = daily_data[date_str]
            
            # Calculate metrics
            total_traces = len(summaries)
            successful_traces = sum(1 for s in summaries if s.get('overall_success', False))
            unique_users = len(set(s.get('userId') for s in summaries if s.get('userId')))
            unique_sessions = len(set(s.get('sessionId') for s in summaries if s.get('sessionId')))
            
            success_rate = successful_traces / total_traces if total_traces > 0 else 0
            
            summary_table[date_str] = {
                'total_traces': total_traces,
                'successful_traces': successful_traces,
                'success_rate': success_rate,
                'unique_users': unique_users,
                'unique_sessions': unique_sessions,
                'error_traces': sum(1 for s in summaries if s.get('overall_error', False)),
                'no_tool_traces': sum(1 for s in summaries if s.get('no_tools_called', False)),
            }
            
            # Time series data
            time_series_data['dates'].append(date_str)
            time_series_data['trace_counts'].append(total_traces)
            time_series_data['success_rates'].append(success_rate)
        
        return {
            'summary_table': summary_table,
            'time_series': time_series_data
        }
    
    def get_dataset_analysis(self, days: int = 5) -> Dict[str, Any]:
        """Analyze dataset usage and success rates"""
        daily_data = self._load_daily_summaries(days)
        
        dataset_table = {}
        
        for date_str in sorted(daily_data.keys()):
            summaries = daily_data[date_str]
            
            # Collect dataset information
            dataset_stats = defaultdict(lambda: {'attempted': 0, 'successful': 0})
            all_datasets = set()
            
            for summary in summaries:
                datasets = summary.get('datasets_queried', [])
                pull_data_success = summary.get('tool_pull_data_success')
                
                for dataset in datasets:
                    all_datasets.add(dataset)
                    dataset_stats[dataset]['attempted'] += 1
                    if pull_data_success:
                        dataset_stats[dataset]['successful'] += 1
            
            # Calculate success rates
            dataset_summary = {}
            for dataset, stats in dataset_stats.items():
                success_rate = stats['successful'] / stats['attempted'] if stats['attempted'] > 0 else 0
                dataset_summary[dataset] = {
                    'attempted': stats['attempted'],
                    'successful': stats['successful'],
                    'success_rate': success_rate
                }
            
            dataset_table[date_str] = {
                'unique_datasets': len(all_datasets),
                'datasets_list': list(all_datasets),
                'dataset_stats': dataset_summary
            }
        
        return {'dataset_table': dataset_table}
    
    def get_tool_analysis(self, days: int = 5) -> Dict[str, Any]:
        """Analyze tool usage and success rates"""
        daily_data = self._load_daily_summaries(days)
        
        tool_table = {}
        
        for date_str in sorted(daily_data.keys()):
            summaries = daily_data[date_str]
            total_traces = len(summaries)
            
            # Collect tool information
            tool_usage = defaultdict(int)
            tool_success = defaultdict(int)
            tool_calls_per_trace = defaultdict(list)
            
            for summary in summaries:
                unique_tools = summary.get('unique_tools', [])
                tools_used = summary.get('tools_used', [])
                overall_success = summary.get('overall_success', False)
                
                # Count tool usage
                for tool in unique_tools:
                    tool_usage[tool] += 1
                    if overall_success:
                        tool_success[tool] += 1
                
                # Count tool calls per trace
                tool_call_counts = Counter(tool['name'] for tool in tools_used)
                for tool, count in tool_call_counts.items():
                    tool_calls_per_trace[tool].append(count)
            
            # Calculate metrics
            tool_summary = {}
            for tool in tool_usage.keys():
                usage_rate = tool_usage[tool] / total_traces if total_traces > 0 else 0
                success_rate = tool_success[tool] / tool_usage[tool] if tool_usage[tool] > 0 else 0
                
                calls_per_trace = tool_calls_per_trace[tool]
                avg_calls = sum(calls_per_trace) / len(calls_per_trace) if calls_per_trace else 0
                max_calls = max(calls_per_trace) if calls_per_trace else 0
                
                tool_summary[tool] = {
                    'usage_count': tool_usage[tool],
                    'usage_rate': usage_rate,
                    'success_rate': success_rate,
                    'avg_calls_per_trace': avg_calls,
                    'max_calls_per_trace': max_calls
                }
            
            tool_table[date_str] = {
                'unique_tools': len(tool_usage),
                'tools_list': list(tool_usage.keys()),
                'tool_stats': tool_summary
            }
        
        return {'tool_table': tool_table}
    
    def _load_daily_summaries(self, days: int) -> Dict[str, List[Dict]]:
        """Load summary data for the last N days"""
        daily_data = {}
        
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            
            summary_file = self.config.DATA_DIR / f"{date_str}_summary.json"
            
            if summary_file.exists():
                with open(summary_file, 'r', encoding='utf-8') as f:
                    daily_data[date_str] = json.load(f)
            else:
                daily_data[date_str] = []
        
        return daily_data
