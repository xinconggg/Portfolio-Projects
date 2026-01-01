# Drivers of Customer Retention and Repeat Purchase in Telco

## Project Overview
Customer retention is a key metric for telecom companies, as acquiring new customers is **5–25x more expensive than retaining existing ones**. While marketing and retention teams often rely on correlations, these metrics can be misleading due to confounding factors like demographics, engagement, and service usage.  

This project applies **causal inference techniques** to identify the **true drivers of customer churn and repeat usage**, using the [Telco Customer Churn dataset](https://community.ibm.com/community/user/businessanalytics/blogs/steven-macko/2019/07/11/telco-customer-churn-1113) from IBM. By isolating causal effects, we can recommend **data-driven retention strategies** that maximize customer lifetime value (CLTV).

---

## Problem Statement
**Primary Objective:**  
Determine the **causal impact** of service and marketing interventions on customer churn (or retention) while controlling for confounding variables.  

**Primary Causal Question:**  
*“Does offering specific promotions, contract plans, or services reduce the probability of customer churn in the following month?”*

**Secondary Questions:**  
- Which customer segments are most responsive to promotions or service changes?  
- How do engagement metrics (e.g., online services, call usage) modify treatment effects?  

---

## Dataset Description

**Dataset Source:** IBM – [Telco Customer Churn](https://community.ibm.com/community/user/businessanalytics/blogs/steven-macko/2019/07/11/telco-customer-churn-1113)

The dataset tracks a fictional telecom company's **customer churn** with multiple dimensions, including demographics, service usage, engagement, and churn outcomes.  

### Key Tables / Columns:

#### 1. Demographics (Telco_customer_churn_demographics.xlsx)
- `CustomerID`: Unique identifier  
- `Gender`, `Age`, `SeniorCitizen`, `Married`  
- `Dependents`, `NumberOfDependents`

#### 2. Location (Telco_customer_churn_location.xlsx)
- `Country`, `State`, `City`, `ZipCode`, `Latitude`, `Longitude`

#### 3. Population (Telco_customer_churn_population.xlsx)
- `ZipCode`, `Population` (for area demographics)

#### 4. Services (Telco_customer_churn_services.xlsx)
- `TenureInMonths`, `Offer` (last marketing offer accepted)  
- Service subscriptions: `PhoneService`, `MultipleLines`, `InternetService`  
- Additional services: `OnlineSecurity`, `OnlineBackup`, `DeviceProtectionPlan`, `PremiumTechSupport`  
- Streaming: `StreamingTV`, `StreamingMovies`, `StreamingMusic`  
- Billing & usage: `MonthlyCharge`, `TotalCharges`, `AvgMonthlyGBDownload`, `UnlimitedData`, `Contract`, `PaymentMethod`, `PaperlessBilling`

#### 5. Status (Telco_customer_churn_status.xlsx)
- `ChurnLabel` / `ChurnValue`: Target variable (Yes/No, 1/0)  
- `CustomerStatus`: Churned / Stayed / Joined  
- `SatisfactionScore`, `SatisfactionScoreLabel`  
- `CLTV` & `CLTVCategory`  
- `ChurnCategory` & `ChurnReason`  

**Notes:** The dataset contains **treatment-like variables** (e.g., Offers, Contract type) and rich **covariates for causal inference**, making it ideal for analyzing churn interventions.

---

## Approach / Methodology

### 1. Data Preparation
- Define **treatment variable(s)**: e.g., `Offer` accepted, `Contract` type  
- Define **outcome variable**: `ChurnLabel` / `ChurnValue`  
- Identify **pre-treatment covariates**: demographics, service usage, engagement metrics  

### 2. Data Cleaning & Feature Engineering
- Handle missing values (`mean` for continuous, `"Unknown"` for categorical)  
- Encode categorical variables (`OneHotEncoder` or `pd.get_dummies`)  
- Scale numeric features (`StandardScaler`)  
- Create interaction or lag features if necessary  

### 3. Causal Inference Techniques
- **Propensity Score Matching (PSM)** – match treated vs. control on covariates  
- **Doubly Robust Estimation / IPW** – more robust if covariates are imbalanced  
- **DoWhy / EconML** – estimate heterogeneous treatment effects, perform robustness checks  

### 4. Model Implementation
- Estimate **Average Treatment Effect (ATE)** and **Conditional Average Treatment Effect (CATE)**  
- Validate covariate balance and assumptions  
- Perform **sensitivity analysis** and **placebo tests**  

### 5. Visualization & Dashboarding
- Plot propensity score distributions, treatment effect distributions  
- Show lift by customer segment (VIP, new, dormant)  
- Build interactive dashboards using **Plotly** or **Tableau**  

---
## Dataset Acknowledgements
- IBM Sample Dataset: Telco Customer Churn  
- Source: [IBM Community Blog](https://community.ibm.com/community/user/businessanalytics/blogs/steven-macko/2019/07/11/telco-customer-churn-1113)
---
