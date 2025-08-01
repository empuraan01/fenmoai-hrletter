"""
Response formatter for improving search result presentation
"""

import re
from typing import List, Dict, Any
from collections import defaultdict

class ResponseFormatter:
    """Formats search results into user-friendly responses"""
    
    def __init__(self):
        self.band_mapping = {
            'L1': 'Junior Level',
            'L2': 'Mid Level', 
            'L3': 'Senior Level',
            'L4': 'Lead Level',
            'L5': 'Executive Level'
        }
    
    def format_policy_search_results(self, query: str, results: List[Dict[str, Any]]) -> str:
        """Format policy search results into a user-friendly response"""
        
        if not results:
            return self._format_no_results_message(query)
        
        query_analysis = self._analyze_query(query)
        
        organized_results = self._organize_results(results, query_analysis)
        
        response = self._build_response(query, query_analysis, organized_results)
        
        return response
    
    def _analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze the user query to understand intent and context"""
        
        query_lower = query.lower()
        analysis = {
            'topic': None,
            'specific_band': None,
            'band_level': None,
            'is_general': True,
            'keywords': []
        }
        
        band_match = re.search(r'L[1-5]', query.upper())
        if band_match:
            analysis['specific_band'] = band_match.group()
            analysis['band_level'] = self.band_mapping.get(analysis['specific_band'], 'Unknown')
            analysis['is_general'] = False
        
        if any(term in query_lower for term in ['senior', 'executive', 'lead']):
            if 'senior' in query_lower:
                analysis['band_level'] = 'Senior Level (L3+)'
            elif 'executive' in query_lower:
                analysis['band_level'] = 'Executive Level (L5)'
            elif 'lead' in query_lower:
                analysis['band_level'] = 'Lead Level (L4+)'
            analysis['is_general'] = False
        
        if any(term in query_lower for term in ['leave', 'vacation', 'time off', 'sick', 'casual']):
            analysis['topic'] = 'leave_policy'
        elif any(term in query_lower for term in ['travel', 'trip', 'allowance', 'per diem', 'flight', 'hotel']):
            analysis['topic'] = 'travel_policy'
        elif any(term in query_lower for term in ['wfh', 'work from home', 'remote', 'hybrid']):
            analysis['topic'] = 'work_arrangements'
        elif any(term in query_lower for term in ['compensation', 'salary', 'pay']):
            analysis['topic'] = 'compensation'
        
        analysis['keywords'] = self._extract_keywords(query_lower)
        
        return analysis
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract important keywords from the query"""
        
        important_terms = [
            'leave', 'travel', 'allowance', 'policy', 'days', 'per diem',
            'hotel', 'flight', 'sick', 'casual', 'earned', 'wfh', 'remote',
            'senior', 'junior', 'executive', 'lead', 'band', 'compensation'
        ]
        
        found_keywords = []
        for term in important_terms:
            if term in query:
                found_keywords.append(term)
        
        return found_keywords
    
    def _organize_results(self, results: List[Dict[str, Any]], query_analysis: Dict[str, Any]) -> Dict[str, List[Dict]]:
        """Organize results by relevance and remove redundancy"""
        
        organized = {
            'high_relevance': [],
            'medium_relevance': [],
            'tables_and_matrices': [],
            'general_info': []
        }
        
        seen_content = set()
        
        for result in results:
            content = result['content']
            similarity = result['similarity']
            
            content_key = self._get_content_signature(content)
            if content_key in seen_content:
                continue
            seen_content.add(content_key)
            
            if self._is_table_or_matrix(content):
                organized['tables_and_matrices'].append(result)
            elif similarity > 0.5:
                organized['high_relevance'].append(result)
            elif similarity > 0.4:
                organized['medium_relevance'].append(result)
            else:
                organized['general_info'].append(result)
        
        for category in organized:
            organized[category] = organized[category][:3]  # Max 3 per category
        
        return organized
    
    def _get_content_signature(self, content: str) -> str:
        """Get a signature of content to detect duplicates"""
        cleaned = re.sub(r'\s+', ' ', content.strip())
        return cleaned[:50].lower()
    
    def _is_table_or_matrix(self, content: str) -> bool:
        """Check if content contains tabular data"""
        table_indicators = [
            'matrix', 'table', 'band', 'l1', 'l2', 'l3', 'l4', 'l5',
            '|', 'header', 'row', 'column'
        ]
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in table_indicators)
    
    def _build_response(self, query: str, analysis: Dict[str, Any], organized_results: Dict[str, List[Dict]]) -> str:
        """Build the final formatted response"""
        
        response_parts = []
        
        header = self._build_header(query, analysis)
        response_parts.append(header)
        
        if organized_results['tables_and_matrices']:
            response_parts.append("\n📊 **Policy Matrix/Table Information:**")
            for result in organized_results['tables_and_matrices']:
                formatted_content = self._format_table_content(result['content'])
                response_parts.append(f"\n{formatted_content}")
        
        if organized_results['high_relevance']:
            response_parts.append("\n🎯 **Key Policy Details:**")
            for i, result in enumerate(organized_results['high_relevance'], 1):
                formatted_content = self._format_policy_content(result['content'])
                response_parts.append(f"\n**{i}.** {formatted_content}")
        
        if organized_results['medium_relevance']:
            response_parts.append("\n📋 **Additional Information:**")
            for i, result in enumerate(organized_results['medium_relevance'], 1):
                formatted_content = self._format_policy_content(result['content'])
                response_parts.append(f"\n**{i}.** {formatted_content}")
        
        suggestions = self._generate_suggestions(analysis)
        if suggestions:
            response_parts.append(f"\n\n💡 **Related Questions You Might Ask:**\n{suggestions}")
        
        return "\n".join(response_parts)
    
    def _build_header(self, query: str, analysis: Dict[str, Any]) -> str:
        """Build a contextual header for the response"""
        
        if analysis['specific_band']:
            band_level = analysis['band_level']
            return f"📋 **Policy Information for {analysis['specific_band']} ({band_level}) employees:**"
        elif analysis['band_level']:
            return f"📋 **Policy Information for {analysis['band_level']} employees:**"
        elif analysis['topic']:
            topic_name = analysis['topic'].replace('_', ' ').title()
            return f"📋 **{topic_name} Information:**"
        else:
            return f"📋 **Policy Information:**"
    
    def _format_table_content(self, content: str) -> str:
        """Format table/matrix content for better readability"""
        
        lines = content.split('\n')
        formatted_lines = []
        
        has_band_data = any(f'L{i}' in content.upper() for i in range(1, 6))
        
        if has_band_data and ('leave' in content.lower() or 'wfh' in content.lower()):
            formatted_lines.append("**Policy Summary by Band:**")
            
            import re
            
            for band_num in range(1, 6):
                band = f'L{band_num}'
                pattern = rf'{band}[^\w]*(\d+)'
                match = re.search(pattern, content)
                if match:
                    days = match.group(1)
                    
                    wfh_info = ""
                    if 'unlimited' in content.lower() and band == 'L5':
                        wfh_info = "Unlimited leave, Full Flex WFH"
                    elif 'limited' in content.lower() and band == 'L1':
                        wfh_info = f"{days} days, Limited WFH"
                    elif 'partial' in content.lower() and band == 'L2':
                        wfh_info = f"{days} days, Partial WFH"
                    elif 'yes' in content.lower() and band in ['L3', 'L4']:
                        wfh_info = f"{days} days, Full WFH"
                    else:
                        wfh_info = f"{days} total leave days"
                    
                    formatted_lines.append(f"• **{band}:** {wfh_info}")
        
        elif '|' in content or 'matrix' in content.lower():
            for line in lines:
                line = line.strip()
                if not line or line.startswith('==='):
                    continue
                    
                if '|' in line:
                    parts = [part.strip() for part in line.split('|') if part.strip()]
                    if len(parts) > 1:
                        formatted_lines.append(" | ".join(parts))
                elif any(band in line.upper() for band in ['L1', 'L2', 'L3', 'L4', 'L5']):
                    formatted_lines.append(f"**{line}**")
                else:
                    formatted_lines.append(line)
        else:
            for line in lines:
                line = line.strip()
                if not line or line.startswith('===') or line.startswith('---'):
                    continue
                formatted_lines.append(line)
        
        result = '\n'.join(formatted_lines[:8])
        
        if len(result) > 400:
            result = result[:400] + "..."
        
        return result
    
    def _format_policy_content(self, content: str) -> str:
        """Format policy content for better readability"""
        
        content = re.sub(r'--- Page \d+ ---', '', content)
        content = re.sub(r'===.*?===', '', content)
        content = re.sub(r'\s+', ' ', content)
        content = content.strip()
        
        if len(content) > 200:
            content = content[:200] + "..."
        
        if '●' in content:
            content = content.replace('●', '\n  •')
        
        return content
    
    def _generate_suggestions(self, analysis: Dict[str, Any]) -> str:
        """Generate helpful follow-up questions"""
        
        suggestions = []
        
        if analysis['topic'] == 'leave_policy':
            suggestions.extend([
                "What are the WFH policies for different bands?",
                "How do I apply for leave?",
                "What are the different types of leave available?"
            ])
        elif analysis['topic'] == 'travel_policy':
            suggestions.extend([
                "What are the hotel booking guidelines?",
                "How do travel approvals work for different bands?",
                "What expenses are reimbursable during travel?"
            ])
        elif analysis['specific_band']:
            band = analysis['specific_band']
            suggestions.extend([
                f"What are the travel policies for {band} employees?",
                f"What are the leave entitlements for {band} band?",
                f"What work arrangements are available for {band}?"
            ])
        else:
            suggestions.extend([
                "What are the policies for L3 employees?",
                "Show me travel allowance information",
                "What are the leave policies for senior staff?"
            ])
        
        return "\n".join(f"  • {suggestion}" for suggestion in suggestions[:3])
    
    def _format_no_results_message(self, query: str) -> str:
        """Format message when no results are found"""
        
        return f"""❌ **No relevant policies found for:** '{query}'

💡 **Try asking about:**
  • Specific salary bands (L1, L2, L3, L4, L5)
  • Leave policies and entitlements
  • Travel allowances and policies
  • Work from home arrangements
  • Compensation information

**Example queries:**
  • "What are the leave policies for L3 employees?"
  • "Show me travel allowance for senior staff"
  • "What are the WFH policies for different bands?"
""" 