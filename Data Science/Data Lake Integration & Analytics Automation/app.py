import streamlit as st
import pandas as pd
import pickle

# Load trained XGBoost model
with open("xgb.pkl", "rb") as f:
    model = pickle.load(f)

model_features = [
    'amount', 'num_cards_issued', 'credit_limit', 'current_age',
    'retirement_age', 'per_capita_income', 'yearly_income', 'total_debt',
    'credit_score', 'num_credit_cards',
    'is_weekend', 'high_value_tx', 'amount_to_limit_ratio',
    'transactions_per_day', 'card_dark_web_flag', 'errors_freq',
    'payment_method_Online Transaction', 'payment_method_Swipe Transaction',
    'card_brand_Discover', 'card_brand_Mastercard', 'card_brand_Visa',
    'card_type_Debit', 'card_type_Debit (Prepaid)', 'has_chip_YES',
    'gender_Male', 'cost_center_Debit', 'cost_center_Debit (Prepaid)'
]

binary_features = [
    'is_weekend', 'high_value_tx', 'card_dark_web_flag',
    'card_type_Debit', 'card_type_Debit (Prepaid)',
    'has_chip_YES', 'gender_Male',
    'cost_center_Debit', 'cost_center_Debit (Prepaid)'
]

numeric_features = [
    'amount', 'num_cards_issued', 'credit_limit', 'current_age',
    'retirement_age', 'per_capita_income', 'yearly_income',
    'total_debt', 'credit_score', 'num_credit_cards',
    'amount_to_limit_ratio', 'transactions_per_day', 'errors_freq'
]

st.set_page_config(page_title="Fraud Detection App", layout="wide")

st.title("Credit Card Fraud Detection")
st.write("Upload a CSV/Excel file or manually enter transaction details.")

uploaded_file = st.file_uploader(
    "Upload Excel (.xlsx) or CSV file",
    type=["xlsx", "csv"]
)

if uploaded_file is not None:

    if uploaded_file.name.endswith(".xlsx"):
        input_df = pd.read_excel(uploaded_file)
    else:
        input_df = pd.read_csv(uploaded_file)

    st.write("Preview of uploaded data:")
    st.dataframe(input_df.head())

    for col in model_features:
        if col not in input_df.columns:
            input_df[col] = 0

    input_df = input_df[model_features]

    predictions = model.predict(input_df)
    probabilities = model.predict_proba(input_df)[:, 1]

    input_df["Fraud_Prediction"] = predictions
    input_df["Fraud_Probability"] = probabilities

    st.success("Predictions completed.")
    st.dataframe(input_df.head())

    csv = input_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download Predictions",
        data=csv,
        file_name="fraud_predictions.csv",
        mime="text/csv"
    )

st.subheader("Manual Transaction Prediction")

manual_input = {}

col1, col2 = st.columns(2)

for i, feature in enumerate(numeric_features):
    if i % 2 == 0:
        manual_input[feature] = col1.number_input(feature, value=0.0)
    else:
        manual_input[feature] = col2.number_input(feature, value=0.0)

st.markdown("Binary Features")

for feature in binary_features:
    choice = st.selectbox(feature, ["No", "Yes"])
    manual_input[feature] = 1 if choice == "Yes" else 0

st.markdown("Payment Details")

payment_method = st.selectbox(
    "Payment Method",
    ["Online Transaction", "Swipe Transaction"]
)

manual_input['payment_method_Online Transaction'] = 0
manual_input['payment_method_Swipe Transaction'] = 0
manual_input[f'payment_method_{payment_method}'] = 1

card_brand = st.selectbox(
    "Card Brand",
    ["Discover", "Mastercard", "Visa"]
)

manual_input['card_brand_Discover'] = 0
manual_input['card_brand_Mastercard'] = 0
manual_input['card_brand_Visa'] = 0
manual_input[f'card_brand_{card_brand}'] = 1

if st.button("Predict Fraud Risk"):

    manual_df = pd.DataFrame([manual_input])
    manual_df = manual_df[model_features]

    prediction = model.predict(manual_df)[0]
    probability = model.predict_proba(manual_df)[0, 1]

    st.markdown("Result")

    if prediction == 1:
        st.error("High Fraud Risk Detected")
    else:
        st.success("Low Fraud Risk")

    st.write(f"Fraud Probability: {probability * 100:.2f}%")