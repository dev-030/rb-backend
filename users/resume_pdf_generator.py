"""
Professional Resume PDF Generator using ReportLab
Free, open-source, no API keys required
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from io import BytesIO
import base64
from PIL import Image as PILImage


class ResumePDFGenerator:
    """Generate professional ATS-friendly resume PDFs"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Create custom paragraph styles for resume"""
        # Name style (large, bold)
        self.styles.add(ParagraphStyle(
            name='Name',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=6,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Contact info style
        self.styles.add(ParagraphStyle(
            name='Contact',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#555555'),
            spaceAfter=12,
            alignment=TA_CENTER
        ))
        
        # Section heading style
        self.styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2c3e50'),
            spaceBefore=12,
            spaceAfter=6,
            fontName='Helvetica-Bold',
            borderWidth=0,
            borderPadding=0,
            borderColor=colors.HexColor('#3498db'),
            borderRadius=None,
            backColor=None,
            leftIndent=0,
            rightIndent=0,
        ))
        
        # Job title style
        self.styles.add(ParagraphStyle(
            name='JobTitle',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#2c3e50'),
            spaceBefore=6,
            spaceAfter=3,
            fontName='Helvetica-Bold'
        ))
        
        # Company/Institution style
        self.styles.add(ParagraphStyle(
            name='Company',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#555555'),
            spaceAfter=3,
            fontName='Helvetica-Oblique'
        ))
        
        # Body text style
        self.styles.add(ParagraphStyle(
            name='Body',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#333333'),
            spaceAfter=6,
            leading=14
        ))
        
        # Skill style
        self.styles.add(ParagraphStyle(
            name='Skill',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=4
        ))
    
    def generate(self, resume_data):
        """
        Generate PDF from resume data
        
        Args:
            resume_data: Dictionary with personalInfo, workExperience, education, skills
            
        Returns:
            BytesIO object containing the PDF
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        story = []
        
        # Personal Info Section
        personal = resume_data.get('personalInfo', {})
        if personal:
            story.extend(self._build_personal_section(personal))
        
        # Work Experience Section
        work_exp = resume_data.get('workExperience', [])
        if work_exp:
            story.append(Spacer(1, 0.2*inch))
            story.extend(self._build_work_section(work_exp))
        
        # Education Section
        education = resume_data.get('education', [])
        if education:
            story.append(Spacer(1, 0.2*inch))
            story.extend(self._build_education_section(education))
        
        # Skills Section
        skills = resume_data.get('skills', [])
        if skills:
            story.append(Spacer(1, 0.2*inch))
            story.extend(self._build_skills_section(skills))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer
    
    def _build_personal_section(self, personal):
        """Build personal information section"""
        elements = []
        
        # Name
        name = personal.get('fullName', '')
        if name:
            elements.append(Paragraph(name, self.styles['Name']))
        
        # Contact info (email, location, DOB)
        contact_parts = []
        if personal.get('email'):
            contact_parts.append(personal['email'])
        if personal.get('location'):
            contact_parts.append(personal['location'])
        if personal.get('dateOfBirth'):
            contact_parts.append(f"DOB: {personal['dateOfBirth']}")
        
        if contact_parts:
            contact_text = ' | '.join(contact_parts)
            elements.append(Paragraph(contact_text, self.styles['Contact']))
        
        # Divider line
        elements.append(Spacer(1, 0.1*inch))
        line = Table([['']], colWidths=[7*inch])
        line.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, 0), 1, colors.HexColor('#3498db')),
        ]))
        elements.append(line)
        
        return elements
    
    def _build_work_section(self, work_experiences):
        """Build work experience section"""
        elements = []
        
        # Section heading
        elements.append(Paragraph('WORK EXPERIENCE', self.styles['SectionHeading']))
        elements.append(Spacer(1, 0.1*inch))
        
        for exp in work_experiences:
            # Job title
            job_title = exp.get('jobTitle', 'Position')
            elements.append(Paragraph(job_title, self.styles['JobTitle']))
            
            # Company and dates
            company_parts = []
            if exp.get('company'):
                company_parts.append(exp['company'])
            if exp.get('location'):
                company_parts.append(exp['location'])
            
            company_text = ' - '.join(company_parts) if company_parts else ''
            
            # Add dates
            start_date = exp.get('startDate', '')
            end_date = exp.get('endDate', 'Present') if not exp.get('current') else 'Present'
            if start_date:
                company_text += f" | {start_date} - {end_date}"
            
            if company_text:
                elements.append(Paragraph(company_text, self.styles['Company']))
            
            # Description
            description = exp.get('description', '')
            if description:
                elements.append(Paragraph(description, self.styles['Body']))
            
            # Responsibilities (bullet points)
            responsibilities = exp.get('responsibilities', [])
            if responsibilities:
                for resp in responsibilities:
                    bullet_text = f"• {resp}"
                    elements.append(Paragraph(bullet_text, self.styles['Body']))
            
            elements.append(Spacer(1, 0.15*inch))
        
        return elements
    
    def _build_education_section(self, education_list):
        """Build education section"""
        elements = []
        
        # Section heading
        elements.append(Paragraph('EDUCATION', self.styles['SectionHeading']))
        elements.append(Spacer(1, 0.1*inch))
        
        for edu in education_list:
            # Degree
            degree = edu.get('degree', '')
            field = edu.get('fieldOfStudy', '')
            degree_text = f"{degree} - {field}" if field else degree
            
            if degree_text:
                elements.append(Paragraph(degree_text, self.styles['JobTitle']))
            
            # Institution and years
            institution_parts = []
            if edu.get('institutionName'):
                institution_parts.append(edu['institutionName'])
            
            start_year = edu.get('startYear', '')
            end_year = edu.get('endYear', 'Present') if not edu.get('current') else 'Present'
            if start_year:
                institution_parts.append(f"{start_year} - {end_year}")
            
            if edu.get('grade'):
                institution_parts.append(f"Grade: {edu['grade']}")
            
            if institution_parts:
                institution_text = ' | '.join(institution_parts)
                elements.append(Paragraph(institution_text, self.styles['Company']))
            
            elements.append(Spacer(1, 0.1*inch))
        
        return elements
    
    def _build_skills_section(self, skills):
        """Build skills section"""
        elements = []
        
        # Section heading
        elements.append(Paragraph('SKILLS', self.styles['SectionHeading']))
        elements.append(Spacer(1, 0.1*inch))
        
        # Display skills as comma-separated list or bullet points
        if len(skills) <= 10:
            # Comma-separated for short lists
            skills_text = ', '.join(skills)
            elements.append(Paragraph(skills_text, self.styles['Skill']))
        else:
            # Bullet points for long lists
            for skill in skills:
                elements.append(Paragraph(f"• {skill}", self.styles['Skill']))
        
        return elements
