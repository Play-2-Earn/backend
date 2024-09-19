# -*- coding: utf-8 -*-
"""CV_analyze.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/10q9y0Px0KGhq1GxZb0t0zBKFBhKPo99_
"""

#from google.colab import drive
#drive.mount('/content/drive')

'''
pip install PyPDF2

pip install sentence_transformers
'''

import re
import os
import re
import docx
import logging
import subprocess
import spacy
from PyPDF2 import PdfReader
import numpy as np
import pdfplumber
import tensorflow_hub as hub
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer, util
from sklearn.preprocessing import normalize
from cloudmersive_virus_api_client.rest import ApiException
import cloudmersive_virus_api_client

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Cloudmersive Virus Scan Configuration
api_key = '88ce5f3c-ff0d-4ff1-b93a-6e367230dc6a'  # Replace with your actual API key

def scan_one_file(input_file, api_key, retry_time):
    """
    Scans a single file for viruses and returns whether it is clean.
    """
    configuration = cloudmersive_virus_api_client.Configuration()
    configuration.api_key['Apikey'] = api_key
    api_instance = cloudmersive_virus_api_client.ScanApi(
        cloudmersive_virus_api_client.ApiClient(configuration)
    )
    allow_executables = False
    allow_invalid_files = False
    allow_scripts = True
    allow_password_protected_files = True
    allow_macros = True
    allow_xml_external_entities = False
    allow_insecure_deserialization = False
    allow_html = False

    try:
        api_response = api_instance.scan_file_advanced(
            input_file,
            allow_executables=allow_executables,
            allow_invalid_files=allow_invalid_files,
            allow_scripts=allow_scripts,
            allow_password_protected_files=allow_password_protected_files,
            allow_macros=allow_macros,
            allow_xml_external_entities=allow_xml_external_entities,
            allow_insecure_deserialization=allow_insecure_deserialization,
            allow_html=allow_html
        )
        return api_response.clean_result
    except Exception as e:
        logging.warning(f"Exception when calling ScanApi->scan_file: {e}\n")
        if retry_time < 5:
            return scan_one_file(input_file, api_key, retry_time + 1)
        else:
            logging.warning(f"Failed to scan file {input_file}")
            return False

def scan_all_files_in_repository(cv_folder_path, all_valid_files, api_key):
    """
    Scans all valid files in a directory and returns a list of files without any problems.
    """
    files_without_problem = []
    for file_name in all_valid_files:
        logging.info(f"Scanning file: {file_name}")
        file_path = os.path.join(cv_folder_path, file_name)
        scan_result = scan_one_file(file_path, api_key, 0)
        if scan_result:
            files_without_problem.append(file_name)
            logging.info(f"File {file_name} is clean")
        else:
            logging.warning(f"File {file_name} is not clean")
    return files_without_problem

"""AI Models"""

# Load Universal Sentence Encoder
def load_use_model():
    model = hub.load("https://tfhub.dev/google/universal-sentence-encoder/4")
    return model

# Load a bert model for skill match
def load_bert_model():
    model = SentenceTransformer('bert-large-nli-stsb-mean-tokens', device='cpu')
    return model

