"""
Section parser for identifying and extracting structured sections
from resume text (Education, Experience, Skills, etc.).
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class SectionType(Enum):
    """Enumeration of resume sections"""
    CONTACT = "contact"
    SUMMARY = "summary"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    SKILLS = "skills"
    PROJECTS = "projects"
    CERTIFICATIONS = "certifications"
    AWARDS = "awards"
    REFERENCES = "references"
    OTHER = "other"


@dataclass
class ResumeSection:
    """Represents a parsed resume section"""
    section_type: SectionType
    title: str
    content: str
    start_line: int
    end_line: int
    confidence: float


class SectionParser:
    """Parse resume text into structured sections"""
    
    def __init__(self):
        self.section_patterns = self._init_section_patterns()
    
    def _init_section_patterns(self) -> Dict[SectionType, List[str]]:
        """Initialize patterns for identifying section headers"""
        return {
            SectionType.CONTACT: [
                r'contact\s+information?',
                r'personal\s+details?',
                r'contact\s+details?'
            ],
            SectionType.SUMMARY: [
                r'(?:professional\s+)?summary',
                r'(?:career\s+)?objective',
                r'(?:professional\s+)?profile',
                r'about\s+me',
                r'overview'
            ],
            SectionType.EXPERIENCE: [
                r'(?:work\s+|professional\s+|employment\s+)?experience',
                r'work\s+history',
                r'employment\s+history',
                r'career\s+history',
                r'professional\s+background'
            ],
            SectionType.EDUCATION: [
                r'education(?:al\s+background)?',
                r'academic\s+background',
                r'qualifications',
                r'academic\s+history'
            ],
            SectionType.SKILLS: [
                r'(?:technical\s+)?skills',
                r'competencies',
                r'core\s+competencies',
                r'areas\s+of\s+expertise',
                r'technical\s+proficiencies'
            ],
            SectionType.PROJECTS: [
                r'projects?',
                r'key\s+projects?',
                r'notable\s+projects?',
                r'selected\s+projects?'
            ],
            SectionType.CERTIFICATIONS: [
                r'certifications?',
                r'professional\s+certifications?',
                r'licenses?\s+(?:and\s+certifications?)?'
            ],
            SectionType.AWARDS: [
                r'awards?',
                r'honors?',
                r'achievements?',
                r'recognitions?',
                r'awards?\s+(?:and\s+honors?)?'
            ],
            SectionType.REFERENCES: [
                r'references?',
                r'professional\s+references?'
            ]
        }
    
    def parse_sections(self, text: str) -> List[ResumeSection]:
        """Parse text into resume sections"""
        lines = text.split('\n')
        sections = []
        
        # Find section headers
        section_markers = self._find_section_markers(lines)
        
        # Extract content for each section
        for i, (line_idx, section_type, title, confidence) in enumerate(section_markers):
            start_line = line_idx
            
            # Determine end line (start of next section or end of document)
            if i + 1 < len(section_markers):
                end_line = section_markers[i + 1][0] - 1
            else:
                end_line = len(lines) - 1
            
            # Extract content
            content_lines = lines[start_line + 1:end_line + 1]
            content = '\n'.join(content_lines).strip()
            
            if content:  # Only add sections with content
                section = ResumeSection(
                    section_type=section_type,
                    title=title,
                    content=content,
                    start_line=start_line,
                    end_line=end_line,
                    confidence=confidence
                )
                sections.append(section)
        
        return sections
    
    def _find_section_markers(self, lines: List[str]) -> List[Tuple[int, SectionType, str, float]]:
        """Find section headers in the text"""
        markers = []
        
        for line_idx, line in enumerate(lines):
            line_clean = line.strip()
            if not line_clean:
                continue
            
            # Check if line looks like a section header
            if self._is_potential_header(line_clean):
                section_match = self._match_section_pattern(line_clean)
                if section_match:
                    section_type, confidence = section_match
                    markers.append((line_idx, section_type, line_clean, confidence))
        
        return markers
    
    def _is_potential_header(self, line: str) -> bool:
        """Check if a line could be a section header"""
        # Headers are typically:
        # - Short (< 100 characters)
        # - Don't contain excessive punctuation
        # - May be in all caps or title case
        # - Often standalone (not part of a paragraph)
        
        if len(line) > 100:
            return False
        
        # Check for header-like formatting
        is_all_caps = line.isupper()
        is_title_case = line.istitle()
        has_minimal_punctuation = len([c for c in line if c in '.,;:']) <= 1
        
        return (is_all_caps or is_title_case) and has_minimal_punctuation
    
    def _match_section_pattern(self, line: str) -> Optional[Tuple[SectionType, float]]:
        """Match line against section patterns"""
        line_lower = line.lower()
        
        for section_type, patterns in self.section_patterns.items():
            for pattern in patterns:
                if re.search(pattern, line_lower):
                    # Calculate confidence based on pattern specificity
                    confidence = self._calculate_pattern_confidence(pattern, line_lower)
                    return section_type, confidence
        
        return None
    
    def _calculate_pattern_confidence(self, pattern: str, line: str) -> float:
        """Calculate confidence score for pattern match"""
        # Base confidence
        confidence = 0.7
        
        # Boost confidence for exact matches
        if pattern.replace(r'\s+', ' ').replace('?', '') in line:
            confidence += 0.2
        
        # Boost for shorter, more specific patterns
        if len(pattern) < 20:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def get_section_by_type(self, sections: List[ResumeSection], section_type: SectionType) -> Optional[ResumeSection]:
        """Get the first section of a specific type"""
        for section in sections:
            if section.section_type == section_type:
                return section
        return None
    
    def get_sections_dict(self, sections: List[ResumeSection]) -> Dict[str, str]:
        """Convert sections to a dictionary mapping type to content"""
        sections_dict = {}
        
        for section in sections:
            key = section.section_type.value
            if key in sections_dict:
                # If multiple sections of same type, concatenate
                sections_dict[key] += "\n\n" + section.content
            else:
                sections_dict[key] = section.content
        
        return sections_dict
    
    def extract_structured_data(self, sections: List[ResumeSection]) -> Dict[str, any]:
        """Extract structured data from parsed sections"""
        structured_data = {}
        
        for section in sections:
            if section.section_type == SectionType.EXPERIENCE:
                structured_data['work_experience'] = self._parse_experience_section(section.content)
            elif section.section_type == SectionType.EDUCATION:
                structured_data['education'] = self._parse_education_section(section.content)
            elif section.section_type == SectionType.SKILLS:
                structured_data['skills'] = self._parse_skills_section(section.content)
        
        return structured_data
    
    def _parse_experience_section(self, content: str) -> List[Dict[str, str]]:
        """Parse work experience section into structured format"""
        experiences = []
        
        # Split into individual job entries (naive approach)
        # Look for patterns like job titles followed by company names
        entries = re.split(r'\n\s*\n', content)
        
        for entry in entries:
            if entry.strip():
                # Extract basic info (this is a simplified parser)
                lines = [line.strip() for line in entry.split('\n') if line.strip()]
                if lines:
                    exp_data = {
                        'title': lines[0] if lines else '',
                        'content': entry.strip()
                    }
                    experiences.append(exp_data)
        
        return experiences
    
    def _parse_education_section(self, content: str) -> List[Dict[str, str]]:
        """Parse education section into structured format"""
        education = []
        
        entries = re.split(r'\n\s*\n', content)
        
        for entry in entries:
            if entry.strip():
                lines = [line.strip() for line in entry.split('\n') if line.strip()]
                if lines:
                    edu_data = {
                        'institution': lines[0] if lines else '',
                        'content': entry.strip()
                    }
                    education.append(edu_data)
        
        return education
    
    def _parse_skills_section(self, content: str) -> List[str]:
        """Parse skills section into list of skills"""
        skills = []
        
        # Split by common delimiters
        skill_text = re.sub(r'[•\-\*]', ',', content)
        skill_items = re.split(r'[,\n\t]', skill_text)
        
        for skill in skill_items:
            skill = skill.strip()
            if skill and len(skill) > 1:
                skills.append(skill)
        
        return skills