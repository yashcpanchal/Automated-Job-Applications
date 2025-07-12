import pandas as pd 
import re
from collections import Counter

# Load the data
df = pd.read_csv('job_descriptions.csv')

# Common phrases to remove
COMMON_PHRASES = {
    'best practices', 'experience with', 'knowledge of', 'proficiency in',
    'strong', 'excellent', 'good', 'ability to', 'skills in', 'working knowledge of',
    'understanding of', 'familiarity with', 'including but not limited to',
    'such as', 'e.g.', 'i.e.', 'etc.', 'and', 'or', 'the', 'a', 'an', 'in', 'on',
    'at', 'for', 'with', 'to', 'of', 'as', 'by', 'via', 'using', 'through', 'from',
    'various', 'different', 'multiple', 'including', 'like', 'such',
    'other', 'related', 'relevant', 'basic', 'intermediate', 'advanced', 'expert',
    'senior', 'junior', 'entry-level', 'level', 'all', 'any', 'some', 'many', 'most'
}

def clean_skill(skill):
    """Clean and normalize a single skill."""
    # Remove any non-alphanumeric characters except spaces, hyphens, and forward slashes
    skill = re.sub(r"[^\w\s\-/]", "", str(skill).lower())
    # Remove extra spaces
    skill = re.sub(r"\s+", " ", skill).strip()
    # Remove common phrases
    words = [w for w in skill.split() if w.lower() not in COMMON_PHRASES]
    skill = " ".join(words).strip()
    # Remove any remaining non-word characters at start/end
    skill = re.sub(r"^[^\w]+|[^\w]+$", "", skill)
    return skill

def extract_skills(skills_text):
    if pd.isna(skills_text):
        return []
    
    text = str(skills_text).lower()
    
    # Remove content in parentheses and brackets
    text = re.sub(r'\([^)]*\)', ' ', text)
    text = re.sub(r'\[[^]]*\]', ' ', text)
    
    # Replace common delimiters with commas
    text = re.sub(r'[;|/\\]', ',', text)
    
    # Handle 'and' between skills
    text = re.sub(r'\s+and\s+', ', ', text)
    
    # Split by commas and clean each skill
    raw_skills = [s.strip() for s in text.split(",") if s.strip()]
    
    # Further split by common conjunctions and clean
    split_skills = []
    for skill in raw_skills:
        # Split by common conjunctions
        sub_skills = re.split(r'\s+(?:and|or|/|&)\s+', skill)
        for sub_skill in sub_skills:
            cleaned = clean_skill(sub_skill)
            if len(cleaned) > 1:  # Only include non-empty skills
                split_skills.append(cleaned)
    
    return split_skills

# Extract and count all skills
all_skills = []
for skills_text in df['skills'].dropna():
    all_skills.extend(extract_skills(skills_text))

# Count skill occurrences
skill_counts = Counter(all_skills)

# Filter out very common words that aren't useful as skills
MIN_SKILL_LENGTH = 2
MIN_OCCURRENCES = 5
filtered_skills = {
    skill: count for skill, count in skill_counts.items() 
    if (len(skill) >= MIN_SKILL_LENGTH and 
        count >= MIN_OCCURRENCES and 
        not any(word in COMMON_PHRASES for word in skill.split()))
}

# Sort skills by count (descending)
sorted_skills = sorted(filtered_skills.items(), key=lambda x: (-x[1], x[0]))

# Print top 100 skills
print("Top 100 most common skills:")
for skill, count in sorted_skills[:100]:
    print(f"{skill}: {count}")


with open('extracted_skills_improved.txt', 'w') as f:
    for skill, _ in sorted_skills:
        f.write(f'"{skill}",\n')

print(f"\nTotal unique skills: {len(sorted_skills)}")
print("Extracted skills have been saved to 'extracted_skills_improved.txt'")

with open('skill_counts.csv', 'w') as f:
    f.write("skill,count\n")
    for skill, count in sorted_skills:
        f.write(f'"{skill}",{count}\n')