def read_skills_from_file(file_path):
    """
    Reads all the skills from the given file.

    Args:
        file_path (str): The path to the skills file.

    Returns:
        list: A list of skills extracted from the file.
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        skills = [line.strip() for line in file.readlines()]

    return skills

'''
def extract_text_from_pdf(pdf_path):
    """
    Extracts text from a PDF file using PyPDF2.

    Args:
        pdf_path (str): The path to the PDF file.

    Returns:
        str: Extracted text from the PDF file.
    """
    text = ""

    try:
        reader = PdfReader(pdf_path)

        # Iterate through each page and extract text
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                lines = page_text.splitlines()  # Split by actual line breaks
                text += "\n".join(lines) + "\n"
                #text += lines + "\n"
            else:
                logging.warning(f"No text found on a page in {pdf_path}")
    except Exception as e:
        logging.error(f"Error reading PDF file {pdf_path}: {e}")
    finally:
        return text
'''
import pdfplumber
import logging

def extract_text_from_pdf(pdf_path):
    """
    Extracts text from a PDF file using pdfplumber with error handling.
    
    Args:
        pdf_path (str): The path to the PDF file.

    Returns:
        str: The extracted text from the PDF. If an error occurs, an empty string is returned.
    """
    text = ""  # Initialize an empty string to store the extracted text

    try:
        # Open the PDF file using pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            # Iterate through each page in the PDF
            for page in pdf.pages:
                # Extract text from the current page and append it to the text variable
                page_text = page.extract_text()
                if page_text:
                    text += page_text
                else:
                    logging.warning(f"No text found on page {pdf.pages.index(page)} in {pdf_path}")
    except Exception as e:
        # Log any errors that occur during the PDF reading process
        logging.error(f"Error reading PDF file {pdf_path}: {e}")
        return ""  # Return an empty string if an error occurs

    return text  # Return the extracted text after successfully processing the PDF

def extract_text_from_docx(docx_file_path):
    text = ""

    try:
        doc = docx.Document(docx_file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        logging.error(f"Error reading DOCX file {docx_file_path}: {e}")
    finally:
        return text

def extract_text_from_doc(doc_file_path):
    try:
        result = subprocess.run(['antiword', doc_file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result.stdout
    except Exception as e:
        logging.error(f"Error reading DOC file {doc_file_path}: {e}")
        return ""

def match_skills_in_jd(jd_text, skills):
    """
    Matches skills from the skills list in the JD text.

    Args:
        jd_text (str): The job description text.
        skills (list): The list of skills to match.

    Returns:
        list: A list of matched skills found in the JD text.
    """
    matched_skills = []

    jd_text_lower = jd_text.lower()

    # Traverse through each skill and use regex to match full words
    for skill in skills:
        # Escape any special characters in the skill and ensure it matches as a full word
        skill_pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(skill_pattern, jd_text_lower):
            matched_skills.append(skill)

    return matched_skills

def rank_skills_by_importance(jd_text, matched_skills, top_n=25):
    """
    Ranks the matched skills based on their TF-IDF scores from the JD text.

    Args:
        jd_text (str): The job description text.
        matched_skills (list): The list of matched skills to rank.
        top_n (int): Number of top skills to return.

    Returns:
        list: A list of top_n ranked skills based on their importance.
    """
    # Initialize TF-IDF Vectorizer for the matched skills only
    vectorizer = TfidfVectorizer(vocabulary=matched_skills, stop_words='english', min_df=1, max_df=1.0)

    # Fit the vectorizer on the JD text to compute TF-IDF scores
    tfidf_matrix = vectorizer.fit_transform([jd_text])

    # Get the TF-IDF scores for each skill
    tfidf_scores = zip(vectorizer.get_feature_names_out(), tfidf_matrix.toarray()[0])


    # calculate BERT embedding
    model = load_bert_model()
    jd_embedding = model.encode([jd_text], convert_to_tensor=True)

    combined_scores = {}

    # get the overall score of each skill from TF-IDF Score and Semantic Similarity then take mean
    for skill, tfidf in tfidf_scores:
        skill_embedding = model.encode([skill], convert_to_tensor=True)
        semantic_similarity = util.pytorch_cos_sim(jd_embedding, skill_embedding).item()

        combined_score = (tfidf * 0.5) + (semantic_similarity * 0.5)
        combined_scores[skill] = combined_score

    # Sort skills by their TF-IDF scores in descending order
    ranked_skills = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)

    # Select the top N skills, or return all skills if top_n exceeds the number of skills
    top_skills = [skill for skill, score in ranked_skills[:top_n]]

    return top_skills

# match_skills_in_jd function (unchanged):
def match_skills_in_jd(jd_text, skills):
    """
    Matches skills from the skills list in the JD text or CV text.

    Args:
        jd_text (str): The job description or CV text.
        skills (list): The list of skills to match.

    Returns:
        list: A list of matched skills found in the text.
    """
    matched_skills = []

    jd_text_lower = jd_text.lower()

    # Traverse through each skill and use regex to match full words
    for skill in skills:
        # Escape any special characters in the skill and ensure it matches as a full word
        skill_pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(skill_pattern, jd_text_lower):
            matched_skills.append(skill)

    return matched_skills

'''=================================================='''

# Preprocessing the text: lowercasing, removing special characters, etc.
def preprocess_text(text):
    text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with single space
    text = re.sub(r'[^\w\s]', '', text)  # Remove special characters
    return text.lower()

def split_into_points(section_text):
    return [point.strip() for point in re.split(r'[\n•-]', section_text) if point.strip()]

# Parsing function
def parse_jd(jd_text):
    sections = {}

    # Define the patterns to match the sections
    patterns = {
        "Goal": r"Goal:\s*(.*?)(?:\n\n|$)",
        "Objectives": r"Objectives:\s*(.*?)(?:Deliverables:|$)",
        "Deliverables": r"Deliverables:\s*(.*?)(?:Requirements:|$)",
        "Requirements": r"Requirements:\s*(.*?)(?:Skills:|$)",
        "Skills": r"Skills:\s*(.*?)(?:Experience:|$)",
        "Experience": r"Experience:\s*(.*)"
    }

    # Iterate over each pattern and apply regex to find corresponding section
    for section, pattern in patterns.items():
        match = re.search(pattern, jd_text, re.DOTALL)
        if match:
            # Clean up the matched text by stripping extra spaces
            sections[section] = match.group(1).strip()

    return sections

def extract_candidate_name(text, nlp):
    """
    Extracts the candidate name using Named Entity Recognition (NER).
    """
    # Split the text into words and take the first ten words
    first_ten_words = " ".join(text.split()[:10])

    print(f"First 10 words: ", first_ten_words)
    
    doc = nlp(first_ten_words)
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            return ent.text
    return "Unknown"

def extract_experience(text):
    """
    Extracts the experience section from the given text using regex pattern matching.
    
    Args:
        text (str): The text to extract experience from (e.g., from a CV or JD).
    
    Returns:
        list: The extracted experience text, or an empty list if no experience section is found.
    """
    # Define a more flexible experience regex pattern
    #experience_pattern = r'(experience|work\s*experience|professional\s*experience|job\s*history)\s*[:\n]*([\s\S]+?)(?:skills|education|certifications|$)'
    #experience_pattern = r'(?:experience|work\s*experience|professional\s*experience|job\s*history|employment\s*history)\s*[:\n]*([\s\S]+?)(?:skills|education|certifications|expertise|$)'
    experience_pattern = r'(?:experience|work\s*experience|professional\s*experience|job\s*history|employment\s*history)\s*[:\n]*([\s\S]+?)(?=\b(?:skills|education|certifications|expertise|projects|summary)\b|$)'

    experience_matches = re.finditer(experience_pattern, text, re.IGNORECASE)

    all_experiences = []

    # Iterate over all matches
    for match in experience_matches:
        experience_text = match.group(1).strip()
        experience_list = re.split(r'\s{2,}', experience_text)
        # Clean up the experience text
        cleaned_experience_list = [re.sub(r'\s+', ' ', exp).strip() for exp in experience_list]  # Replace multiple spaces and newlines with a single space
        all_experiences.extend(cleaned_experience_list)

    return all_experiences


# Modified function to combine JD sections for experience comparison
def combine_jd_sections(sections):
    """
    Combine the Requirements, Skills, and Experience sections from the JD.

    Args:
        sections (dict): The parsed sections of the JD.

    Returns:
        str: Combined text of Requirements, Skills, and Experience sections.
    """
    combined_text = []

    if sections.get("Requirements"):
        combined_text.append(sections["Requirements"])
    if sections.get("Skills"):
        combined_text.append(sections["Skills"])
    if sections.get("Experience"):
        combined_text.append(sections["Experience"])

    # Join all sections into one combined text
    return " ".join(combined_text)

# Modified function to calculate experience similarity
def calculate_experience_similarity(cv_text, jd_combined_text):
    """
    Calculate the similarity between the CV's experience and the combined JD sections (Requirements, Skills, Experience).

    Args:
        cv_text (str): The text extracted from the CV.
        jd_combined_text (str): The combined JD sections to compare with.

    Returns:
        float: The similarity score between the combined JD and CV experience sections.
    """
    model = load_bert_model()

    # Extract experience from the CV
    cv_experience = extract_experience(cv_text)
    cv_experience_text = " ".join(cv_experience)

    # If no experience is found in either, return 0
    if not cv_experience_text or not jd_combined_text:
        return 0.0

    # Generate BERT embeddings for both JD combined and CV experience
    jd_combined_embedding = model.encode(jd_combined_text, convert_to_tensor=True)
    cv_experience_embedding = model.encode(cv_experience_text, convert_to_tensor=True)

    # Calculate cosine similarity between the embeddings
    experience_similarity = util.pytorch_cos_sim(jd_combined_embedding, cv_experience_embedding)
    experience_similarity_percent = max(0, experience_similarity.item()) * 100

    return experience_similarity_percent, cv_experience


# Modified function to process CVs using combined JD sections
def process_cv_folder(cv_folder_path, all_skills, ranked_skills, requirements_points, jd_combined_text, model):
    """
    Processes all CVs in a folder and calculates which ranked skills are matched in each CV.
    Additionally, calculates the similarity between the CV and the combined JD sections.

    Args:
        cv_folder_path (str): The folder containing CV PDF files.
        ranked_skills (list): List of ranked skills from the JD to match against CVs.
        requirements_points (list): List of requirement points from the JD.
        jd_combined_text (str): The combined JD sections for comparison.
        model: The Universal Sentence Encoder model for calculating similarity.

    Returns:
        list: A list of tuples containing CV file name, matched ranked skills, skill match score,
              requirements similarity score, and matched requirement sections.
    """
    cv_results = []
    cv_files = [file for file in os.listdir(cv_folder_path) if file.endswith(('.pdf', '.docx', '.doc'))]

    safe_cv_files = cv_files
    #safe_cv_files = scan_all_files_in_repository(cv_folder_path, cv_files, api_key)
    logging.info(f"All clean CV files: {safe_cv_files}")

    # Loop through all files in the folder
    for cv_file in safe_cv_files:
        cv_path = os.path.join(cv_folder_path, cv_file)

        # deal with doc, docx, pdf, while other file type is not allowed
        if cv_file.endswith(".pdf"):
            cv_text = extract_text_from_pdf(cv_path)
        elif cv_file.endswith(".docx"):
            cv_text = extract_text_from_docx(cv_path)
        elif cv_file.endswith(".doc"):
            cv_text = extract_text_from_doc(cv_path)
        else:
            logging.info("File type not supported.")
            continue

        # Extract candidate name
        nlp = spacy.load('en_core_web_sm')
        candidate_name = extract_candidate_name(cv_text, nlp)

        # Preprocess CV text (optional if necessary, similar to how JD is preprocessed)
        cv_text = preprocess_text(cv_text)

        # extract cv skills (all)
        cv_skills = match_skills_in_jd(cv_text, all_skills)

        # Match ranked skills from the JD with the CV text
        #print(f"Ranked Skills: ", ranked_skills)
        matched_skills = match_skills_in_jd(cv_text, ranked_skills)
        #print(f"matched_skills: ", matched_skills)

        # Calculate match ratio (matched skills / total ranked skills)
        skill_match_ratio = len(matched_skills) / len(ranked_skills) * 100 if len(ranked_skills) > 0 else 0

        # Calculate requirements similarity using the calculate_similarity_granular function
        avg_similarity, matched_sections = calculate_similarity_granular(requirements_points, cv_text, model)
        avg_similarity = max(0, avg_similarity) * 100

        # Calculate experience similarity with combined JD sections
        experience_similarity, cv_experience = calculate_experience_similarity(cv_text, jd_combined_text)

        # Calculate weighted full score
        total_similarity = (skill_match_ratio * 0.4) + (avg_similarity * 0.5) + (experience_similarity * 0.1)

        cv_results.append((cv_file, candidate_name, cv_skills, matched_skills, skill_match_ratio, matched_sections, avg_similarity, cv_experience, experience_similarity, total_similarity))

        #print("All Skills in CV: ", cv_skills)
        #print("Matched Skills in CV: ", matched_skills)

    return cv_results

# Calculate similarity between JD sections and CV
def calculate_similarity_granular(jd_sections, cv_text, model):
    matched_sections = []
    total_similarity = 0

    for section in jd_sections:
        embeddings = model([section, cv_text])
        similarity = cosine_similarity(embeddings[0].numpy().reshape(1, -1), embeddings[1].numpy().reshape(1, -1))

        if similarity[0][0] > 0.0:
            matched_sections.append(section)

        total_similarity += similarity[0][0]

    avg_similarity = total_similarity / len(jd_sections) if jd_sections else 0
    return avg_similarity, matched_sections

def analyze_cvs(jd_text, cv_folder_path, linkedin_skills_file_path):
    """
    Analyzes CVs against a job description, calculates scores, and ranks CVs.
    Returns the filename, full score, matched experience, and skills for each CV.

    Args:
        jd_text (str): The job description text.
        cv_folder_path (str): The path to the folder containing CVs.
        linkedin_skills_file_path (str): The path to the file with LinkedIn skills.

    Returns:
        list: A list of dictionaries containing rank, filename, full score, experience, and skills for each CV.
    """
    try:
        # Check if JD text is valid
        if not jd_text or not isinstance(jd_text, str):
            raise ValueError("Invalid job description text.")

        # Check if CV folder path exists
        if not os.path.isdir(cv_folder_path):
            raise FileNotFoundError(f"CV folder path not found: {cv_folder_path}")
        
        # Check if LinkedIn skills file path exists
        if not os.path.isfile(linkedin_skills_file_path):
            raise FileNotFoundError(f"Skills file path not found: {linkedin_skills_file_path}")

        # Parse the job description into sections
        sections = parse_jd(jd_text)

        # Combine sections for experience and requirements comparison
        jd_combined_text = combine_jd_sections(sections)

        # Read LinkedIn skills from the file
        try:
            skills_from_file = read_skills_from_file(linkedin_skills_file_path)
        except Exception as e:
            logging.error(f"Error reading skills file: {e}")
            return []

        # Extract skills and requirements from the job description
        jd_skills_section = sections.get("Skills", "")
        jd_requirements_section = sections.get("Requirements", "")

        # Process the job description only if both skills and requirements sections exist
        if jd_skills_section and jd_requirements_section:
            # Match skills from LinkedIn file with JD skills section
            matched_skills = match_skills_in_jd(jd_skills_section, skills_from_file)

            # Rank the matched skills based on their importance
            ranked_skills = rank_skills_by_importance(jd_skills_section, matched_skills)

            # Preprocess and split the Requirements section for granular comparison
            processed_requirements = preprocess_text(jd_requirements_section)
            requirements_points = split_into_points(processed_requirements)

            # Load the model for similarity comparison
            try:
                model = load_use_model()
            except Exception as e:
                logging.error(f"Error loading Universal Sentence Encoder model: {e}")
                return []

            # Process each CV in the specified folder
            try:
                cv_results = process_cv_folder(cv_folder_path, skills_from_file, ranked_skills, requirements_points, jd_combined_text, model)
            except Exception as e:
                logging.error(f"Error processing CVs in folder: {e}")
                return []

            # Sort the CV results by the full similarity score in descending order
            sorted_cv_results = sorted(cv_results, key=lambda x: x[-1], reverse=True)

            # Prepare the data for each CV to be printed later
            cvs_data = []

            #print(f"Top JD skills: ", ranked_skills)

            for rank, (cv_file, candidate_name, cv_skills, matched_skills, skill_match_ratio, matched_sections, avg_similarity, cv_experience, experience_similarity, total_similarity) in enumerate(sorted_cv_results[:10], start=1):
                cvs_data.append({
                    'rank': rank,
                    'filename': cv_file,
                    'candidate_name': candidate_name,
                    'full_score': round(total_similarity, 4),
                    'experience': cv_experience,
                    'cv_skills': ", ".join(cv_skills),
                    'matched_skills': ", ".join(matched_skills)
                })

            return cvs_data
        else:
            logging.warning("No Skills or Requirements section found in the job description.")
            return []
        
    except Exception as e:
        logging.error(f"Error in analyze_cvs: {e}")
        return []
 