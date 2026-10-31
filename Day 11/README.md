# Day 11: Classification Models & Supervised Learning

**Date:** 30/10/2026  
**Status:** Completed 

---

## Learning Objectives

* **Regression to Classification Transition**: Understand how to binarize continuous target variables (such as sales data) into discrete categorical outcomes using median thresholds.
* **Logistic Regression Pipeline**: Build, train, and evaluate a Logistic Regression classification model incorporating feature scaling via `StandardScaler` and confusion matrix evaluation.
* **Decision Tree Classifier**: Implement non-linear decision tree models, visualize classification metrics, and extract key feature importances.

---

## Tasks Completed

* **Target Variable Transformation**: Prepared the dataset by converting the continuous `Sales` target variable into a binary classification format (`High Sales` vs `Low Sales`).
* **Logistic Regression Execution**: Configured and trained a scaled Logistic Regression pipeline, generating predictions validated through detailed classification reports and accuracy scores.
* **Decision Tree Implementation**: Tuned a Decision Tree Classifier (`max_depth=4`) to handle multi-feature interactions natively without feature standardization.
* **Confusion Matrix Visualization**: Generated and customized Seaborn heatmaps to clearly inspect true versus predicted classification distributions for both models.
* **Feature Importance Analysis**: Evaluated model weights and feature importances, confirming that **TV** advertising budget is the primary driver of sales performance compared to Radio and Newspaper channels.

---

## Deliverables & Repository Updates

* **Jupyter Notebook (`SalesPrediction.ipynb`)**: Updated with clean cell-wise markdown documentation, code implementations, and visual outputs.
* **Performance Insights**: Confusion matrices and comparative feature metrics successfully reviewed, analyzed, and integrated into the repository.
