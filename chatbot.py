import os
import json
import datetime
import csv
import nltk
import ssl
import streamlit as st
import random
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

# --- Step 1: Library and Data Setup ---
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

nltk.data.path.append(os.path.abspath("nltk_data"))
try:
    if not os.path.exists(os.path.join(os.path.abspath("nltk_data"), 'tokenizers', 'punkt')):
        nltk.download('punkt', download_dir=os.path.abspath("nltk_data"))
except Exception as e:
    st.error(f"NLTK punkt download failed: {e}")
    st.stop()

# Load intents from the JSON file
file_path = os.path.abspath("./intents.json")
try:
    with open(file_path, "r") as file:
        intents = json.load(file)
except FileNotFoundError:
    st.error(f"Error: intents.json not found at {file_path}")
    st.stop()
except json.JSONDecodeError:
    st.error(f"Error: Could not decode intents.json. Please check its format.")
    st.stop()

# --- Step 2: Model Training ---
vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
clf = LogisticRegression(random_state=0, max_iter=10000, solver='liblinear')

# Preprocess the data
tags = []
patterns = []
for intent in intents:
    for pattern in intent['patterns']:
        tags.append(intent['tag'])
        patterns.append(pattern)

# Training the model
if len(patterns) > 0 and len(tags) > 0:
    x = vectorizer.fit_transform(patterns)
    y = tags
    clf.fit(x, y)
else:
    st.error("Error: No patterns found in intents.json. Please populate the file.")
    st.stop()

# --- Step 3: Enhanced Chatbot Functionality ---
def get_chatbot_response(input_text):
    if not input_text:
        return random.choice(["Please enter a message.", "What can I help you with?"])
    
    input_text_vec = vectorizer.transform([input_text])
    
    # Get prediction and confidence score
    probabilities = clf.predict_proba(input_text_vec)[0]
    max_prob = np.max(probabilities)
    predicted_tag = clf.classes_[np.argmax(probabilities)]
    
    # Confidence threshold for better responses
    confidence_threshold = 0.5 
    
    # If confidence is below threshold, use a fallback 'unknown' tag
    if max_prob < confidence_threshold:
        fallback_tag = 'unknown' 
        for intent in intents:
            if intent['tag'] == fallback_tag:
                return random.choice(intent['responses'])
    
    # Otherwise, use the predicted tag
    for intent in intents:
        if intent['tag'] == predicted_tag:
            return random.choice(intent['responses'])

    # Fallback if the tag is not found for some reason
    return "I'm sorry, I seem to be having a bit of trouble. Please try again."

counter = 0

# --- Step 4: Streamlit Web Interface ---
def main():
    global counter
    
    st.set_page_config(page_title="Intents of Chatbot using NLP", layout="wide")

    page_bg_img = """
<style>
[data-testid="stAppViewContainer"] {
background-color: #ADD8E6;
background-image: none;
}
</style>
"""
    st.markdown(page_bg_img, unsafe_allow_html=True)
    st.title("Intents of Chatbot using NLP 🤖")
    
    menu = ["Home", "Conversation History", "About"]
    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "Home":
        st.write("Welcome to the chatbot. Please type a message to start the conversation.")

        if not os.path.exists('chat_log.csv'):
            with open('chat_log.csv', 'w', newline='', encoding='utf-8') as csvfile:
                csv_writer = csv.writer(csvfile)
                csv_writer.writerow(['User Input', 'Chatbot Response', 'Timestamp'])

        counter += 1
        user_input = st.text_input("You:", key=f"user_input_{counter}")

        if user_input:
            user_input_str = str(user_input)
            response = get_chatbot_response(user_input)
            
            st.text_area("Chatbot:", value=response, height=120, max_chars=None, key=f"chatbot_response_{counter}")
            
            timestamp = datetime.datetime.now().strftime(f"%Y-%m-%d %H:%M:%S")
            with open('chat_log.csv', 'a', newline='', encoding='utf-8') as csvfile:
                csv_writer = csv.writer(csvfile)
                csv_writer.writerow([user_input_str, response, timestamp])

            if response.lower() in ['goodbye', 'bye', 'take care']:
                st.write("Thank you for chatting with me. Have a great day!")
                st.stop()
        elif user_input.strip() == "":
             st.info("Please enter a valid message to get a response!")

    elif choice == "Conversation History":
        st.header("Conversation History 📖")
        if not os.path.exists('chat_log.csv'):
            st.info("No conversation history found.")
        else:
            with open('chat_log.csv', 'r', encoding='utf-8') as csvfile:
                csv_reader = csv.reader(csvfile)
                try:
                    header = next(csv_reader)
                    rows = list(csv_reader)
                    if not rows:
                        st.info("No conversation history found.")
                    else:
                        for row in reversed(rows):
                            if len(row) >= 3:
                                st.text(f"User: {row[0]}")
                                st.text(f"Chatbot: {row[1]}")
                                st.text(f"Timestamp: {row[2]}")
                                st.markdown("---")
                except StopIteration:
                    st.info("No conversation history found.")


    elif choice == "About":
        st.header("About This Chatbot Project 🧐")
        st.write("""
        The goal of this project is to create a chatbot that can understand and respond to user input based on a predefined set of intents. The chatbot is built using Natural Language Processing (NLP) techniques and a machine learning model, and its interface is powered by Streamlit.
        """)
        st.subheader("Project Overview:")
        st.write("""
        1. **NLP and Machine Learning**: The chatbot's core logic uses a **TF-IDF Vectorizer** to convert text into numerical data and a **Logistic Regression** classifier to predict the user's intent. To improve accuracy, the model now includes a confidence threshold to provide more relevant responses and a fallback mechanism for out-of-scope questions.
        2. **Streamlit Interface**: The web-based chatbot interface is built with Streamlit, a Python library for creating interactive applications. It features a simple design with a conversation history and an 'About' section to explain the project.
        """)
        st.subheader("Dataset:")
        st.write("""
        The chatbot's knowledge is stored in the `intents.json` file. Each entry contains:
        * **Intents**: The user's goal or purpose (e.g., "greeting", "budget", "about").
        * **Patterns**: Various phrases a user might use to express an intent.
        * **Responses**: The chatbot's potential replies for a given intent.
        """)
        st.subheader("Conclusion:")
        st.write("""
        This project demonstrates the fundamental principles of building an intent-based chatbot. By refining the training data and implementing a confidence-based response system, the chatbot's performance is significantly enhanced, allowing for more accurate and helpful conversations.
        """)
    
if __name__ == '__main__':
    main()