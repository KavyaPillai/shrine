import pandas as pd

# Step 1: Load CSVs
registration_df = pd.read_csv("registration.csv")
paytm_df = pd.read_csv("AprilPaytm.csv")
icici_df = pd.read_csv("AprilICICI.csv")

# Step 2: Clean column names for uniformity
registration_df.columns = registration_df.columns.str.strip()
paytm_df.columns = paytm_df.columns.str.strip()
icici_df.columns = icici_df.columns.str.strip()

# Step 3: User Input
first_name_input = input("Enter First Name: ").strip().lower()
last_name_input = input("Enter Last Name: ").strip().lower()

# Step 4: Search and Score
results = []

for _, row in registration_df.iterrows():
    full_name = str(row["STUDENTS NAME"]).strip()
    parts = full_name.split()
    first_name = parts[0].lower() if parts else ""
    last_name = parts[-1].lower() if len(parts) > 1 else ""

    confidence = 0
    breakdown = {}

    # Check First Name
    if first_name == first_name_input:
        confidence += 20
        breakdown["first_name"] = 20
    else:
        breakdown["first_name"] = 0

    # Check Last Name
    if last_name == last_name_input:
        confidence += 10
        breakdown["last_name"] = 10
    else:
        breakdown["last_name"] = 0

    # Mobile Match
    reg_mobile = str(row.get("MOBILE NUM", "")).strip()
    paytm_match = paytm_df["Payment_Mobile_Number"].astype(str).str.strip().str.contains(reg_mobile).any()
    icici_match = icici_df["Transaction Remarks"].astype(str).str.contains(reg_mobile).any()

    if paytm_match or icici_match:
        confidence += 50
        breakdown["mobile"] = 50
    else:
        breakdown["mobile"] = 0

    # Email Match (optional, if you'd like to expand)
    email = str(row.get("E.M@IL", "")).strip().lower()
    paytm_email_match = paytm_df["Payment_Email_Id"].astype(str).str.lower().str.contains(email).any()
    if email and paytm_email_match:
        confidence += 20
        breakdown["email"] = 20
    else:
        breakdown["email"] = 0

    if confidence > 0:
        results.append({
            "Student Name": full_name,
            "Fees Paid": "Yes" if (paytm_match or icici_match) else "No",
            "Confidence Points": confidence,
            "Breakdown": breakdown
        })

# Step 5: Show Results
if results:
    print("\n--- Matching Students ---\n")
    for i, res in enumerate(results, 1):
        print(f"{i}. {res['Student Name']} | Fees: {res['Fees Paid']} | Points: {res['Confidence Points']}")
        view_breakdown = input("Show confidence breakdown? (y/n): ").strip().lower()
        if view_breakdown == "y":
            print(res["Breakdown"])
        print()
else:
    print("No matches found.")
