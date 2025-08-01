import pandas as pd
from typing import Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass
import logging
from config import settings

@dataclass
class Employee:
    name: str
    position: str
    department: str
    team: str
    salary_band: str
    base_salary: float
    joining_date: str
    employee_id: str

class EmployeeManager:
    """
    Manages employee data and extracts salary band logic from HR policy documents
    """
    
    def __init__(self, csv_path: str = None, vector_store=None):
        self.csv_path = csv_path or f"{settings.assets_path}/Employee_List.csv"
        self.vector_store = vector_store
        self.logger = logging.getLogger(__name__)
        self.employees: Dict[str, Employee] = {}
        self.salary_bands = {}
        self._load_employees()
        self._extract_salary_bands_from_policies()
    
    def _load_employees(self):
        """Load employee data from CSV file"""
        try:
            df = pd.read_csv(self.csv_path)
            
            for _, row in df.iterrows():
                employee = Employee(
                    name=row.get('Employee Name', '').strip(),
                    position=row.get('Department', '').strip(),  
                    department=row.get('Department', '').strip(),
                    team=row.get('Location', '').strip(),  # using location as team
                    salary_band=row.get('Band', '').strip(),
                    base_salary=float(row.get('Base Salary (INR)', 0)),
                    joining_date=row.get('Joining Date', '').strip(),
                    employee_id=f"EMP_{len(self.employees)+1:03d}"  # generating employee ID
                )
                
                self.employees[employee.name.lower()] = employee
            
            self.logger.info(f"Loaded {len(self.employees)} employees from {self.csv_path}")
            
        except Exception as e:
            self.logger.error(f"Error loading employee data: {str(e)}")
            raise
    
    def _extract_salary_bands_from_policies(self):
        """Extract salary band information from chunked HR policy documents"""
        if not self.vector_store:
            self.logger.warning("No vector store provided, cannot extract salary band information")
            return
            
        try:

            salary_bands_info = {}
            
            for band in ['L1', 'L2', 'L3', 'L4', 'L5']:
                band_info = self._extract_band_policies(band)
                if band_info:
                    salary_bands_info[band] = band_info
                    
            if salary_bands_info:
                self.salary_bands = salary_bands_info
                self.logger.info(f"Successfully extracted salary band information for {len(salary_bands_info)} bands from policy documents")
            else:
                self.logger.warning("No salary band information found in policy documents")
                
        except Exception as e:
            self.logger.error(f"Error extracting salary bands from policies: {str(e)}")
    
    def _extract_band_policies(self, band: str) -> Dict:
        """Extract policy information for a specific salary band"""
        try:
            leave_results = self.vector_store.similarity_search(
                f"{band} leave entitlement days earned sick casual annual",
                n_results=3,
                document_types=['hr_policy'],
                min_similarity=0.1
            )
            
            travel_results = self.vector_store.similarity_search(
                f"{band} travel allowance per diem accommodation flight domestic international",
                n_results=3,
                document_types=['hr_policy', 'travel_policy'],
                min_similarity=0.1
            )
            
            band_info = {
                'level': self._extract_level_from_results(band, leave_results + travel_results),
                'leave_days': self._extract_leave_days(band, leave_results),
                'travel_allowance': self._extract_travel_allowance(band, travel_results),
                'raw_policy_chunks': {
                    'leave': [r.get('content', '') for r in leave_results[:2]],
                    'travel': [r.get('content', '') for r in travel_results[:2]]
                }
            }
            
            return band_info
            
        except Exception as e:
            self.logger.error(f"Error extracting policies for band {band}: {str(e)}")
            return None
    
    def _extract_level_from_results(self, band: str, results: List[Dict]) -> str:
        """Extract job level description from search results"""
        level_mapping = {
            'L1': 'Junior',
            'L2': 'Mid-level', 
            'L3': 'Senior',
            'L4': 'Lead',
            'L5': 'Executive'
        }
        
        for result in results:
            content = result.get('content', '').lower()
            if 'junior' in content and band == 'L1':
                return 'Junior'
            elif 'senior' in content and band == 'L3':
                return 'Senior'
            elif 'lead' in content and band == 'L4':
                return 'Lead'
            elif 'executive' in content and band == 'L5':
                return 'Executive'
        
        return level_mapping.get(band, 'Unknown')
    
    def _extract_leave_days(self, band: str, results: List[Dict]) -> int:
        """Extract leave days from search results"""
        import re
        
        for result in results:
            content = result.get('content', '')
            
            day_patterns = [
                rf'Ban d:\s*{band}\s*\|\s*Total Leave Days:\s*(\d+)',
                rf'ROW\s+\d+\s+DETAILS:.*?Ban d:\s*{band}\s*\|\s*Total Leave Days:\s*(\d+)',
                rf'{band}\s*\|\s*(\d+)\s*\|',
                rf'^\s*{band}\s+(\d+)\s+\d+\s+\d+',
                rf'^\s*{band}\s+(\d+)',
                rf'{band}[:\s]*(\d+)\s*days?',
                rf'(\d+)\s*days?[^0-9]*{band}'
            ]
            
            for pattern in day_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
                if matches:
                    for match in matches:
                        try:
                            days = int(match)
                            if 5 <= days <= 50:
                                self.logger.info(f"Extracted {days} leave days for {band} using pattern: {pattern}")
                                return days
                        except ValueError:
                            continue
        
        for result in results:
            content = result.get('content', '')
            if band == 'L5' and 'unlimited' in content.lower():
                self.logger.info(f"Found unlimited leave for {band}")
                return 999  # special value for unlimited
        
        self.logger.warning(f"No leave days found for {band} in policy documents")
        return None
    
    def _extract_travel_allowance(self, band: str, results: List[Dict]) -> str:
        """Extract travel allowance category from search results"""
        import re
        
        for result in results:
            content = result.get('content', '')
            
            band_row_patterns = [
                rf'{band}.*?Economy.*?Rs\.?\s*(\d+)',  # "L1 ... Economy Rs. 2000"
                rf'{band}.*?Business.*?Rs\.?\s*(\d+)', # "L2 ... Business Rs. 3000"
                rf'{band}.*?(\w+)\s+Class',            # "L3 ... Premium Class"
                rf'{band}.*?(\w+)\s+Rs\.\s*\d+'        # "L4 Executive Rs. 5000"
            ]
            
            for pattern in band_row_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    context = match.group(0).lower()
                    if 'economy' in context or '2000' in context:
                        return 'Standard'
                    elif 'business' in context or '3000' in context:
                        return 'Enhanced'
                    elif 'premium' in context or '4000' in context:
                        return 'Premium'
                    elif 'executive' in context or '5000' in context:
                        return 'Executive'
        
        allowance_keywords = {
            'standard': ['standard', 'basic', 'regular', 'economy', '2000'],
            'enhanced': ['enhanced', 'improved', 'better', 'business', '3000'],
            'premium': ['premium', 'senior', 'advanced', '4000'],
            'executive': ['executive', 'lead', 'management', '5000'],
            'executive plus': ['executive plus', 'top tier', 'highest', '6000']
        }
        
        for result in results:
            content = result.get('content', '').lower()
            for allowance_type, keywords in allowance_keywords.items():
                if any(keyword in content for keyword in keywords):
                    self.logger.info(f"Extracted travel allowance '{allowance_type}' for {band}")
                    return allowance_type.title()
        
        self.logger.warning(f"No travel allowance found for {band} in policy documents")
        return None
    
    def find_employee(self, name: str) -> Optional[Employee]:
        """Find employee by name (case-insensitive)"""
        return self.employees.get(name.lower())
    
    def get_employee_context(self, employee_name: str) -> Dict:
        """
        Get comprehensive employee context for offer letter generation
        
        Args:
            employee_name: Name of the employee
            
        Returns:
            Dict with employee details and applicable policies
        """
        employee = self.find_employee(employee_name)
        
        if not employee:
            raise ValueError(f"Employee '{employee_name}' not found")
        
        band_info = self.salary_bands.get(employee.salary_band, {})
        
        context = {
            'employee': {
                'name': employee.name,
                'position': employee.position,
                'department': employee.department,
                'team': employee.team,
                'salary_band': employee.salary_band,
                'base_salary': employee.base_salary,
                'joining_date': employee.joining_date,
                'employee_id': employee.employee_id
            },
            'salary_band_info': band_info,
            'policies_applicable': self._get_applicable_policies(employee)
        }
        
        return context
    
    def _get_applicable_policies(self, employee: Employee) -> Dict:
        """Determine which policies apply to this employee"""
        return {
            'leave_policy': True,
            'travel_policy': True,
            'wfh_policy': employee.salary_band in ['L2', 'L3', 'L4', 'L5'],
            'flexible_hours': employee.salary_band in ['L3', 'L4', 'L5']
        }
    
    def list_all_employees(self) -> List[str]:
        """Get list of all employee names"""
        return list(self.employees.keys())
    
    def get_employees_by_band(self, salary_band: str) -> List[Employee]:
        """Get all employees in a specific salary band"""
        return [emp for emp in self.employees.values() 
                if emp.salary_band == salary_band]