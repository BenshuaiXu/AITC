import streamlit as st
import PyPDF2
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from PIL import Image
import re


# Function to read PDF and extract text
def read_pdf(file):
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n"
    return text

# Function to chunk text
def chunk_text(text, chunk_size=300):
    words = text.split()
    return [' '.join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]

# Function to precompute TF-IDF vectors for text chunks
def vectorize_text_chunks(text_chunks):
    vectorizer = TfidfVectorizer().fit(text_chunks)
    tfidf_chunks = vectorizer.transform(text_chunks)
    return vectorizer, tfidf_chunks

# Function to find the most similar chunks
def find_most_similar_chunks(user_query, vectorizer, tfidf_chunks, text_chunks, top_n=4):
    tfidf_query = vectorizer.transform([user_query])
    similarities = cosine_similarity(tfidf_query, tfidf_chunks)
    most_similar_indices = np.argsort(similarities[0])[-top_n:][::-1]
    return [text_chunks[i] for i in most_similar_indices]
