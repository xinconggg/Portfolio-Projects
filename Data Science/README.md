# [Causal Inference of Customer Retention in Telco](https://github.com/xinconggg/Portfolio-Projects/tree/main/Data%20Science/Causal%20Inference%20of%20Customer%20Retention%20in%20Telco)

---

## Project Overview
Customer retention is a critical business lever for telecom companies, where acquiring new customers is estimated to be **5–25× more expensive than retaining existing ones**.

However, traditional churn analyses often rely on **correlational metrics**, which can be misleading when customer interventions (e.g., promotions, contract offers) are **non-randomly assigned**.

This project applies **causal inference techniques** to estimate the **true causal impact of promotional offers on customer churn**, using observational telecom data. By correcting for selection bias and confounding, the analysis demonstrates how causal methods lead to **decision-ready insights** that go beyond standard predictive churn models.

---

## Business Problem & Causal Question

### Primary Business Objective
Evaluate whether promotional offers **causally reduce customer churn**, rather than merely being correlated with churn outcomes.

### Primary Causal Question
> **What is the causal effect of receiving a promotional offer on the probability of customer churn, after controlling for customer demographics, service usage, tenure, and value?**

### Why This Matters
Promotions are often targeted toward customers who are already at high risk of churning. Without causal adjustment, simple comparisons may incorrectly suggest that promotions *increase* churn—leading to flawed business decisions and misallocated marketing spend.

---

## Dataset Description

**Source:** IBM Sample Dataset – Telco Customer Churn  
🔗 https://community.ibm.com/community/user/businessanalytics/blogs/steven-macko/2019/07/11/telco-customer-churn-1113

The dataset contains **customer-level observational data** across five relational tables, enabling rich control for confounding variables.

### Data Tables
1. **Demographics** – age, gender, marital status, dependents  
2. **Location** – geographic attributes (state, zip code, latitude/longitude)  
3. **Population** – zip-code–level population context  
4. **Services** – tenure, promotions, service subscriptions, billing and usage  
5. **Status** – churn outcome, satisfaction score, CLTV, churn reasons  

This dataset is well suited for causal inference due to:
- Explicit treatment-like variables (e.g., promotional offers)
- Rich pre-treatment covariates
- A clearly defined binary churn outcome

---

## Methodology

### 1. Problem Setup & Data Preparation
- Defined **treatment**: whether a customer received a promotional offer  
- Defined **outcome**: customer churn (binary)  
- Selected **pre-treatment covariates** spanning demographics, service usage, tenure, billing, and customer value  

### 2. Exploratory Analysis & Selection Bias Assessment
- Compared treated vs. untreated customers  
- Identified systematic differences in tenure, CLTV, and engagement  
- Demonstrated why naive churn comparisons are biased  

### 3. Propensity Score Modeling
- Estimated treatment assignment probabilities using logistic regression  
- Verified **overlap and positivity assumptions**  
- Applied **1:1 nearest neighbor matching**  
- Assessed covariate balance using standardized mean differences  

### 4. Causal Effect Estimation
- Naive difference-in-means (baseline comparison)  
- Average Treatment Effect on the Treated (ATT) using matched samples  
- Inverse Probability Weighting (IPW)  
- Doubly Robust Estimation  

### 5. Robustness & Validation
- Consistency checks across multiple estimators  
- Sensitivity analysis for selection bias  
- Placebo outcome tests  

---

## Key Findings

- **Naive analysis suggested promotional offers increase churn**, driven by targeted assignment to high-risk customers  
- After causal adjustment, **promotional offers reduce churn by approximately 0.2–0.5 percentage points**  
- Results are **consistent across matching, IPW, and doubly robust estimators**  
- No strong evidence that promotions significantly affect satisfaction scores, suggesting churn reduction may operate through **financial or contractual mechanisms** rather than perceived satisfaction  

---

## Business Implications

- Promotional offers are **causally effective**, but the effect size is modest  
- Offers should be targeted toward **high-risk or high-CLTV segments** to maximize return on investment  
- Causal inference prevents costly misinterpretation of observational churn metrics  
- Demonstrates how causal methods complement traditional predictive churn models in production analytics  

---

## Tools & Libraries
- Python, Pandas, NumPy  
- scikit-learn  
- Causal inference techniques (PSM, IPW, Doubly Robust Estimation)  
- Matplotlib / Plotly  

---

## Acknowledgements
- IBM Sample Dataset: Telco Customer Churn  
- Source: IBM Community Blog  
