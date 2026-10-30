import pandas as pd
import numpy as np

class AICustomerSegmentationAgent:
    def __init__(self, file_path):
        self.file_path = file_path

    def run_pipeline(self, output_path="web_campaign_results.csv", min_discount=2.0, max_discount=25.0):
        # Load dataset safely
        if self.file_path.endswith('.csv'):
            df = pd.read_csv(self.file_path)
        else:
            df = pd.read_excel(self.file_path)
            
        # Ensure required columns exist
        if 'CustomerID' not in df.columns:
            possible_id_cols = [col for col in df.columns if 'id' in col.lower() or 'customer' in col.lower()]
            if possible_id_cols:
                df['CustomerID'] = df[possible_id_cols[0]]
            else:
                df['CustomerID'] = range(101, 101 + len(df))
                
        if 'Recency' not in df.columns:
            df['Recency'] = np.random.randint(1, 60, size=len(df))
        if 'Frequency' not in df.columns:
            df['Frequency'] = np.random.randint(1, 15, size=len(df))
        if 'Monetary' not in df.columns:
            spend_cols = [col for col in df.columns if 'spend' in col.lower() or 'amount' in col.lower() or 'revenue' in col.lower() or 'total' in col.lower()]
            if spend_cols:
                df['Monetary'] = df[spend_cols[0]]
            else:
                df['Monetary'] = np.random.uniform(50, 3000, size=len(df))

        # Assign Customer Segments based on RFM-style thresholds
        conditions = [
            (df['Monetary'] > df['Monetary'].quantile(0.75)),
            (df['Monetary'] > df['Monetary'].quantile(0.4)),
            (df['Recency'] > 30)
        ]
        choices = ['Champions', 'Loyal Customers', 'At Risk']
        df['Segment'] = np.select(conditions, choices, default='New Customers')

        # Normalize metrics for behavioral calculations
        min_m, max_m = df['Monetary'].min(), df['Monetary'].max()
        monetary_range = (max_m - min_m) if (max_m - min_m) > 0 else 1.0

        discounts = []
        messages = []

        for _, row in df.iterrows():
            seg = row['Segment']
            cust_id = row['CustomerID']
            monetary = row['Monetary']
            frequency = row['Frequency']
            recency = row['Recency']
            
            # Behavioral score factors (normalized between 0 and 1)
            monetary_score = (monetary - min_m) / monetary_range
            freq_factor = min(frequency / 20.0, 1.0)
            recency_factor = min(recency / 60.0, 1.0)

            # --- DYNAMIC BEHAVIORAL DISCOUNT CALCULATION ---
            if seg == 'Champions':
                discount = round(3.0 + (monetary_score * 6.0), 1)
                messages.append(f"Hi #{cust_id}, as a top champion with ${monetary:,.2f} in lifetime value, enjoy exclusive early access and a tailored {discount}% reward voucher!")
            elif seg == 'Loyal Customers':
                discount = round(5.0 + (freq_factor * 5.0) + (monetary_score * 5.0), 1)
                messages.append(f"Thank you for your frequent visits (Frequency: {frequency}), #{cust_id}! Here is a personalized {discount}% loyalty reward to celebrate your support.")
            elif seg == 'At Risk':
                discount = round(10.0 + (recency_factor * 10.0) + (monetary_score * 5.0), 1)
                messages.append(f"We miss you, #{cust_id}! It's been {recency} days since your last order. Come back with this special {discount}% winback offer.")
            else:
                discount = round(8.0 + (monetary_score * 12.0), 1)
                messages.append(f"Welcome to our platform, #{cust_id}! Explore more of our collection with your customized {discount}% welcome voucher.")

            # Clamp discount between user-defined minimum and maximum limits
            discount = max(min_discount, min(discount, max_discount))
            discounts.append(discount)

        df['Assigned_Discount_%'] = discounts
        df['Automated_Message'] = messages

        df.to_csv(output_path, index=False)
        return df