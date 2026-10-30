## Day 11: Classification & Regression Models
**Date:** October 30, 2026

---

### Learning Objectives
* **Model Implementation & Evaluation:** Implement, train, and evaluate multiple regression algorithms (**Linear Regression** and **Decision Tree Regressor**) on advertising sales data.
* **Algorithm Trade-off Analysis:** Understand key performance differences between linear and non-linear regression models using standard metrics ($R^2$ Score, MAE, and MSE).
* **Performance Visualization:** Build clear visual comparisons of actual vs. predicted values using line plots and benchmark model accuracy using bar charts.

---

### Tasks Completed

- [x] **Data Splitting:** Divided the cleaned dataset into feature matrix `X` (`TV`, `Radio`, `Newspaper`) and target variable `y` (`Sales`) using an **80-20 train-test split** (`train_test_split`).
- [x] **Linear Regression Baseline:** Built and evaluated a Linear Regression model, achieving a strong baseline $R^2$ score of **~0.90 – 0.91** with low error rates.
- [x] **Decision Tree Modeling:** Trained an unconstrained `DecisionTreeRegressor` model, achieving an $R^2$ score of **~0.85 – 0.89**.
- [x] **Prediction Plots:** Generated individual line graphs comparing actual vs. predicted sales across the first 50 test samples for both models.
- [x] **Comparative Evaluation:** Plotted a simple bar chart comparing $R^2$ accuracy scores side-by-side to highlight model selection trade-offs.

---

### Model Performance Summary

| Model | $R^2$ Score (Accuracy) | Key Characteristics |
| :--- | :---: | :--- |
| **Linear Regression** | **~0.90 – 0.91** | Smooth prediction curve; closely tracks actual linear sales trends with minimal gap. |
| **Decision Tree Regressor** | **~0.85 – 0.89** | Jagged, step-like predictions; shows slight variance/overfitting on unconstrained splits. |

---

### Status
- **Pipeline Execution:** Complete (Both Linear Regression and Decision Tree models trained and benchmarked successfully).
- **Visualizations:** Generated and verified.
- **Repository Maintenance:** Code, plots, and documentation committed to the main branch.
