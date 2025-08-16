"""
Transaction Reconciler: Reconcile Paytm, ICICI, and Registration data.

This module provides functionality to match transaction records from
payment platforms with student registration data based on various
identifiers like names, mobile numbers, and email addresses.
"""

import argparse
import pandas as pd
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

# Global key database for storing registration data
KEY_DB = {}
THRESHOLD = 0


class Logger:
    """Simple logger class for transaction processing."""
    
    def __init__(self, filename: str, prefix: str = "", date: bool = True):
        """
        Initialize logger.
        
        Args:
            filename: Name of the log file
            prefix: Prefix for log messages
            date: Whether to include date in log messages
        """
        self.filename = filename
        self.prefix = prefix
        self.date = date
        print(f"Starting {filename} log")

    def log(self, message: str, *var_tuple: Any) -> None:
        """
        Log a message with optional additional variables.
        
        Args:
            message: Main log message
            *var_tuple: Additional variables to log
        """
        separator = "\t"
        
        if self.prefix:
            message = f"{self.prefix}{separator}{message}"
            
        if self.date:
            now = datetime.now()
            dt_string = now.strftime("%Y/%m/%d %H:%M:%S")
            message = f"{dt_string}{separator}{message}"
            
        for token in var_tuple:
            if token is not None:
                message = f"{message}{separator}{token}"


class Registration:
    """Handle student registration data and build key database."""
    
    def __init__(self, file_path: str, headers: str):
        """
        Initialize registration processor.
        
        Args:
            file_path: Path to registration CSV file
            headers: CSV headers (unused but kept for compatibility)
        """
        print("Code Flow: utils - In init")
        self.attr = 0
        self._read_registration_csv_to_table(file_path, headers)

    def _read_registration_csv_to_table(self, file_path: str, headers: str) -> None:
        """
        Read registration CSV and populate key database.
        
        Args:
            file_path: Path to CSV file
            headers: CSV headers (unused but kept for compatibility)
        """
        print("Code Flow: utils - Reading CSV")
        
        # Define data types for consistent reading
        dtype_mapping = {
            "SL.NO": str,
            "STUDENTS NAME": str, 
            "PARENTS NAME": str,
            "MOBILE NUM": str,
            "ALTERNATIVE NUM": str,
            "E.M@IL": str
        }
        
        data = pd.read_csv(file_path, dtype=dtype_mapping)

        # Extract columns as lists
        reg_ids = data["SL.NO"].tolist()
        student_names = data['STUDENTS NAME'].tolist()
        parent_names = data["PARENTS NAME"].tolist()
        mobile_numbers = data["MOBILE NUM"].tolist()
        alternate_numbers = data["ALTERNATIVE NUM"].tolist()
        email_addresses = data["E.M@IL"].tolist()

        # Process different data types
        self._teach_names(reg_ids, student_names, "")
        self._teach_names(reg_ids, parent_names, "P_")
        self._teach_mobiles(reg_ids, mobile_numbers)
        self._teach_mobiles(reg_ids, alternate_numbers)
        self._teach_emails(reg_ids, email_addresses)

    def _teach_mobiles(self, reg_ids: List[str], mobiles: List[str]) -> None:
        """
        Process mobile numbers for all registrations.
        
        Args:
            reg_ids: List of registration IDs
            mobiles: List of mobile numbers
        """
        for i in range(len(mobiles)):
            self._teach_mobile(reg_ids[i], mobiles[i])

    def _teach_mobile(self, reg_id: str, mobile: str) -> None:
        """
        Process a single mobile number and add to key database.
        
        Args:
            reg_id: Registration ID
            mobile: Mobile number string
        """
        if pd.isna(reg_id) or pd.isna(mobile):
            return
            
        # Clean phone number string
        phone_str = re.sub("[^0-9,+]+", '', mobile)
        phone_list = phone_str.split(',')
        
        for phone in phone_list:
            if len(phone) > 11:
                # Handle international numbers
                if phone.startswith("+") and phone[:-10] != "+91":
                    self._add_key(reg_id, phone[:-10], "INT", 20)
                phone = phone[-10:]  # Get last 10 digits
                
            if len(phone) == 10:
                self._add_key(reg_id, phone, "MOB", 50)
                self._add_key(reg_id, phone[-4:], "MOBL4", 20)

    def _teach_names(self, reg_ids: List[str], names: List[str], 
                    type_prefix: str) -> None:
        """
        Process names for all registrations.
        
        Args:
            reg_ids: List of registration IDs
            names: List of names
            type_prefix: Prefix for name types (e.g., "P_" for parent)
        """
        for i in range(len(names)):
            self._teach_name(reg_ids[i], names[i], type_prefix)

    def _teach_name(self, reg_id: str, name: str, type_prefix: str) -> None:
        """
        Process a single name and add to key database.
        
        Args:
            reg_id: Registration ID
            name: Name string
            type_prefix: Prefix for name type
        """
        if pd.isna(reg_id) or pd.isna(name):
            return
            
        if isinstance(name, str):
            name_type = ""
            confidence = 0
            
            for j, part in enumerate(name.lower().split()):
                if len(part) > 2:
                    if name_type == "":
                        name_type = f"{type_prefix}FNAME"
                        confidence = 20
                    elif name_type == f"{type_prefix}FNAME":
                        name_type = f"{type_prefix}LNAME"
                        confidence = 10
                    self._add_key(reg_id, part, name_type, confidence)

    def _add_key(self, key: str, value: str, key_type: str, 
                confidence: int) -> None:
        """
        Add a key-value pair to the global key database.
        
        Args:
            key: Registration ID
            value: Value to store
            key_type: Type of the value
            confidence: Confidence score
        """
        if key not in KEY_DB:
            KEY_DB[key] = []
        KEY_DB[key].append([value, key_type, confidence])

    def print_key_db(self) -> None:
        """Print the entire key database for debugging."""
        for key in KEY_DB:
            print(key)
            for entry in KEY_DB[key]:
                print(f"    {entry}")

    def _teach_emails(self, reg_ids: List[str], emails: List[str], 
                     type_prefix: str = "") -> None:
        """
        Process email addresses for all registrations.
        
        Args:
            reg_ids: List of registration IDs
            emails: List of email addresses
            type_prefix: Prefix for email types (unused)
        """
        for i in range(len(emails)):
            self._teach_email(reg_ids[i], emails[i], type_prefix)

    def _teach_email(self, reg_id: str, email: str, type_prefix: str) -> None:
        """
        Process a single email address and add to key database.
        
        Args:
            reg_id: Registration ID
            email: Email address
            type_prefix: Prefix for email type (unused)
        """
        if pd.isna(reg_id) or pd.isna(email):
            return
            
        self._add_key(reg_id, email, "EMAIL", 50)
        
        # Extract username part of email (up to 7 characters)
        username_length = min(len(email.split('@')[0]), 7)
        self._add_key(reg_id, email[:username_length], "SEMAIL", 30)


