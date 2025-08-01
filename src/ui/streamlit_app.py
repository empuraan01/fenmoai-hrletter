
try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:

    pass

import streamlit as st
import os
import sys
import logging
from datetime import datetime
from pathlib import Path
import re
from dotenv import load_dotenv

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment
load_dotenv()

# Import RAG components
from src.agent import RAGEngine
from src.data import EmployeeManager
from src.utils.document_generator import DocumentGenerator

# Configure page
st.set_page_config(
    page_title="FenmoAI - Offer Letter Generator",
    page_icon="🤖",
    layout="wide"
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "rag_engine" not in st.session_state:
    st.session_state.rag_engine = None
if "system_initialized" not in st.session_state:
    st.session_state.system_initialized = False

def initialize_system():
    """Initialize the RAG system"""
    try:
        with st.spinner("🚀 Initializing FenmoAI System..."):
            # Initialize full RAG engine
            try:
                rag_engine = RAGEngine()
            except Exception as e:
                st.error(f"❌ Failed to initialize system: {str(e)}")
                st.info("Please check your configuration and try refreshing the page.")
                return False
            
            # Test Gemini availability for offer letter generation
            try:
                gemini_available = rag_engine.gemini_client.test_connection()
            except Exception as e:
                st.warning(f"⚠️ Gemini API issue: {str(e)}")
                gemini_available = False
            
            if not gemini_available:
                st.info("🔍 **Policy search is fully functional!**")
            
            # Check system status
            status = rag_engine.get_system_status()
            
            # Process documents if needed
            if status['vector_store']['total_documents'] == 0:
                with st.spinner("📄 Processing HR documents..."):
                    processing_result = rag_engine.process_and_store_documents()
                    if processing_result.get('errors'):
                        st.error(f"Document processing errors: {processing_result['errors']}")
                    else:
                        st.success(f"✅ Processed {processing_result['total_chunks']} document chunks")
            
            st.session_state.rag_engine = rag_engine
            st.session_state.gemini_available = gemini_available
            st.session_state.system_initialized = True
            
            # Add welcome message
            welcome_content = f"""👋 **Welcome to FenmoAI HR Assistant!**

🎯 **What I can do:**
- Search HR policies and procedures intelligently
- Answer questions about compensation and policies  
- Show employee information and salary bands"""
            
            if gemini_available:
                welcome_content += f"""
- Generate personalized offer letters for employees

💬 **Try asking me:**
- "Generate offer letter for Martha Bennett"
- "What are the leave policies for L3 employees?"
- "Show me travel allowance for senior staff"
- "What are the WFH policies for different bands?"

📊 **System Status:**
- 📄 Documents: {status['vector_store']['total_documents']} processed
- 👥 Employees: {status['employee_count']} loaded
- 🤖 AI Model: {status['embedding_model']['model_name']}
- ✅ Fully operational!"""
            else:
                welcome_content += f"""

💬 **Try asking me:**
- "What are the leave policies for L3 employees?"
- "Show me travel allowance for senior staff"
- "What are the WFH policies for different bands?"
- "What policies apply to L5 employees?"

📊 **System Status:**
- 📄 Documents: {status['vector_store']['total_documents']} processed
- 👥 Employees: {status['employee_count']} loaded  
- 🤖 Search Model: {status['embedding_model']['model_name']}
- ⚠️ Offer letters unavailable (Gemini API issue)"""
            
            welcome_msg = {
                "role": "assistant", 
                "content": welcome_content
            }
            st.session_state.messages.append(welcome_msg)
            
    except Exception as e:
        st.error(f"❌ Failed to initialize system: {str(e)}")
        st.info("💡 **Troubleshooting Tips:**\n- Check your internet connection\n- Verify .env file has GEMINI_API_KEY\n- Try refreshing the page")
        return False
    
    return True

def create_download_buttons(offer_letter_text: str, employee_name: str, key_prefix: str):
    """Create download buttons for different file formats"""
    doc_generator = DocumentGenerator()
    available_formats = doc_generator.get_available_formats()
    
    # Create columns for different download options
    cols = st.columns(len([fmt for fmt, available in available_formats.items() if available]))
    col_idx = 0
    
    # TXT format (always available)
    with cols[col_idx]:
        if st.download_button(
            "📄 Download TXT",
            data=offer_letter_text,
            file_name=f"offer_letter_{employee_name.replace(' ', '_')}.txt",
            mime="text/plain",
            key=f"{key_prefix}_txt"
        ):
            st.success("✅ TXT Downloaded!")
    col_idx += 1
    
    # PDF format
    if available_formats['pdf']:
        with cols[col_idx]:
            try:
                pdf_data = doc_generator.generate_pdf(offer_letter_text, employee_name)
                if st.download_button(
                    "📋 Download PDF",
                    data=pdf_data,
                    file_name=f"offer_letter_{employee_name.replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    key=f"{key_prefix}_pdf"
                ):
                    st.success("✅ PDF Downloaded!")
            except Exception as e:
                st.error(f"PDF generation error: {str(e)}")
        col_idx += 1
    
    # DOCX format
    if available_formats['docx']:
        with cols[col_idx]:
            try:
                docx_data = doc_generator.generate_docx(offer_letter_text, employee_name)
                if st.download_button(
                    "📝 Download DOCX",
                    data=docx_data,
                    file_name=f"offer_letter_{employee_name.replace(' ', '_')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"{key_prefix}_docx"
                ):
                    st.success("✅ DOCX Downloaded!")
            except Exception as e:
                st.error(f"DOCX generation error: {str(e)}")

def extract_employee_name(user_input):
    """Extract employee name from user input"""
    # Common patterns for requesting offer letters or employee info
    patterns = [
        r"generate.*offer.*letter.*for\s+([a-zA-Z\s]+)",
        r"create.*offer.*letter.*for\s+([a-zA-Z\s]+)", 
        r"offer.*letter.*for\s+([a-zA-Z\s]+)",
        r"generate.*for\s+([a-zA-Z\s]+)",
        r"create.*for\s+([a-zA-Z\s]+)",
        r"show.*information.*for\s+([a-zA-Z\s]+)",
        r"info.*for\s+([a-zA-Z\s]+)",
        r"details.*for\s+([a-zA-Z\s]+)"
    ]
    
    user_input_lower = user_input.lower()
    
    for pattern in patterns:
        match = re.search(pattern, user_input_lower, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            # Clean up the name
            name = ' '.join(word.capitalize() for word in name.split())
            return name
    
    return None

def handle_user_query(query):
    """Handle user query and generate response"""
    try:
        rag_engine = st.session_state.rag_engine
        gemini_available = st.session_state.get('gemini_available', False)
        
        # Check if it's an offer letter request
        employee_name = extract_employee_name(query)
        
        if employee_name:
            if not gemini_available:
                # Show employee info but can't generate offer letter
                try:
                    employee = rag_engine.employee_manager.find_employee(employee_name)
                    if employee:
                        response = f"""⚠️ **Offer Letter Generation Unavailable**

👤 **Found Employee: {employee.name}**
- **Position:** {employee.position}
- **Department:** {employee.department}
- **Salary Band:** {employee.salary_band}
- **Base Salary:** ₹{employee.base_salary:,}
- **Joining Date:** {employee.joining_date}

❌ **Cannot generate offer letter** - Gemini AI is currently unavailable.

💡 **What you can do:**
- Ask about HR policies and compensation for this employee
- Search for policy information related to their salary band
- View detailed employee information

**Try asking:** "What are the policies for {employee.salary_band} employees?"
"""
                    else:
                        response = f"❌ Employee '{employee_name}' not found. Available employees: {', '.join(rag_engine.employee_manager.list_all_employees()[:5])}..."
                    
                    return {"content": response}
                except Exception as e:
                    return {"content": f"❌ Error looking up employee: {str(e)}"}
            else:
                # Generate offer letter (full mode)
                with st.spinner(f"🔍 Generating offer letter for {employee_name}..."):
                    try:
                        result = rag_engine.generate_offer_letter(employee_name)
                        
                        # Format response
                        employee_info = result['employee_context']['employee']
                        metadata = result['generation_metadata']
                        
                        response = f"""✅ **Offer Letter Generated for {employee_info['name']}**

👤 **Employee Details:**
- **Position:** {employee_info['position']}
- **Department:** {employee_info['department']}
- **Salary Band:** {employee_info['salary_band']}
- **Base Salary:** ₹{employee_info['base_salary']:,}

📋 **Generation Summary:**
- **Policies Used:** {metadata['policies_used']} policy types
- **Policy Chunks:** {metadata['total_policy_chunks']} relevant sections

---

📄 **OFFER LETTER:**

{result['offer_letter']}

---

💾 **Download:** Use the download button below to save this offer letter."""
                        
                        return {
                            "content": response,
                            "offer_letter": result['offer_letter'],
                            "employee_name": employee_info['name'],
                            "metadata": result
                        }
                        
                    except Exception as e:
                        return {
                            "content": f"❌ **Error generating offer letter for {employee_name}:**\n\n{str(e)}\n\n**Suggestions:**\n- Check if the employee name is spelled correctly\n- Try: 'Generate offer letter for Martha Bennett'"
                        }
        else:
            # Handle general queries (policy search)
            with st.spinner("🔍 Searching policies..."):
                search_results = rag_engine.search_policies(query)
                
                # Use the new response formatter
                from src.utils import ResponseFormatter
                formatter = ResponseFormatter()
                response = formatter.format_policy_search_results(query, search_results)
                
                # Add note about offer letter availability if needed
                if not gemini_available and search_results:
                    response += f"\n\n💡 **Note:** For offer letter generation, please ensure Gemini API is available."
                
                return {"content": response}
                
    except Exception as e:
        return {
            "content": f"❌ **Error processing your request:**\n\n{str(e)}\n\n**Please try again or contact support.**"
        }

def main():
    """Main Streamlit app"""
    
    # Header
    st.title("🤖 FenmoAI Offer Letter Generator")
    st.markdown("*Intelligent HR Assistant powered by RAG + Gemini AI*")
    
    # Initialize system
    if not st.session_state.system_initialized:
        if not initialize_system():
            st.stop()
    
    # Sidebar with employee list and stats
    with st.sidebar:
        st.header("📊 System Status")
        
        if st.session_state.rag_engine:
            status = st.session_state.rag_engine.get_system_status()
            
            st.metric("📄 Documents", status['vector_store']['total_documents'])
            st.metric("👥 Employees", status['employee_count'])
            st.metric("🤖 Gemini Status", "✅ Connected" if status['gemini_connected'] else "❌ Error")
            
            st.header("👥 Available Employees")
            employees = st.session_state.rag_engine.employee_manager.list_all_employees()
            
            # Employee list with expandable view
            gemini_available = st.session_state.get('gemini_available', False)
            
            # Show first 10 employees
            for emp_name in employees[:10]:
                employee = st.session_state.rag_engine.employee_manager.find_employee(emp_name)
                button_text = f"📝 {employee.name}" if gemini_available else f"👤 {employee.name}"
                
                if st.button(button_text, key=f"btn_{emp_name}"):
                    if gemini_available:
                        # Auto-generate offer letter query
                        query = f"Generate offer letter for {employee.name}"
                    else:
                        # Show employee info query
                        query = f"Show information for {employee.name}"
                    
                    st.session_state.messages.append({"role": "user", "content": query})
                    
                    # Process query
                    response = handle_user_query(query)
                    st.session_state.messages.append({"role": "assistant", **response})
                    st.rerun()
            
            # Show remaining employees in an expandable section
            if len(employees) > 10:
                remaining_employees = employees[10:]
                with st.expander(f"👥 Show {len(remaining_employees)} more employees"):
                    for emp_name in remaining_employees:
                        employee = st.session_state.rag_engine.employee_manager.find_employee(emp_name)
                        button_text = f"📝 {employee.name}" if gemini_available else f"👤 {employee.name}"
                        
                        if st.button(button_text, key=f"btn_more_{emp_name}"):
                            if gemini_available:
                                # Auto-generate offer letter query
                                query = f"Generate offer letter for {employee.name}"
                            else:
                                # Show employee info query
                                query = f"Show information for {employee.name}"
                            
                            st.session_state.messages.append({"role": "user", "content": query})
                            
                            # Process query
                            response = handle_user_query(query)
                            st.session_state.messages.append({"role": "assistant", **response})
                            st.rerun()
    
    # Chat interface
    st.header("💬 Chat with FenmoAI")
    
    # Display chat messages
    for msg_idx, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Add download buttons for offer letters
            if message["role"] == "assistant" and "offer_letter" in message:
                st.markdown("**💾 Download Options:**")
                create_download_buttons(
                    message["offer_letter"], 
                    message["employee_name"], 
                    f"download_history_{msg_idx}"
                )
    
    # Chat input
    if prompt := st.chat_input("Ask me to generate an offer letter or search policies..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate and display assistant response
        with st.chat_message("assistant"):
            response = handle_user_query(prompt)
            st.markdown(response["content"])
            
            # Add download buttons if offer letter generated
            if "offer_letter" in response:
                st.markdown("**💾 Download Options:**")
                create_download_buttons(
                    response["offer_letter"], 
                    response["employee_name"], 
                    "download_current"
                )
        
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", **response})

    # Footer
    st.markdown("---")
    st.markdown("**💡 Tips:** Try asking 'Generate offer letter for [Employee Name]' or search for policies!")
    st.markdown("**💾 Downloads:** Offer letters available in TXT, PDF, and DOCX formats!")

if __name__ == "__main__":
    main()
