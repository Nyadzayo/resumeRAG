"""
Entity extraction service for identifying and extracting structured information
from resume text including names, companies, emails, phone numbers, etc.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ExtractedEntity:
    """Represents an extracted entity with metadata"""
    entity_type: str
    value: str
    confidence: float
    start_pos: int
    end_pos: int
    source_text: str


class EntityExtractor:
    """Extract structured entities from resume text"""
    
    def __init__(self):
        self.patterns = self._init_patterns()
    
    def _init_patterns(self) -> Dict[str, Dict]:
        """Initialize regex patterns for entity extraction"""
        return {
            "email": {
                "pattern": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                "confidence": 0.9
            },
            "phone": {
                "pattern": r'(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',
                "confidence": 0.8
            },
            "linkedin": {
                "pattern": r'(?:https?://)?(?:www\.)?linkedin\.com/in/[\w-]+/?',
                "confidence": 0.9
            },
            "github": {
                "pattern": r'(?:https?://)?(?:www\.)?github\.com/[\w-]+/?',
                "confidence": 0.9
            },
            "website": {
                "pattern": r'(?:https?://)?(?:www\.)?[\w-]+\.[\w.-]+(?:/[\w.-]*)*/?',
                "confidence": 0.7
            },
            "degree": {
                "pattern": r'\b(?:Bachelor|Master|PhD|Ph\.D\.|B\.S\.|B\.A\.|M\.S\.|M\.A\.|MBA|M\.B\.A\.)\b',
                "confidence": 0.8
            },
            "gpa": {
                "pattern": r'\bGPA:?\s*([0-4]\.\d{1,2})\b',
                "confidence": 0.9
            },
            "date_range": {
                "pattern": r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\s*-\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b',
                "confidence": 0.8
            },
            "year_range": {
                "pattern": r'\b\d{4}\s*-\s*(?:\d{4}|Present|Current)\b',
                "confidence": 0.8
            },
            "certification": {
                "pattern": r'\b(?:Certified|Certificate|Certification)\s+[\w\s]+\b',
                "confidence": 0.7
            }
        }
    
    def extract_entities(self, text: str) -> List[ExtractedEntity]:
        """Extract all entities from text"""
        entities = []
        
        for entity_type, pattern_info in self.patterns.items():
            pattern = pattern_info["pattern"]
            base_confidence = pattern_info["confidence"]
            
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                entity = ExtractedEntity(
                    entity_type=entity_type,
                    value=match.group().strip(),
                    confidence=base_confidence,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    source_text=text[max(0, match.start() - 20):match.end() + 20]
                )
                entities.append(entity)
        
        return entities
    
    def extract_names(self, text: str) -> List[ExtractedEntity]:
        """Extract potential names using heuristics"""
        entities = []
        
        # Simple name pattern - capitalized words at the beginning
        lines = text.split('\n')
        
        for i, line in enumerate(lines[:10]):  # Check first 10 lines
            line = line.strip()
            if not line:
                continue
            
            # Look for potential names (2-4 capitalized words)
            name_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}\b'
            matches = re.finditer(name_pattern, line)
            
            for match in matches:
                name = match.group().strip()
                # Filter out common words that aren't names
                if self._is_likely_name(name):
                    entity = ExtractedEntity(
                        entity_type="name",
                        value=name,
                        confidence=0.7 if i < 3 else 0.5,  # Higher confidence for top lines
                        start_pos=match.start(),
                        end_pos=match.end(),
                        source_text=line
                    )
                    entities.append(entity)
        
        return entities
    
    def _is_likely_name(self, text: str) -> bool:
        """Heuristic to determine if text is likely a person's name"""
        words = text.split()
        
        # Filter out common resume words
        common_words = {
            'resume', 'curriculum', 'vitae', 'experience', 'education', 
            'skills', 'projects', 'contact', 'information', 'summary',
            'objective', 'profile', 'about', 'references', 'available'
        }
        
        # Check if any word is in common words
        for word in words:
            if word.lower() in common_words:
                return False
        
        # Check for reasonable name length
        if len(words) < 2 or len(words) > 4:
            return False
        
        # Check for reasonable word lengths
        for word in words:
            if len(word) < 2 or len(word) > 20:
                return False
        
        return True
    
    def extract_skills(self, text: str) -> List[ExtractedEntity]:
        """Extract technical skills and competencies"""
        entities = []
        
        # Common technical skills patterns
        skill_patterns = [
            r'\b(?:Python|Java|JavaScript|C\+\+|C#|Ruby|PHP|Go|Rust|Swift|Kotlin)\b',
            r'\b(?:React|Angular|Vue|Node\.js|Express|Django|Flask|Spring|Laravel)\b',
            r'\b(?:SQL|MySQL|PostgreSQL|MongoDB|Redis|Elasticsearch|Cassandra)\b',
            r'\b(?:AWS|Azure|GCP|Docker|Kubernetes|Jenkins|Git|GitHub|GitLab)\b',
            r'\b(?:Machine Learning|AI|Data Science|Deep Learning|TensorFlow|PyTorch)\b',
            r'\b(?:HTML|CSS|Bootstrap|Tailwind|SASS|LESS)\b'
        ]
        
        for pattern in skill_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                entity = ExtractedEntity(
                    entity_type="skill",
                    value=match.group(),
                    confidence=0.8,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    source_text=text[max(0, match.start() - 20):match.end() + 20]
                )
                entities.append(entity)
        
        return entities
    
    def extract_companies(self, text: str) -> List[ExtractedEntity]:
        """Extract company names from experience sections"""
        entities = []
        
        # Look for patterns like "at Company Name" or "Company Name, City"
        company_patterns = [
            r'\bat\s+([A-Z][A-Za-z\s&.,]+(?:Inc|LLC|Corp|Ltd|Company|Co\.|Technologies|Tech|Systems|Solutions|Group|Consulting)?)\b',
            r'\b([A-Z][A-Za-z\s&.,]+(?:Inc|LLC|Corp|Ltd|Company|Co\.|Technologies|Tech|Systems|Solutions|Group|Consulting)),\s*[A-Z][a-z]+',
        ]
        
        for pattern in company_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                company = match.group(1).strip()
                if len(company) > 2 and len(company) < 50:  # Reasonable company name length
                    entity = ExtractedEntity(
                        entity_type="company",
                        value=company,
                        confidence=0.7,
                        start_pos=match.start(1),
                        end_pos=match.end(1),
                        source_text=match.group()
                    )
                    entities.append(entity)
        
        return entities
    
    def extract_all(self, text: str) -> Dict[str, List[ExtractedEntity]]:
        """Extract all types of entities from text"""
        all_entities = {
            "general": self.extract_entities(text),
            "names": self.extract_names(text),
            "skills": self.extract_skills(text),
            "companies": self.extract_companies(text)
        }
        
        return all_entities
    
    def get_best_entities_by_type(self, entities: Dict[str, List[ExtractedEntity]]) -> Dict[str, ExtractedEntity]:
        """Get the best entity for each type based on confidence"""
        best_entities = {}
        
        # Flatten all entities
        all_entities = []
        for entity_list in entities.values():
            all_entities.extend(entity_list)
        
        # Group by type and find best
        entity_groups = {}
        for entity in all_entities:
            if entity.entity_type not in entity_groups:
                entity_groups[entity.entity_type] = []
            entity_groups[entity.entity_type].append(entity)
        
        for entity_type, group in entity_groups.items():
            # Sort by confidence and take the best
            best = max(group, key=lambda x: x.confidence)
            best_entities[entity_type] = best
        
        return best_entities