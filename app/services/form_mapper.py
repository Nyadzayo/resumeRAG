"""
Form field mapping and standardization for ResumeRAG system.
Maps common form field labels to standardized queries for resume extraction.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class FieldType(Enum):
    """Types of form fields"""
    PERSONAL_INFO = "personal_info"
    CONTACT = "contact"
    EDUCATION = "education"
    EXPERIENCE = "experience"
    SKILLS = "skills"
    OTHER = "other"


@dataclass
class FormField:
    """Represents a form field with its mapping to resume data"""
    field_name: str
    field_type: FieldType
    extraction_query: str
    common_labels: List[str]
    example_values: List[str]
    required: bool = False


class FormFieldMapper:
    """Maps form field labels to standardized resume extraction queries"""
    
    def __init__(self):
        self.field_mappings = self._initialize_field_mappings()
        self.label_to_field = self._create_label_mapping()
    
    def _initialize_field_mappings(self) -> Dict[str, FormField]:
        """Initialize standard form field mappings"""
        return {
            # Personal Information
            "first_name": FormField(
                field_name="first_name",
                field_type=FieldType.PERSONAL_INFO,
                extraction_query="What is the person's first name or given name? Look for names at the beginning of the resume.",
                common_labels=[
                    "first name", "firstname", "given name", "name", 
                    "first", "forename", "christian name"
                ],
                example_values=["John", "Sarah", "Michael"],
                required=True
            ),
            "last_name": FormField(
                field_name="last_name",
                field_type=FieldType.PERSONAL_INFO,
                extraction_query="What is the person's last name, surname, or family name? Look for names at the beginning of the resume.",
                common_labels=[
                    "last name", "lastname", "surname", "family name",
                    "last", "family", "surname"
                ],
                example_values=["Smith", "Johnson", "Williams"],
                required=True
            ),
            "full_name": FormField(
                field_name="full_name",
                field_type=FieldType.PERSONAL_INFO,
                extraction_query="What is the person's full name? Look for the complete name at the top of the resume.",
                common_labels=[
                    "full name", "name", "candidate name", "applicant name",
                    "your name", "complete name"
                ],
                example_values=["John Smith", "Sarah Johnson"],
                required=True
            ),
            
            # Contact Information
            "email": FormField(
                field_name="email",
                field_type=FieldType.CONTACT,
                extraction_query="What is the person's email address? Look for email format like name@domain.com in the contact information.",
                common_labels=[
                    "email", "email address", "e-mail", "electronic mail",
                    "contact email", "work email", "personal email"
                ],
                example_values=["john.smith@email.com", "sarah@company.com"],
                required=True
            ),
            "phone": FormField(
                field_name="phone",
                field_type=FieldType.CONTACT,
                extraction_query="What is the person's phone number or telephone number? Look for numbers in formats like (555) 123-4567 or +1-555-123-4567.",
                common_labels=[
                    "phone", "phone number", "telephone", "mobile", "cell",
                    "contact number", "primary phone", "mobile number"
                ],
                example_values=["(555) 123-4567", "+1-555-123-4567"],
                required=True
            ),
            "address": FormField(
                field_name="address",
                field_type=FieldType.CONTACT,
                extraction_query="home address or location",
                common_labels=[
                    "address", "home address", "street address", "location",
                    "residence", "current address", "mailing address"
                ],
                example_values=["123 Main St, City, State 12345"]
            ),
            "city": FormField(
                field_name="city",
                field_type=FieldType.CONTACT,
                extraction_query="city or location",
                common_labels=["city", "location", "current city", "residence city"],
                example_values=["New York", "Los Angeles", "Chicago"]
            ),
            "state": FormField(
                field_name="state",
                field_type=FieldType.CONTACT,
                extraction_query="state or province",
                common_labels=["state", "province", "region"],
                example_values=["CA", "NY", "TX", "California"]
            ),
            "zip_code": FormField(
                field_name="zip_code",
                field_type=FieldType.CONTACT,
                extraction_query="zip code or postal code",
                common_labels=[
                    "zip", "zip code", "postal code", "postcode", "zipcode"
                ],
                example_values=["12345", "90210", "10001"]
            ),
            
            # Education
            "university": FormField(
                field_name="university",
                field_type=FieldType.EDUCATION,
                extraction_query="university or college name",
                common_labels=[
                    "university", "college", "school", "institution",
                    "alma mater", "educational institution"
                ],
                example_values=["Harvard University", "MIT", "Stanford"]
            ),
            "degree": FormField(
                field_name="degree",
                field_type=FieldType.EDUCATION,
                extraction_query="degree or qualification",
                common_labels=[
                    "degree", "qualification", "education level", "diploma",
                    "major", "field of study", "bachelor", "master", "phd"
                ],
                example_values=["Bachelor of Science", "MBA", "PhD in Computer Science"]
            ),
            "graduation_year": FormField(
                field_name="graduation_year",
                field_type=FieldType.EDUCATION,
                extraction_query="graduation year",
                common_labels=[
                    "graduation year", "year graduated", "completion year",
                    "graduation date", "year of graduation"
                ],
                example_values=["2020", "2018", "2022"]
            ),
            "gpa": FormField(
                field_name="gpa",
                field_type=FieldType.EDUCATION,
                extraction_query="GPA or grade point average",
                common_labels=["gpa", "grade point average", "grades", "cgpa"],
                example_values=["3.8", "3.5", "4.0"]
            ),
            
            # Experience
            "current_job_title": FormField(
                field_name="current_job_title",
                field_type=FieldType.EXPERIENCE,
                extraction_query="current job title or position",
                common_labels=[
                    "current position", "job title", "current job", "position",
                    "current role", "title", "occupation"
                ],
                example_values=["Software Engineer", "Marketing Manager", "Data Scientist"]
            ),
            "current_company": FormField(
                field_name="current_company",
                field_type=FieldType.EXPERIENCE,
                extraction_query="current company or employer",
                common_labels=[
                    "current company", "employer", "current employer",
                    "company", "organization", "workplace"
                ],
                example_values=["Google", "Microsoft", "Apple"]
            ),
            "years_of_experience": FormField(
                field_name="years_of_experience",
                field_type=FieldType.EXPERIENCE,
                extraction_query="total years of work experience",
                common_labels=[
                    "years of experience", "work experience", "experience",
                    "years worked", "professional experience"
                ],
                example_values=["5 years", "3-5 years", "7"]
            ),
            "previous_company": FormField(
                field_name="previous_company",
                field_type=FieldType.EXPERIENCE,
                extraction_query="previous company or employer",
                common_labels=[
                    "previous company", "former employer", "last company",
                    "previous employer", "prior company"
                ],
                example_values=["IBM", "Amazon", "Facebook"]
            ),
            
            # Skills
            "skills": FormField(
                field_name="skills",
                field_type=FieldType.SKILLS,
                extraction_query="technical skills and competencies",
                common_labels=[
                    "skills", "technical skills", "competencies", "abilities",
                    "expertise", "proficiencies", "technologies"
                ],
                example_values=["Python, JavaScript, React", "Project Management, Leadership"]
            ),
            "programming_languages": FormField(
                field_name="programming_languages",
                field_type=FieldType.SKILLS,
                extraction_query="programming languages",
                common_labels=[
                    "programming languages", "coding languages", "languages",
                    "programming skills", "development languages"
                ],
                example_values=["Python, Java, JavaScript", "C++, C#, SQL"]
            ),
            "certifications": FormField(
                field_name="certifications",
                field_type=FieldType.OTHER,
                extraction_query="certifications and professional credentials",
                common_labels=[
                    "certifications", "certificates", "credentials", "licenses",
                    "professional certifications", "qualifications"
                ],
                example_values=["AWS Certified", "PMP", "Google Cloud Certified"]
            ),
            
            # Other Common Fields
            "linkedin": FormField(
                field_name="linkedin",
                field_type=FieldType.CONTACT,
                extraction_query="What is the person's LinkedIn profile URL or LinkedIn username? Look for linkedin.com links or LinkedIn profiles.",
                common_labels=[
                    "linkedin", "linkedin profile", "linkedin url",
                    "professional profile", "linkedin link"
                ],
                example_values=["linkedin.com/in/johnsmith", "https://linkedin.com/in/sarah"]
            ),
            "github": FormField(
                field_name="github",
                field_type=FieldType.CONTACT,
                extraction_query="What is the person's GitHub profile URL or GitHub username? Look for github.com links or GitHub profiles.",
                common_labels=[
                    "github", "github profile", "github username",
                    "github url", "git profile"
                ],
                example_values=["github.com/johnsmith", "johnsmith"]
            ),
            "portfolio": FormField(
                field_name="portfolio",
                field_type=FieldType.CONTACT,
                extraction_query="portfolio website or personal website",
                common_labels=[
                    "portfolio", "website", "personal website", "portfolio url",
                    "portfolio link", "web portfolio"
                ],
                example_values=["johnsmith.com", "https://myportfolio.com"]
            ),
            "salary_expectation": FormField(
                field_name="salary_expectation",
                field_type=FieldType.OTHER,
                extraction_query="salary expectation or desired salary",
                common_labels=[
                    "salary expectation", "expected salary", "desired salary",
                    "salary range", "compensation expectation"
                ],
                example_values=["$80,000", "$70k-90k", "80000"]
            )
        }
    
    def _create_label_mapping(self) -> Dict[str, str]:
        """Create mapping from field labels to field names"""
        label_mapping = {}
        
        for field_name, field_info in self.field_mappings.items():
            # Add field name itself
            label_mapping[field_name.lower()] = field_name
            
            # Add all common labels
            for label in field_info.common_labels:
                label_mapping[label.lower()] = field_name
        
        return label_mapping
    
    def get_field_info(self, field_label: str) -> Optional[FormField]:
        """Get field information for a given label"""
        field_name = self.label_to_field.get(field_label.lower())
        if field_name:
            return self.field_mappings[field_name]
        return None
    
    def get_extraction_query(self, field_label: str) -> Optional[str]:
        """Get the standardized extraction query for a field label"""
        field_info = self.get_field_info(field_label)
        if field_info:
            return field_info.extraction_query
        
        # Enhanced fallback for unmapped fields with smarter query generation
        field_lower = field_label.lower()
        
        # Generate contextual queries for common patterns
        if any(term in field_lower for term in ['first', 'given']):
            return "What is the person's first name or given name? Look for names at the beginning of the resume."
        elif any(term in field_lower for term in ['last', 'family', 'surname']):
            return "What is the person's last name, surname, or family name? Look for names at the beginning of the resume."
        elif 'email' in field_lower:
            return "What is the person's email address? Look for email format like name@domain.com in the contact information."
        elif any(term in field_lower for term in ['phone', 'mobile', 'telephone']):
            return "What is the person's phone number or telephone number? Look for numbers in formats like (555) 123-4567."
        elif 'linkedin' in field_lower:
            return "What is the person's LinkedIn profile URL or LinkedIn username? Look for linkedin.com links."
        elif 'github' in field_lower:
            return "What is the person's GitHub profile URL or GitHub username? Look for github.com links."
        elif any(term in field_lower for term in ['company', 'employer']):
            return f"What is the person's {field_label.lower()}? Look in the work experience or employment history section."
        elif any(term in field_lower for term in ['title', 'position', 'job']):
            return f"What is the person's {field_label.lower()}? Look in the work experience section for job titles."
        elif any(term in field_lower for term in ['skill', 'technology', 'programming']):
            return f"What are the person's {field_label.lower()}? Look in the skills or technical competencies section."
        elif any(term in field_lower for term in ['university', 'college', 'school']):
            return f"What is the person's {field_label.lower()}? Look in the education section."
        elif any(term in field_lower for term in ['degree', 'education']):
            return f"What is the person's {field_label.lower()}? Look in the education section for degrees or qualifications."
        
        # Generic fallback
        return f"What is the person's {field_label.lower()}? Look for this information in the resume."
    
    def get_all_fields_by_type(self, field_type: FieldType) -> List[FormField]:
        """Get all fields of a specific type"""
        return [
            field for field in self.field_mappings.values()
            if field.field_type == field_type
        ]
    
    def get_required_fields(self) -> List[FormField]:
        """Get all required fields"""
        return [
            field for field in self.field_mappings.values()
            if field.required
        ]
    
    def suggest_field_name(self, field_label: str) -> Optional[str]:
        """Suggest the best field name for a given label"""
        field_info = self.get_field_info(field_label)
        if field_info:
            return field_info.field_name
        return None
    
    def get_example_form_fields(self) -> Dict[str, List[Dict]]:
        """Get example form fields organized by type for demo purposes"""
        examples = {}
        
        for field_type in FieldType:
            fields = self.get_all_fields_by_type(field_type)
            examples[field_type.value] = [
                {
                    "field_name": field.field_name,
                    "label": field.common_labels[0],  # Use first common label
                    "example_value": field.example_values[0] if field.example_values else "",
                    "required": field.required
                }
                for field in fields[:3]  # Limit to first 3 fields per type
            ]
        
        return examples


# Global form field mapper instance
form_mapper = FormFieldMapper()