class TransactionMatcher:
    """Match transaction records with registration data."""
    
    def __init__(self, file_path: str, headers: str, source: str = "Paytm"):
        """
        Initialize transaction matcher.
        
        Args:
            file_path: Path to transaction CSV file
            headers: CSV headers (unused but kept for compatibility)
            source: Source of transactions (Paytm or ICICI)
        """
        print(f"In {source} class")
        self.transactions: Dict[str, List] = {}
        self.confidence_breakdown: Dict[str, Dict[str, int]] = {}
        self.logger = Logger(f"{source.lower()}payments", source.lower(), False)
        self._read_transactions(file_path, headers, source)

    def _add_confidence_detail(self, reg_id: str, key_type: str, 
                              confidence: int) -> None:
        """
        Add confidence detail for a registration ID.
        
        Args:
            reg_id: Registration ID
            key_type: Type of match
            confidence: Confidence score
        """
        if reg_id not in self.confidence_breakdown:
            self.confidence_breakdown[reg_id] = {}
        if key_type not in self.confidence_breakdown[reg_id]:
            self.confidence_breakdown[reg_id][key_type] = 0
        self.confidence_breakdown[reg_id][key_type] += confidence

    def _read_transactions(self, file_path: str, headers: str, 
                          source: str) -> None:
        """
        Read transaction CSV file and process records.
        
        Args:
            file_path: Path to CSV file
            headers: CSV headers (unused)
            source: Source of transactions
        """
        print(f"In readTransactions for {source}")
        data = pd.read_csv(file_path)

        # Map ICICI columns to common schema
        if source == "ICICI":
            column_mapping = {
                "Cheque. No./Ref. No.": "Transaction_ID",
                "Transaction Date": "Transaction_Date",
                "Transaction Remarks": "AdditionalComments",
                "Deposit Amt (INR)": "Amount"
            }
            data.rename(columns=column_mapping, inplace=True)

            # Add placeholder columns for ICICI
            placeholder_columns = [
                "Customer_Nickname", "Payment_Mobile_Number", 
                "Payment_Email_Id", "Customer_VPA"
            ]
            for col in placeholder_columns:
                data[col] = None

        # Validate required columns
        required_columns = [
            "Transaction_ID", "Transaction_Date", "Customer_Nickname",
            "Payment_Mobile_Number", "Payment_Email_Id", "Amount",
            "Customer_VPA", "AdditionalComments"
        ]
        missing_columns = [c for c in required_columns if c not in data.columns]
        if missing_columns:
            raise KeyError(f"Missing columns in {source} file: {missing_columns}")

        # Process each transaction
        for i, row in data.iterrows():
            self._reconcile_transaction(
                row["Transaction_ID"],
                row["Transaction_Date"],
                row["Customer_Nickname"],
                row["Payment_Mobile_Number"],
                row["Payment_Email_Id"],
                row["Amount"],
                row["Customer_VPA"],
                row["AdditionalComments"],
                source
            )

    def _reconcile_transaction(self, transaction_id: str, transaction_date: str,
                              nickname: str, mobile: str, email: str,
                              amount: float, customer_vpa: str, comment: str,
                              source: str) -> None:
        """
        Reconcile a single transaction with registration data.
        
        Args:
            transaction_id: Unique transaction identifier
            transaction_date: Date of transaction
            nickname: Customer nickname
            mobile: Mobile number
            email: Email address
            amount: Transaction amount
            customer_vpa: Customer VPA
            comment: Additional comments
            source: Source of transaction
        """
        score = 0

        # Match nickname (Paytm only)
        name_match = self._find_name(nickname)
        if name_match:
            score += name_match[2]
            self._add_confidence_detail(name_match[0], name_match[1], name_match[2])
            self._store_transaction(
                name_match[0], score, transaction_date, transaction_id,
                nickname, mobile, email, customer_vpa, comment, amount, source
            )

        # Match masked mobile (Paytm only)
        mobile_match = self._find_mobile(mobile)
        if mobile_match:
            score += mobile_match[2]
            self._add_confidence_detail(mobile_match[0], mobile_match[1], mobile_match[2])
            self._store_transaction(
                mobile_match[0], score, transaction_date, transaction_id,
                nickname, mobile, email, customer_vpa, comment, amount, source
            )

        # Match by email, VPA, and comments
        all_matches = (self._find_email(email) + 
                      self._find_customer_vpa(customer_vpa) + 
                      self._find_comments(comment))
        
        for match in all_matches:
            score += match[1]
            self._add_confidence_detail(match[0], match[2], match[1])
            self._store_transaction(
                match[0], score, transaction_date, transaction_id,
                nickname, mobile, email, customer_vpa, comment, amount, source
            )

    def _store_transaction(self, reg_id: str, score: int, transaction_date: str,
                          transaction_id: str, nickname: str, mobile: str,
                          email: str, customer_vpa: str, comment: str,
                          amount: float, source: str) -> None:
        """
        Store a matched transaction.
        
        Args:
            reg_id: Registration ID
            score: Confidence score
            transaction_date: Date of transaction
            transaction_id: Transaction ID
            nickname: Customer nickname
            mobile: Mobile number
            email: Email address
            customer_vpa: Customer VPA
            comment: Comments
            amount: Transaction amount
            source: Source of transaction
        """
        transaction_record = [
            transaction_date, transaction_id, nickname, mobile, email,
            customer_vpa, comment, score, amount, source
        ]
        
        if reg_id not in self.transactions:
            self.transactions[reg_id] = [score]
        else:
            existing_score = self.transactions[reg_id][0]
            self.transactions[reg_id][0] = max(existing_score, score)
            
        self.transactions[reg_id].append(transaction_record)

    def _find_name(self, name: str) -> Optional[Tuple[str, str, int]]:
        """
        Find registration ID by matching name.
        
        Args:
            name: Name to search for
            
        Returns:
            Tuple of (reg_id, match_type, confidence) or None
        """
        if not pd.isna(name):
            for token in name.split():
                for key in KEY_DB:
                    for entry in KEY_DB[key]:
                        if self._compare_strings(token, entry[0]):
                            return (key, entry[1], entry[2])
        return None

    def _find_mobile(self, mobile: str) -> Optional[Tuple[str, str, int]]:
        """
        Find registration ID by matching masked mobile number.
        
        Args:
            mobile: Mobile number (possibly masked)
            
        Returns:
            Tuple of (reg_id, match_type, confidence) or None
        """
        if not pd.isna(mobile) and "****" in mobile:
            tokens = mobile.split("****")
            for key in KEY_DB:
                for entry in KEY_DB[key]:
                    if self._compare_strings(tokens[1], entry[0]):
                        return (key, entry[1], entry[2])
        return None

    def _find_email(self, email: str) -> List[Tuple[str, int, str]]:
        """
        Find registration IDs by matching email.
        
        Args:
            email: Email address
            
        Returns:
            List of (reg_id, confidence, match_type) tuples
        """
        return self._find_generic_match(email, "SEMAIL")

    def _find_customer_vpa(self, customer_vpa: str) -> List[Tuple[str, int, str]]:
        """
        Find registration IDs by matching customer VPA.
        
        Args:
            customer_vpa: Customer VPA
            
        Returns:
            List of (reg_id, confidence, match_type) tuples
        """
        return self._find_generic_match(customer_vpa, "SEMAIL")

    def _find_comments(self, comments: str) -> List[Tuple[str, int, str]]:
        """
        Find registration IDs by matching comments.
        
        Args:
            comments: Transaction comments
            
        Returns:
            List of (reg_id, confidence, match_type) tuples
        """
        return self._find_generic_match(comments, "SEMAIL")

    def _find_generic_match(self, field: str, 
                           key_type: str) -> List[Tuple[str, int, str]]:
        """
        Find registration IDs by generic string matching.
        
        Args:
            field: Field value to search
            key_type: Type of key to match
            
        Returns:
            List of (reg_id, confidence, match_type) tuples
        """
        matches = []
        if not pd.isna(field):
            token = field.split('@')[0].split("****")[0]
            for key in KEY_DB:
                for entry in KEY_DB[key]:
                    if self._has_substring(token, entry[0]):
                        matches.append((key, entry[2], entry[1]))
        return matches

    def _compare_strings(self, word1: str, word2: str) -> bool:
        """
        Compare two strings (case-insensitive exact match).
        
        Args:
            word1: First string
            word2: Second string
            
        Returns:
            True if strings match exactly (case-insensitive)
        """
        return word1.lower() == word2.lower()

    def _has_substring(self, word1: str, word2: str) -> bool:
        """
        Check if word2 is a substring of word1 (case-insensitive).
        
        Args:
            word1: String to search in
            word2: Substring to search for
            
        Returns:
            True if word2 is found in word1
        """
        return word2.lower() in word1.lower()

    def _get_student_name(self, reg_id: str) -> str:
        """
        Get formatted student name from registration ID.
        
        Args:
            reg_id: Registration ID
            
        Returns:
            Formatted student name or registration ID if no name found
        """
        first_name = ""
        last_name = ""
        
        if reg_id in KEY_DB:
            for entry in KEY_DB[reg_id]:
                if entry[1] == "FNAME":
                    first_name = entry[0].capitalize()
                elif entry[1] == "LNAME":
                    last_name = entry[0].capitalize()
                    
        full_name = f"{first_name} {last_name}".strip()
        return full_name if full_name else reg_id

    def print_final_report(self, output_file: str = "final_report.csv") -> None:
        """
        Generate and print final reconciliation report.
        
        Args:
            output_file: Output CSV file name
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        output_file = f"final_report_{timestamp}.csv"
        rows = []
        
        for reg_id, entries in self.transactions.items():
            score = entries[0]
            student_name = self._get_student_name(reg_id)
            confidence_detail = self.confidence_breakdown.get(reg_id, {})

            for transaction in entries[1:]:
                row = {
                    "Student Name": student_name,
                    "Registration ID": reg_id,
                    "Transaction ID": transaction[1],
                    "Transaction Date": transaction[0],
                    "Nickname": transaction[2],
                    "Mobile": transaction[3],
                    "Email": transaction[4],
                    "Customer VPA": transaction[5],
                    "Comments": transaction[6],
                    "Amount (₹)": transaction[8],
                    "Confidence Score": score,
                    "Confidence Breakdown": str(confidence_detail),
                    "Source": transaction[9]
                }
                rows.append(row)

        df = pd.DataFrame(rows)
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\nReport successfully written to {output_file}")


def main() -> None:
    """Main function to run the transaction reconciler."""
    parser = argparse.ArgumentParser(
        description="Reconcile Paytm, ICICI, and Registration data."
    )
    parser.add_argument(
        "--registration", 
        required=True, 
        help="Path to registration CSV file"
    )
    parser.add_argument(
        "--paytm", 
        required=True, 
        help="Path to Paytm CSV file"
    )
    parser.add_argument(
        "--icici", 
        required=True, 
        help="Path to ICICI CSV file"
    )

    args = parser.parse_args()

    # Initialize with empty headers (kept for compatibility)
    headers = ""
    
    # Process registration data
    registration_processor = Registration(args.registration, headers)
    registration_processor.print_key_db()

    # Process transaction data
    transaction_matcher = TransactionMatcher(args.paytm, headers, source="Paytm")
    transaction_matcher._read_transactions(args.icici, headers, source="ICICI")
    transaction_matcher.print_final_report("final_report.csv")


if __name__ == "__main__":
    main()