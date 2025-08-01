import google.generativeai as genai
from typing import List, Dict, Any, Optional
import logging
from config import settings
import os
from dataclasses import dataclass

@dataclass
class GenerationConfig:
    temperature: float = 0.7
    max_output_tokens: int = 2048
    top_p: float = 0.95
    top_k: int = 64

class GeminiClient:
    """
    Enhanced Gemini API client with context management
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.generation_config = GenerationConfig(
            temperature=settings.gemini_temperature,
            max_output_tokens=settings.gemini_max_tokens
        )
        self._setup_client()
    
    def _setup_client(self):
        """Initialize Gemini client"""
        try:
            genai.configure(api_key=settings.gemini_api_key)
            
            self.model = genai.GenerativeModel(
                model_name=settings.gemini_model,
                generation_config={
                    "temperature": self.generation_config.temperature,
                    "max_output_tokens": self.generation_config.max_output_tokens,
                    "top_p": self.generation_config.top_p,
                    "top_k": self.generation_config.top_k,
                }
            )
            
            self.logger.info("Gemini client initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Gemini client: {str(e)}")
            raise
    
    def generate_offer_letter(self, 
                            employee_context: Dict,
                            policy_context: str,
                            template_context: str) -> str:
        """
        Generate personalized offer letter using Gemini REST API
        
        Args:
            employee_context: Employee details and benefits
            policy_context: Relevant HR policies
            template_context: Offer letter template structure
            
        Returns:
            Generated offer letter content
        """
        
        prompt = self._build_offer_letter_prompt(
            employee_context, policy_context, template_context
        )
        
        try:
            import requests
            import json
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"
            
            headers = {
                'Content-Type': 'application/json',
                'X-goog-api-key': settings.gemini_api_key
            }
            
            data = {
                'contents': [{
                    'parts': [{
                        'text': prompt
                    }]
                }],
                'generationConfig': {
                    'temperature': self.generation_config.temperature,
                    'maxOutputTokens': self.generation_config.max_output_tokens,
                    'topP': self.generation_config.top_p,
                    'topK': self.generation_config.top_k
                }
            }
            
            self.logger.info("Making Gemini REST API request...")
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                if 'candidates' in result and result['candidates']:
                    candidate = result['candidates'][0]
                    if 'content' in candidate and 'parts' in candidate['content']:
                        text = candidate['content']['parts'][0]['text']
                        self.logger.info("Offer letter generated successfully via REST API")
                        return text.strip()
                
                raise Exception("Invalid response structure from Gemini API")
                
            else:
                error_text = response.text
                self.logger.error(f"Gemini API error {response.status_code}: {error_text}")
                raise Exception(f"Gemini API returned {response.status_code}: {error_text}")
                
        except Exception as e:
            self.logger.error(f"Error generating offer letter: {str(e)}")
            raise
    
    def _build_offer_letter_prompt(self, 
                                 employee_context: Dict,
                                 policy_context: str,
                                 template_context: str) -> str:
        """Build comprehensive prompt for offer letter generation"""
        
        employee = employee_context['employee']
        band_info = employee_context['salary_band_info']
        
        leave_days = band_info.get('leave_days')
        travel_allowance = band_info.get('travel_allowance')
        
        leave_info = f"{leave_days} days per year" if leave_days is not None else "Policy information not available"
        travel_info = travel_allowance if travel_allowance is not None else "Policy information not available"
        
        prompt = f"""
You are an expert HR professional generating a personalized job offer letter. 

**EMPLOYEE INFORMATION:**
- Name: {employee['name']}
- Position: {employee['position']}
- Department: {employee['department']}
- Team: {employee['team']}
- Salary Band: {employee['salary_band']} ({band_info.get('level', 'Standard')})
- Base Salary: ₹{employee['base_salary']:,.2f} per annum
- Joining Date: {employee['joining_date']}
- Employee ID: {employee['employee_id']}

**COMPENSATION & POLICIES:**
- Base Salary: ₹{employee['base_salary']:,.2f} per annum
- Leave Days: {leave_info}
- Travel Allowance Category: {travel_info}

**HR POLICIES CONTEXT:**
{policy_context}

**TEMPLATE REFERENCE:**
{template_context}

**INSTRUCTIONS:**
1. Create a professional, personalized offer letter
2. Include all relevant compensation details
3. Reference specific HR policies that apply to this employee's salary band
4. Use formal business letter format with proper date, addresses, and signatures
5. Ensure all financial figures are accurate and clearly stated
6. Include relevant policy excerpts for leave, travel, and work arrangements
7. Make it warm yet professional in tone
8. Ensure compliance with labor laws and company policies
9. If policy information is not available, focus on the base salary and general company policies

**OUTPUT FORMAT:**
Generate a complete offer letter in proper business format, including:
- Company letterhead placeholder
- Date and addresses  
- Formal salutation
- Position details and reporting structure
- Compensation breakdown
- Policy references
- Terms and conditions
- Signature blocks

Please generate the complete offer letter now:
"""
        
        return prompt
    
    def test_connection(self) -> bool:
        """Test if Gemini API connection is working"""
        try:
            #api was tested via curl and confirmed working, so skipping the test
            response = self.model.generate_content("Hello, this is a test. Please respond with 'Connection successful'.")
            return response.text and "successful" in response.text.lower()
            
            self.logger.info("Gemini connection test skipped (API confirmed working)")
            return True
            
        except Exception as e:
            self.logger.error(f"Connection test failed: {str(e)}")
            return False
    
    def generate_summary(self, content: str, max_length: int = 500) -> str:
        """Generate summary of document content"""
        prompt = f"""
        Please provide a concise summary of the following content in {max_length} characters or less:
        
        {content}
        
        Summary:
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip() if response.text else ""
        except Exception as e:
            self.logger.error(f"Error generating summary: {str(e)}")
            return ""