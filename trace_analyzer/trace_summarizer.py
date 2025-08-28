import re
from typing import Dict, List, Any, Optional, Tuple

class TraceSummarizer:
    def summarize_trace(self, trace: Dict) -> Dict:
        """Create a summary of a single trace"""
        
        # Basic info
        summary = {
            'id': trace.get('id'),
            'timestamp': trace.get('timestamp'),
            'environment': trace.get('environment'),
            'userId': trace.get('userId'),
            'sessionId': trace.get('sessionId'),
            'name': trace.get('name'),
            'totalCost': trace.get('totalCost'),
        }
        
        # Extract messages and analyze
        messages = self._extract_messages(trace)
        summary.update(self._analyze_messages(messages))
        
        # Determine success/failure
        summary.update(self._determine_success(messages, summary))
        
        return summary
    
    def _extract_messages(self, trace: Dict) -> List[Dict]:
        """Extract messages from trace output"""
        output = trace.get('output', {})
        return output.get('messages', [])
    
    def _analyze_messages(self, messages: List[Dict]) -> Dict:
        """Analyze messages to extract key information"""
        result = {
            'tools_used': [],
            'datasets_queried': [],
            'aoi_selected': None,
            'user_prompt': '',
            'final_ai_response': '',
            'tool_call_count': 0,
            'unique_tools': set(),
        }
        
        for msg in messages:
            msg_type = msg.get('type')
            
            if msg_type == 'human':
                if not result['user_prompt']:
                    result['user_prompt'] = self._extract_text_content(msg.get('content', ''))
            
            elif msg_type == 'ai':
                result['final_ai_response'] = self._extract_text_content(msg.get('content', ''))
                
                # Count tool calls
                tool_calls = msg.get('tool_calls', [])
                result['tool_call_count'] += len(tool_calls)
                
                for tool_call in tool_calls:
                    tool_name = tool_call.get('name')
                    if tool_name:
                        result['unique_tools'].add(tool_name)
                        result['tools_used'].append({
                            'name': tool_name,
                            'args': tool_call.get('args', {})
                        })
            
            elif msg_type == 'tool':
                tool_name = msg.get('name')
                if tool_name:
                    result['unique_tools'].add(tool_name)
                
                # Extract specific information based on tool
                content = self._extract_text_content(msg.get('content', ''))
                
                if tool_name == 'pick-dataset':
                    dataset = self._extract_selected_dataset(content)
                    if dataset:
                        result['datasets_queried'].append(dataset)
                
                elif tool_name == 'pick-aoi':
                    aoi = self._extract_selected_aoi(content)
                    if aoi:
                        result['aoi_selected'] = aoi
        
        # Convert set to list for JSON serialization
        result['unique_tools'] = list(result['unique_tools'])
        
        return result
    
    def _extract_text_content(self, content) -> str:
        """Extract text from various content formats"""
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            texts = []
            for item in content:
                if isinstance(item, dict):
                    if 'text' in item:
                        texts.append(item['text'])
                    elif 'content' in item:
                        texts.append(item['content'])
            return '\n'.join(texts)
        return ''
    
    def _extract_selected_dataset(self, content: str) -> Optional[str]:
        """Extract dataset name from pick-dataset tool response"""
        match = re.search(r"Selected dataset:\s*(.+)", content, re.IGNORECASE)
        return match.group(1).strip() if match else None
    
    def _extract_selected_aoi(self, content: str) -> Optional[str]:
        """Extract AOI from pick-aoi tool response"""
        match = re.search(r"Selected AOI:\s*([^,\n]+)", content, re.IGNORECASE)
        return match.group(1).strip() if match else None
    
    def _determine_success(self, messages: List[Dict], summary: Dict) -> Dict:
        """Determine if trace was successful based on heuristics"""
        
        # Check for tool failures
        tool_failed = False
        pull_data_called = False
        pull_data_success = False
        
        for msg in messages:
            if msg.get('type') == 'tool':
                content = self._extract_text_content(msg.get('content', ''))
                
                if msg.get('name') == 'pull-data':
                    pull_data_called = True
                    if 'Failed' not in content:
                        pull_data_success = True
                
                if 'Failed' in content or 'Error' in content:
                    tool_failed = True
        
        # Check final AI response for apologies
        final_response = summary.get('final_ai_response', '').lower()
        ai_apologized = any(phrase in final_response for phrase in [
            'sorry', 'apolog', 'unable to', "can't", 'cannot', 'failed to'
        ])
        
        # Determine overall success
        overall_success = (
            pull_data_called and 
            not tool_failed and 
            not ai_apologized and 
            bool(summary.get('final_ai_response', '').strip())
        )
        
        return {
            'overall_success': overall_success,
            'overall_error': tool_failed or ai_apologized,
            'tool_pull_data_success': pull_data_success if pull_data_called else None,
            'no_tools_called': len(summary.get('unique_tools', [])) == 0,
            'pull_data_called': pull_data_called,
        }
