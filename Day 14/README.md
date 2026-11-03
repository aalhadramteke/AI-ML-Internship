# Day 14: Weekly Mini Project : Basic Sentiment Analysis

**Date:** 03/11/2026

### Assigned Tasks:

#### Learning Objectives:

* **Select an appropriate dataset:** Define a text dataset suitable for basic sentiment classification.
* **Clean and preprocess the data:** Prepare text through lowercasing, tokenization, stopword removal, and TF-IDF vectorization.
* **Train at least one Machine Learning model:** Implement a supervised machine learning classifier (Logistic Regression) on numerical text features.
* **Evaluate the model using appropriate metrics:** Compute model performance using accuracy and prediction confidence scores.
* **Write a short explanation of your model's performance:** Analyze and summarize how effectively the model categorizes text sentiments.

#### Tasks Completed:

* **Dataset Selection & Labeling:** Selected a 10-sentence text corpus representing diverse emotional tones and assigned binary ground-truth labels (`Positive` and `Negative`).
* **Text Preprocessing Pipeline:** Standardized text via lowercasing, tokenized using NLTK `word_tokenize`, removed punctuation/stopwords, and extracted weighted numerical features using scikit-learn's `TfidfVectorizer`.
* **Model Training:** Initialized and trained a `LogisticRegression` classifier model using the generated TF-IDF feature matrix (`tfidf_matrix`).
* **Evaluation & Metric Computation:** Evaluated classifier predictions against true labels and calculated overall training accuracy.
* **Performance Analysis:** Summarized model behavior, highlighting how TF-IDF feature weights and decision boundaries (0.50 probability threshold) determine positive vs. negative predictions.

### Status:

* Dataset preprocessing, sentiment labeling, and model training successfully completed.
* Model evaluation and performance explanation documented.
* Jupyter Notebook updated with the complete Sentiment Analysis workflow.
* GitHub repository updated with the final project code and report.
