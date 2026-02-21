import pandas as pd
import json

# Load Dataframes
def load_data(raw_path="data/raw/"):
    # Transaction Data
    transactions = pd.read_csv(raw_path + "transactions_data.csv")
    # Card Data
    cards = pd.read_csv(raw_path + "cards_data.csv")
    # Users Data
    users = pd.read_csv(raw_path + "users_data.csv")
    # MCC (Merchant Category Codes) Codes
    with open(raw_path + "mcc_codes.json") as f:
        mcc_codes = json.load(f)
    mcc_codes = pd.DataFrame(list(mcc_codes.items()), columns=['mcc_code', 'mcc_description'])
    # Fraud Labels
    with open(raw_path + "train_fraud_labels.json") as f:
        fraud_labels = json.load(f)
    fraud_labels = pd.DataFrame(list(fraud_labels['target'].items()), columns=['transaction_id', 'fraud_flag'])
    return transactions, cards, users, mcc_codes, fraud_labels

# Standardize & Clean Dataframes
def clean_transactions(transactions, cards, users, mcc_codes):
    # Rename Columns
    transactions = transactions.rename(columns={
        "id": "transaction_id",
        "date": "transaction_date",
        "use_chip": "payment_method",
        "merchant_id": "vendor_id",
        "mcc": "mcc_code"
    })
    
    # Convert `transaction_date` and `acct_open_date` to datetime
    transactions["transaction_date"] = pd.to_datetime(transactions["transaction_date"], errors="coerce")
    cards["acct_open_date"] = pd.to_datetime(cards["acct_open_date"], errors="coerce")
    
    # Clean amount (Remove $)
    datasets = {
        "transactions": transactions,
        "cards": cards,
        "users": users
    }
    for name, df in datasets.items():
        for col in df.columns:
            if df[col].dtype == "object":
                if df[col].str.contains(r"\$", na=False).any():
                    df[col] = (
                        df[col]
                        .replace(r"[\$,]", "", regex=True)
                        .astype(float)
                    )

    # Ensure mcc is string
    transactions["mcc_code"] = transactions["mcc_code"].astype(str)
    return transactions, cards, users, mcc_codes

def integrate_data(transactions, cards, users, mcc_codes, fraud_labels):
    # Merge transactions with cards
    cleaned_df = transactions.merge(cards, left_on="card_id", right_on="id", how="left", suffixes=("", "_card"))

    # Merge with users
    cleaned_df = cleaned_df.merge(users, left_on="client_id", right_on="id", how="left", suffixes=("", "_user"))

    # Map MCC descriptions
    mcc_dict = dict(zip(mcc_codes['mcc_code'], mcc_codes['mcc_description']))
    cleaned_df['mcc_description'] = cleaned_df['mcc_code'].map(mcc_dict)

    # Map fraud labels
    fraud_dict = dict(zip(fraud_labels['transaction_id'], fraud_labels['fraud_flag']))
    cleaned_df['fraud_flag'] = cleaned_df['transaction_id'].map(fraud_dict)

    return cleaned_df

def generate_synthetic_fields(df):
    df["invoice_number"] = ["INV-" + str(i).zfill(6) for i in range(1, len(df)+1)]
    df["currency"] = "USD"
    df["cost_center"] = df["card_type"].fillna("Unknown")
    return df

def inject_dirty_data(df, n_duplicates=10, n_missing_vendor=5):
    random_rows = df.sample(n=n_duplicates, replace=True).copy()
    df = pd.concat([df, random_rows], ignore_index=True)
    rows_to_corrupt = df.sample(n_missing_vendor, random_state=42).index
    df.loc[rows_to_corrupt, "vendor_id"] = None
    return df