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
        

        if query_analysis['is_multi_band']:
            return self._format_multi_band_response(query, query_analysis, results)
        elif query_analysis['specific_band']:
            return self._format_band_specific_response(query, query_analysis, results)
        else:
            organized_results = self._organize_results(results, query_analysis)
            response = self._build_response(query, query_analysis, organized_results)
            return response
    
    def _analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze the user query to understand intent and context"""
        
        query_lower = query.lower()
        analysis = {
            'topic': None,
            'specific_band': None,
            'multiple_bands': None,
            'band_level': None,
            'is_general': True,
            'is_multi_band': False,
            'keywords': []
        }
        
        band_matches = re.findall(r'L[1-5]', query.upper())
        unique_bands = list(dict.fromkeys(band_matches))
        
        if len(unique_bands) > 1:
            analysis['multiple_bands'] = unique_bands
            analysis['is_multi_band'] = True
            analysis['is_general'] = False
            band_levels = [self.band_mapping.get(band, 'Unknown') for band in unique_bands]
            analysis['band_level'] = f"Multiple bands: {', '.join(unique_bands)}"
        elif len(unique_bands) == 1:
            analysis['specific_band'] = unique_bands[0]
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
    
    def _format_band_specific_response(self, query: str, analysis: Dict[str, Any], results: List[Dict[str, Any]]) -> str:
        """Format response specifically for a single band query"""
        band = analysis['specific_band']
        band_level = analysis['band_level']
        

        band_specific_results = []
        matrix_results = []
        context_results = []
        
        for result in results:
            content = result['content']
            
            if self._is_table_or_matrix(content):
                matrix_results.append(result)
            elif result.get('band_specific', False) or result.get('priority') == 'high':
                band_specific_results.append(result)
            else:
                context_results.append(result)
        
        response_parts = []
        
        response_parts.append(f"📋 **Complete Policy Information for {band} ({band_level}) Employees:**")
        

        if band_specific_results:
            response_parts.append(f"\n🎯 **{band} Specific Policies:**")
            for i, result in enumerate(band_specific_results[:4], 1):  # Focus on top 4 most relevant
                formatted_content = self._format_band_specific_content(result['content'], band)
                response_parts.append(f"\n**{i}.** {formatted_content}")
        

        if matrix_results:
            response_parts.append(f"\n📊 **{band} in Policy Matrix:**")
            band_matrix_info = self._extract_band_from_matrix(matrix_results, band)
            if band_matrix_info:
                response_parts.append(f"\n{band_matrix_info}")
            else:
                for result in matrix_results[:2]:
                    formatted_content = self._format_table_content_for_band(result['content'], band)
                    response_parts.append(f"\n{formatted_content}")
        

        if context_results and len(band_specific_results) < 3:
            response_parts.append(f"\n📋 **Additional Context:**")
            for i, result in enumerate(context_results[:2], 1):  # Limit context
                formatted_content = self._format_policy_content(result['content'])
                response_parts.append(f"\n**{i}.** {formatted_content}")
        

        suggestions = self._generate_band_specific_suggestions(band, analysis['topic'])
        if suggestions:
            response_parts.append(f"\n\n💡 **More about {band} employees:**\n{suggestions}")
        
        return "\n".join(response_parts)
    
    def _format_band_specific_content(self, content: str, band: str) -> str:
        """Format content to highlight band-specific information"""
        content = re.sub(r'--- Page \d+ ---', '', content)
        content = re.sub(r'===.*?===', '', content)
        content = re.sub(r'\s+', ' ', content)
        content = content.strip()
        

        band_pattern = rf'\b{band}\b'
        content = re.sub(band_pattern, f"**{band}**", content, flags=re.IGNORECASE)
        
        if len(content) > 300:
            content = content[:300] + "..."
        
        if '●' in content:
            content = content.replace('●', '\n  •')
        
        return content
    
    def _format_multi_band_response(self, query: str, analysis: Dict[str, Any], results: List[Dict[str, Any]]) -> str:
        """Format response for queries asking about multiple bands"""
        bands = analysis['multiple_bands']
        topic = analysis.get('topic', 'policy')
        
        response_parts = []
        

        bands_text = ', '.join(bands[:-1]) + f" and {bands[-1]}" if len(bands) > 2 else f"{bands[0]} and {bands[1]}"
        response_parts.append(f"📋 **Complete Policy Information for {bands_text} Employees:**")
        

        band_info_sections = []
        
        for band in bands:
            band_level = self.band_mapping.get(band, 'Unknown')
            
            band_results = self._filter_results_for_band(results, band)
            
            band_specific_results = []
            matrix_results = []
            
            for result in band_results:
                content = result['content']
                
                if self._is_table_or_matrix(content):
                    matrix_results.append(result)
                elif result.get('band_specific', False) or result.get('priority') == 'high':
                    band_specific_results.append(result)
            
            band_matrix_info = ""
            if matrix_results:
                band_matrix_info = self._extract_band_from_matrix(matrix_results, band)
            
            band_section = []
            band_section.append(f"\n## 🎯 **{band} ({band_level}) Employees:**")
            
            if band_matrix_info and 'Leave Days Allocation:' in band_matrix_info:
                band_section.append(band_matrix_info)
            else:
                band_section.append(f"\n📊 **{band} Policy Summary:**")
                if band_specific_results:
                    for i, result in enumerate(band_specific_results[:2], 1):
                        formatted_content = self._format_band_specific_content(result['content'], band)
                        band_section.append(f"\n**{i}.** {formatted_content}")
                else:
                    band_section.append(f"\n• Specific {band} policy information available in detailed documents")
            
            band_info_sections.append('\n'.join(band_section))
        
        response_parts.extend(band_info_sections)
        
        if topic == 'leave_policy':
            response_parts.append(self._generate_comparative_summary(bands, results))
        
        suggestions = self._generate_multi_band_suggestions(bands, topic)
        if suggestions:
            response_parts.append(f"\n\n💡 **More comparisons:**\n{suggestions}")
        
        return "\n".join(response_parts)
    
    def _filter_results_for_band(self, results: List[Dict[str, Any]], band: str) -> List[Dict[str, Any]]:
        """Filter results that are relevant to a specific band"""
        band_results = []
        
        for result in results:
            content = result['content'].upper()
            
            if (band in content or 
                self._is_table_or_matrix(result['content']) or
                any(keyword in result['content'].lower() for keyword in ['leave', 'policy', 'entitlement'])):
                band_results.append(result)
        
        return band_results
    
    def _generate_comparative_summary(self, bands: List[str], results: List[Dict[str, Any]]) -> str:
        """Generate a comparative summary for multiple bands"""
        summary_parts = ["\n📊 **Quick Comparison:**"]
        
        band_data = {}
        for band in bands:
            for result in results:
                if self._is_leave_matrix(result['content']) and band in result['content'].upper():
                    parsed = self._parse_leave_entitlement_matrix(result['content'], band)
                    if parsed and 'Total Annual Leave:' in parsed:
                        import re
                        total_match = re.search(r'Total Annual Leave:\*\* (\d+|\w+)', parsed)
                        wfh_match = re.search(r'WFH Eligibility:\*\* ([^•\n]+)', parsed)
                        
                        total_leave = total_match.group(1) if total_match else "Unknown"
                        wfh_status = wfh_match.group(1) if wfh_match else "Unknown"
                        
                        band_data[band] = {
                            'total_leave': total_leave,
                            'wfh_status': wfh_status
                        }
                        break
        

        if band_data:
            summary_parts.append("\n| Band | Total Leave | WFH Eligibility |")
            summary_parts.append("|------|-------------|-----------------|")
            
            for band in bands:
                if band in band_data:
                    data = band_data[band]
                    summary_parts.append(f"| **{band}** | {data['total_leave']} | {data['wfh_status']} |")
                else:
                    summary_parts.append(f"| **{band}** | Not found | Not found |")
        
        return '\n'.join(summary_parts)
    
    def _generate_multi_band_suggestions(self, bands: List[str], topic: str) -> str:
        """Generate suggestions for multi-band queries"""
        bands_text = ', '.join(bands[:-1]) + f" and {bands[-1]}" if len(bands) > 2 else f"{bands[0]} and {bands[1]}"
        
        suggestions = [
                            f"Compare travel allowances for {bands_text}",
                f"What are the per diem differences between {bands[0]} and {bands[1]}?",
            f"What are the differences between {bands[0]} and {bands[1]} benefits?",
            f"Show salary ranges for {bands_text}"
        ]
        
        if topic == 'leave_policy':
            suggestions = [
                f"Compare leave entitlements between {bands[0]} and {bands[1]}",
                f"What are the WFH differences for {bands_text}?",
                f"Show leave application process for {bands_text}"
            ]
        
        return "\n".join(f"  • {suggestion}" for suggestion in suggestions[:3])
    
    def _extract_band_from_matrix(self, matrix_results: List[Dict[str, Any]], band: str) -> str:
        """Extract specific band information from matrix/table content"""
        for result in matrix_results:
            content = result['content']
            

            if self._is_travel_matrix(content) and band in content.upper():
                parsed_result = self._parse_travel_entitlement_matrix(content, band)
                if parsed_result and 'Travel Policy Breakdown:' in parsed_result:
                    return parsed_result
            

            if self._is_leave_matrix(content) and band in content.upper():
                parsed_result = self._parse_leave_entitlement_matrix(content, band)
                if parsed_result and 'Leave Days Allocation:' in parsed_result:
                    return parsed_result
        

        for result in matrix_results:
            content = result['content']
            
            if self._is_travel_matrix(content) and band in content.upper():
                return self._parse_travel_entitlement_matrix(content, band)
            
            if self._is_leave_matrix(content) and band in content.upper():
                return self._parse_leave_entitlement_matrix(content, band)
            

            lines = content.split('\n')
            for i, line in enumerate(lines):
                if band in line.upper() and any(digit in line for digit in '0123456789'):
                    band_info = [f"**{band} Policy Details:**"]
                    band_info.append(f"• {line.strip()}")
                    return '\n'.join(band_info)
        
        return ""
    
    def _is_leave_matrix(self, content: str) -> bool:
        """Check if content contains the leave entitlement matrix"""
        content_lower = content.lower()
        

        matrix_indicators = [
            ('total leave', 'earned'),
            ('leave days', 'sick'),
            ('casual', 'wfh eligibility'),
            ('ban d', 'days'), 
        ]
        
        return any(
            indicator1 in content_lower and indicator2 in content_lower 
            for indicator1, indicator2 in matrix_indicators
        )
    
    def _parse_leave_entitlement_matrix(self, content: str, band: str) -> str:
        """Parse the leave entitlement matrix to extract specific band details"""
        import re
        
        lines = content.split('\n')
        

        if band == 'L5':
            for i, line in enumerate(lines):
                if 'L5' in line and 'unlimited' in line.lower():

                    l5_content = line
                    if i + 1 < len(lines) and 'approval' in lines[i + 1]:
                        l5_content += ' ' + lines[i + 1].strip()
                    

                    wfh_eligibility = "Full Flex"
                    wfo_match = re.search(r'(\d+[-–]\d+)\s*/?\s*week', l5_content, re.IGNORECASE)
                    wfo_minimum = wfo_match.group(1) + "/week (optional)" if wfo_match else "0–2/week (optional)"
                    
                    return f"""**🎯 {band} Leave Entitlement Breakdown:**

