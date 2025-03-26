import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

nlp = spacy.load("en_core_web_sm")

def extract_keywords(text):
    """Extracts keywords (skills, job titles, key phrases) from text."""
    doc = nlp(text)
    keywords = [token.lemma_ for token in doc if token.pos_ in ["NOUN", "PROPN", "ADJ", "VERB"]]
    return list(set(keywords))

resume_text = """John Doe, Software Engineer with 5 years experience in Java, Spring Boot, REST APIs, and Microservices."""
job_description = """We are looking for a Java Developer with expertise in Spring Boot, REST APIs, and cloud deployment."""

resume_keywords = extract_keywords(resume_text)
job_keywords = extract_keywords(job_description)

print("Resume Keywords:", resume_keywords)
print("Job Keywords:", job_keywords)

def calculate_similarity(resume, job):
    """Calculates similarity score between resume and job description."""
    vectorizer = TfidfVectorizer()
    vectors = vectorizer.fit_transform([resume, job])
    similarity = cosine_similarity(vectors[0], vectors[1])
    return similarity[0][0]

match_score = calculate_similarity(" ".join(resume_keywords), " ".join(job_keywords))
print("Job Match Score:", match_score)