📊 **Leave Days Allocation:**
• **Total Annual Leave:** Unlimited (with approval)
• **Earned Leave (EL):** Not applicable
• **Sick Leave (SL):** Not applicable  
• **Casual Leave (CL):** Not applicable

🏠 **Work Arrangements:**
• **WFH Eligibility:** {wfh_eligibility}
• **WFO Minimum:** {wfo_minimum}

💡 **Key Points:**
• Executive level employees have unlimited leave with management approval
• Maximum flexibility in work arrangements
• Full remote work options available
• Leave resets annually on January 1st"""
        

        for line in lines:
            line_clean = ' '.join(line.split())
            
            if band in line.upper():
                
                band_split = line.upper().split(band.upper())
                if len(band_split) > 1:
                    numbers_part = band_split[1]
                    
                    leave_numbers = re.findall(r'\d+', numbers_part.split('Yes')[0].split('Limited')[0].split('Partial')[0])
                    

                    if len(leave_numbers) >= 4:
                        try:
                            total_days = int(leave_numbers[0])
                            earned_leave = int(leave_numbers[1]) 
                            sick_leave = int(leave_numbers[2])
                            casual_leave = int(leave_numbers[3])
                            

                            if "yes" in line.lower():
                                wfh_eligibility = "Yes (Full WFH available)"
                            elif "partial" in line.lower():
                                wfh_eligibility = "Partial (Hybrid work)"
                            elif "limited" in line.lower():
                                wfh_eligibility = "Limited"
                            else:
                                wfh_eligibility = "Unknown"
                            

                            wfo_match = re.search(r'(\d+(?:[-–]\d+)?)\s*/?\s*week', line, re.IGNORECASE)
                            wfo_minimum = wfo_match.group(1) + "/week" if wfo_match else "Not specified"
                            
                            return f"""**🎯 {band} Leave Entitlement Breakdown:**

📊 **Leave Days Allocation:**
• **Total Annual Leave:** {total_days} days
• **Earned Leave (EL):** {earned_leave} days  
• **Sick Leave (SL):** {sick_leave} days
• **Casual Leave (CL):** {casual_leave} days

🏠 **Work Arrangements:**
• **WFH Eligibility:** {wfh_eligibility}
• **WFO Minimum:** {wfo_minimum}

💡 **Key Points:**
• Earned Leave: For planned personal time, travel, rest (apply ≥3 days in advance)
• Sick Leave: For illness/medical emergencies (no prior approval needed)
• Casual Leave: For unforeseen situations (max 2 consecutive days)
• Leave resets annually on January 1st
• Unused leave can be carried forward (max 10 days)"""
                            
                        except (ValueError, IndexError):
                            continue
        

        for i, line in enumerate(lines):
            if band in line.upper() and any(char.isdigit() for char in line):
                context_lines = []
                

                if i > 0:
                    prev_line = lines[i-1].strip()
                    if any(term in prev_line.lower() for term in ['band', 'total', 'leave', 'days']):
                        context_lines.append(f"*{prev_line}*")
                
                context_lines.append(f"**{band}:** {line.strip()}")
                
                return f"**{band} Information:**\n" + '\n'.join(context_lines)
        
        return ""
    
    def _is_travel_matrix(self, content: str) -> bool:
        """Check if content contains the travel entitlement matrix"""
        content_lower = content.lower()
        
        travel_indicators = [
            ('travel', 'per diem'),
            ('hotel', 'flight'),
            ('domestic', 'international'),
            ('travel mode', 'approval'),
            ('per diem', 'hotel cap'),
            ('flight class', 'eligibility'),
            ('travel band', 'matrix'),
            ('allowance', 'reimbursement'),
            ('business', 'economy'),
            ('rs.', 'usd'),
            ('cap/night', 'approval required')
        ]
        
        return any(
            indicator1 in content_lower and indicator2 in content_lower 
            for indicator1, indicator2 in travel_indicators
        )
    
    def _parse_travel_entitlement_matrix(self, content: str, band: str) -> str:
        """Parse the travel entitlement matrix to extract specific band details from actual document content"""
        import re
        
        lines = content.split('\n')
        
        band_line = None
        for line in lines:
            if band in line.upper() and any(char.isdigit() for char in line):
                band_line = line
                break
        
        if not band_line:
            for i, line in enumerate(lines):
                if band in line.upper():
                    context_lines = []
                    
                    if i > 0:
                        prev_line = lines[i-1].strip()
                        if any(term in prev_line.lower() for term in ['band', 'travel', 'mode', 'cap']):
                            context_lines.append(f"*{prev_line}*")
                    
                    context_lines.append(f"**{band}:** {line.strip()}")
                    return f"**{band} Travel Information:**\n" + '\n'.join(context_lines)
            return ""
        
        travel_data = self._extract_travel_data_from_band_line(band_line, band, content)
        
        if travel_data:
            return self._format_travel_breakdown_from_data(band, travel_data)
        
        return f"**🎯 {band} Travel Policy:**\n\n{band_line.strip()}"
    
    def _extract_travel_data_from_band_line(self, band_line: str, band: str, full_content: str) -> Dict[str, str]:
        """Extract travel data by parsing the travel matrix structure systematically"""
        import re
        
        travel_data = {}
        
        matrix_data = self._parse_travel_matrix_structure(full_content, band)
        
        if matrix_data:
            return matrix_data
        
        line_lower = band_line.lower()
        
        rs_matches = re.findall(r'rs\.?\s*(\d{1,3}(?:,\d{3})*)', line_lower)
        usd_matches = re.findall(r'usd\s*(\d+)', line_lower)
        
        if rs_matches:
            travel_data['hotel_cap'] = f"Rs. {rs_matches[0]}"
        
        if usd_matches:
            travel_data['per_diem_intl'] = f"USD {usd_matches[0]}"
        
        if len(rs_matches) > 1:
            travel_data['per_diem_domestic'] = f"Rs. {rs_matches[1]}"
        
        return travel_data
    
    def _parse_travel_matrix_structure(self, content: str, band: str) -> Dict[str, str]:
        """Systematically parse the travel matrix to extract exact band data"""
        import re
        
        travel_data = {}
        
        row_pattern = rf'ROW \d+: {band} \|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)'
        row_match = re.search(row_pattern, content)
        
        if row_match:
            domestic_mode = row_match.group(1).strip()
            international = row_match.group(2).strip()  
            flight_class = row_match.group(3).strip()
            hotel_cap = row_match.group(4).strip()
            per_diem_domestic = row_match.group(5).strip()
            per_diem_intl = row_match.group(6).strip()
            approval = row_match.group(7).strip()
            
            travel_data = {
                'domestic_mode': domestic_mode,
                'international': international,
                'flight_class': flight_class,
                'hotel_cap': hotel_cap,
                'per_diem_domestic': per_diem_domestic,
                'per_diem_intl': per_diem_intl,
                'approval': approval
            }
            
            return travel_data
        
        lines = content.split('\n')
        for line in lines:
            if f'{band} |' in line and any(char.isdigit() for char in line):
                parts = [part.strip() for part in line.split('|')]
                
                if len(parts) >= 8:  
                    travel_data = {
                        'domestic_mode': parts[1],
                        'international': parts[2], 
                        'flight_class': parts[3],
                        'hotel_cap': parts[4],
                        'per_diem_domestic': parts[5],
                        'per_diem_intl': parts[6],
                        'approval': parts[7]
                    }
                    return travel_data
            
            elif band in line and any(char.isdigit() for char in line):
                current_index = lines.index(line)
                full_line = line
                
                for next_offset in range(1, 3):
                    if current_index + next_offset < len(lines):
                        next_line = lines[current_index + next_offset].strip()
                        if (not any(f'L{i}' in next_line for i in range(1, 6)) and 
                            next_line and 
                            any(word in next_line.lower() for word in ['economy', 'business', 'justified', 'approval'])):
                            full_line += ' ' + next_line
                
                parts = full_line.split()
                
                try:
                    band_index = parts.index(band)
                    
                    
                    rs_indices = [i for i, part in enumerate(parts) if part.startswith('Rs.')]
                    usd_indices = [i for i, part in enumerate(parts) if part.startswith('USD')]
                    
                    if rs_indices and usd_indices:
                        first_rs = rs_indices[0]
                        
                        content_parts = parts[band_index+1:first_rs]
                        
                        if len(content_parts) >= 3:
                            intl_keywords = ['standard', 'permitted', 'approval', 'director', 'vp']
                            intl_index = None
                            
                            for i, part in enumerate(content_parts):
                                if part.lower() in intl_keywords:
                                    intl_index = i
                                    break
                            
                            if intl_index is not None:
                                domestic_mode = ' '.join(content_parts[:intl_index])
                                international = content_parts[intl_index]
                                flight_class = ' '.join(content_parts[intl_index+1:])
                            else:
                                domestic_mode = ' '.join(content_parts[:2])
                                international = content_parts[2] if len(content_parts) > 2 else ''
                                flight_class = ' '.join(content_parts[3:]) if len(content_parts) > 3 else ''
                        else:
                            domestic_mode = ' '.join(content_parts)
                            international = ''
                            flight_class = ''
                        
                        hotel_cap = f"{parts[rs_indices[0]]} {parts[rs_indices[0] + 1]}" if rs_indices and rs_indices[0] + 1 < len(parts) else ''
                        per_diem_domestic = f"{parts[rs_indices[1]]} {parts[rs_indices[1] + 1]}" if len(rs_indices) > 1 and rs_indices[1] + 1 < len(parts) else ''
                        per_diem_intl = f"{parts[usd_indices[0]]} {parts[usd_indices[0] + 1]}" if usd_indices and usd_indices[0] + 1 < len(parts) else ''
                        
                        approval_start = usd_indices[0] + 2 if usd_indices and usd_indices[0] + 2 < len(parts) else len(parts)
                        approval_parts = parts[approval_start:]
                        
                        approval_filtered = []
                        for part in approval_parts:
                            if part.lower() in ['economy', '(justified)', 'business']:
                                break
                            approval_filtered.append(part)
                        
                        approval = ' '.join(approval_filtered) if approval_filtered else ''
                        
                        travel_data = {
                            'domestic_mode': domestic_mode.strip(),
                            'international': international.strip(),
                            'flight_class': flight_class.strip(),
                            'hotel_cap': hotel_cap,
                            'per_diem_domestic': per_diem_domestic,
                            'per_diem_intl': per_diem_intl,
                            'approval': approval.strip()
                        }
                        return travel_data
                        
                except (ValueError, IndexError):
                    continue
        
        lines = content.split('\n')
        
        header_line = None
        header_index = -1
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if ('band' in line_lower and 
                any(col in line_lower for col in ['travel mode', 'flight class', 'hotel cap', 'per diem', 'approval'])):
                header_line = line
                header_index = i
                break
        
        if not header_line:
            return travel_data
        
        header_columns = self._parse_matrix_columns(header_line)
        
        band_line = None
        for i in range(header_index + 1, len(lines)):
            if band in lines[i].upper() and any(char.isdigit() for char in lines[i]):
                band_line = lines[i]
                break
        
        if not band_line:
            return travel_data
        
        band_values = self._parse_matrix_columns(band_line)
        
        for i, (header_col, band_val) in enumerate(zip(header_columns, band_values)):
            header_lower = header_col.lower()
            
            if 'flight class' in header_lower or 'flight' in header_lower:
                travel_data['flight_class'] = band_val.strip()
            elif 'travel mode' in header_lower or ('domestic' in header_lower and 'mode' in header_lower):
                travel_data['domestic_mode'] = band_val.strip()
            elif 'international' in header_lower and 'eligibility' in header_lower:
                travel_data['international'] = band_val.strip()
            elif 'hotel cap' in header_lower or ('hotel' in header_lower and 'cap' in header_lower):
                travel_data['hotel_cap'] = band_val.strip()
            elif 'per diem' in header_lower and 'domestic' in header_lower:
                travel_data['per_diem_domestic'] = band_val.strip()
            elif 'per diem' in header_lower and ('intl' in header_lower or 'international' in header_lower):
                travel_data['per_diem_intl'] = band_val.strip()
            elif 'approval' in header_lower and 'required' in header_lower:
                travel_data['approval'] = band_val.strip()
        
        return travel_data
    
    def _parse_matrix_columns(self, line: str) -> List[str]:
        """Parse a matrix line into columns, handling various separators"""
        import re
        
        
        if '|' in line:
            columns = [col.strip() for col in line.split('|') if col.strip()]
            return columns
        
        
        columns = re.split(r'\s{3,}', line.strip())
        columns = [col.strip() for col in columns if col.strip()]
        
        if len(columns) > 1:
            return columns
        
        
        if '\t' in line:
            columns = [col.strip() for col in line.split('\t') if col.strip()]
            return columns
        
        
        tokens = re.findall(r'\S+(?:\s+\S+)*?(?=\s*(?:[A-Z][a-z]|Rs\.|USD|\d|\||$))', line)
        if len(tokens) > 1:
            return [token.strip() for token in tokens]
        
        return [line.strip()] if line.strip() else []
    
    def _format_travel_breakdown_from_data(self, band: str, travel_data: Dict[str, str]) -> str:
        """Format travel breakdown using extracted data from documents"""
        
        
        breakdown_parts = [f"**🎯 {band} Travel Policy Breakdown:**", ""]
        
        if any(key in travel_data for key in ['domestic_mode', 'international', 'flight_class', 'hotel_cap', 'per_diem_domestic', 'per_diem_intl']):
            breakdown_parts.append("✈️ **Travel Entitlements:**")
            
            if 'domestic_mode' in travel_data:
                breakdown_parts.append(f"• **Domestic Travel:** {travel_data['domestic_mode']}")
            
            if 'international' in travel_data:
                breakdown_parts.append(f"• **International Travel:** {travel_data['international']}")
            
            if 'flight_class' in travel_data:
                breakdown_parts.append(f"• **Flight Class:** {travel_data['flight_class']}")
            
            if 'hotel_cap' in travel_data:
                breakdown_parts.append(f"• **Hotel Cap:** {travel_data['hotel_cap']}/night")
            
            if 'per_diem_domestic' in travel_data:
                breakdown_parts.append(f"• **Per Diem (Domestic):** {travel_data['per_diem_domestic']}/day")
            
            if 'per_diem_intl' in travel_data:
                breakdown_parts.append(f"• **Per Diem (International):** {travel_data['per_diem_intl']}/day")
            
            breakdown_parts.append("")
        
        if 'approval' in travel_data:
            breakdown_parts.extend([
                "📋 **Approval Process:**",
                f"• **Approval Required:** {travel_data['approval']}",
                "• **Booking:** Via designated platform",
                ""
            ])
        
        breakdown_parts.extend([
            "💡 **Important Notes:**",
            "• All travel details are as per company policy documents",
            "• Refer to the travel policy for complete terms and conditions"
        ])
        
        return "\n".join(breakdown_parts)
    
    def _format_table_content_for_band(self, content: str, band: str) -> str:
        """Format table content with emphasis on the specific band"""
        lines = content.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('===') or line.startswith('---'):
                continue
            

            if band in line.upper():
                formatted_lines.append(f"**➤ {line}** ← *Your band*")
            elif any(other_band in line.upper() for other_band in ['L1', 'L2', 'L3', 'L4', 'L5']):
                formatted_lines.append(f"  {line}")
            else:
                formatted_lines.append(line)
        
        result = '\n'.join(formatted_lines[:10]) 
        
        if len(result) > 500:
            result = result[:500] + "..."
        
        return result
    
    def _generate_band_specific_suggestions(self, band: str, topic: str) -> str:
        """Generate suggestions specific to the requested band"""
        suggestions = [
            f"What are the travel policies for {band} employees?",
            f"Show me work arrangements for {band} band",
            f"What benefits do {band} employees get?"
        ]
        
        if topic == 'leave_policy':
            suggestions = [
                f"How many leave days do {band} employees get?",
                f"What are the WFH options for {band}?",
                f"Can {band} employees carry forward leave?"
            ]
        elif topic == 'travel_policy':
            suggestions = [
                f"What's the per diem allowance for {band} employees?",
                f"What flight class is {band} eligible for?",
                f"What hotel budget limit does {band} have?",
                f"Do {band} employees need approval for international travel?",
                f"What travel reimbursements are available for {band}?"
            ]
        
        return "\n".join(f"  • {suggestion}" for suggestion in suggestions[:3])
    
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
        
        if has_band_data and ('travel' in content.lower() or 'per diem' in content.lower() or 'hotel' in content.lower()):
            formatted_lines.append("**Travel Policy Summary by Band:**")
            

            for band_num in range(1, 6):
                band = f'L{band_num}'
                if band in content.upper():
                    travel_info = self._extract_travel_info_from_line(content, band)
                    if travel_info:
                        formatted_lines.append(f"• **{band}:** {travel_info}")
        
        elif has_band_data and ('leave' in content.lower() or 'wfh' in content.lower()):
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
    
    def _extract_travel_info_from_line(self, content: str, band: str) -> str:
        """Extract travel information for a specific band from content"""
        lines = content.split('\n')
        
        for line in lines:
            if band in line.upper():

                if 'rs.' in line.lower() and 'usd' in line.lower():

                    import re
                    rs_matches = re.findall(r'Rs\.?\s*(\d{1,3}(?:,\d{3})*)', line, re.IGNORECASE)
                    usd_matches = re.findall(r'USD\s*(\d+)', line, re.IGNORECASE)
                    
                    if rs_matches and usd_matches:
                        return f"Hotel: Rs. {rs_matches[0]}/night, Per Diem: USD {usd_matches[0]}/day"
                

                elif 'economy' in line.lower() or 'business' in line.lower():
                    if 'business' in line.lower():
                        return "Business class flights, Premium allowances"
                    else:
                        return "Economy class flights, Standard allowances"
                

                elif any(char.isdigit() for char in line):
                    clean_line = ' '.join(line.split())
                    if len(clean_line) > 50:
                        clean_line = clean_line[:50] + "..."
                    return clean_line.replace(band, "").strip()
        
        return ""
    
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
                "What are the per diem rates for different bands?",
                "How do travel approvals work for different bands?",
                "What are the hotel booking limits by band?",
                "Show me flight class eligibility for senior bands",
                "What travel expenses are reimbursable?"
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