import pandas as pd
import numpy as np
from copy import deepcopy
import math
import re
import argparse
from datetime import datetime

keydb = {}
paytmdb = {}
THRESHOLD = 0

class logger:
    def __init__(self, filename, prefix="", date=True):
        self.filename = filename
        self.prefix = prefix
        self.date = ""
        print("starting", filename, "log")

    def log(self, message, *vartuple):
        SEP = "\t"
        if self.prefix != "":
            message = str(self.prefix) + SEP + str(message)
        if self.date:
            now = datetime.now()
            dt_string = now.strftime("%Y/%m/%d %H:%M:%S") + SEP + message
        for token in vartuple:
            if token is not None:
                message = str(message) + SEP + str(token)
        # print(message)


class registration:
    def __init__(self, file, headers):
        print("Code Flow: utils - In init")
        self.attr = 0
        self.readRegCSVtoTable(file, headers)

    def readRegCSVtoTable(self, fl, headers):
        print("Code Flow: utils - Reading CSV")
        data = pd.read_csv(fl, dtype={"SL.NO": str, "STUDENTS NAME": str, "PARENTS NAME": str,
                                      "MOBILE NUM": str, "ALTERNATIVE NUM": str, "E.M@IL": str})
        reg = pd.Series(data["SL.NO"]).tolist()
        name = pd.Series(data['STUDENTS NAME']).tolist()
        parent = pd.Series(data["PARENTS NAME"]).tolist()
        mobile = pd.Series(data["MOBILE NUM"]).tolist()
        alternate = pd.Series(data["ALTERNATIVE NUM"]).tolist()
        mail = pd.Series(data["E.M@IL"]).tolist()
        self.teachNames(reg, name, "")
        self.teachNames(reg, parent, "P_")
        self.teachMobiles(reg, mobile)
        self.teachMobiles(reg, alternate)
        self.teachEmails(reg, mail)

    def teachMobiles(self, reg, mobiles):
        for i in range(len(mobiles)):
            self.teachMobile(reg[i], mobiles[i])

    def teachMobile(self, reg_id, mobile):
        if pd.isna(reg_id) or pd.isna(mobile):
            return
        phone_str = re.sub("[^0-9,+]+", '', mobile)
        phone_list = phone_str.split(',')
        for phone in phone_list:
            if len(phone) > 11:
                if phone.startswith("+") and phone[0:-10] != "+91":
                    self.addKey(reg_id, phone[0:-10], "INT", 20)
                phone = phone[-10:]
            if len(phone) == 10:
                self.addKey(reg_id, phone, "MOB", 50)
                self.addKey(reg_id, phone[-4:], "MOBL4", 20)

    def teachNames(self, reg, names, type_prefix):
        for i in range(len(names)):
            self.teachName(reg[i], names[i], type_prefix)

    def teachName(self, reg_id, name, type_prefix):
        if pd.isna(reg_id) or pd.isna(name):
            return
        if isinstance(name, str):
            type = ""
            confidence = 0
            for j, part in enumerate(name.lower().split()):
                if len(part) > 2:
                    if type == "":
                        type = type_prefix + "FNAME"
                        confidence = 20
                    elif type == type_prefix + "FNAME":
                        type = type_prefix + "LNAME"
                        confidence = 10
                    self.addKey(reg_id, part, type, confidence)

    def addKey(self, key, value, type, confidence):
        if key not in keydb:
            keydb[key] = []
        keydb[key].append([value, type, confidence])

    def printKeyDB(self):
        for key in keydb:
            print(key)
            for entry in keydb[key]:
                print("    " + str(entry))

    def teachEmails(self, reg, emails, type_prefix=""):
        for i in range(len(emails)):
            self.teachEmail(reg[i], emails[i], type_prefix)

    def teachEmail(self, reg_id, email, type_prefix):
        if pd.isna(reg_id) or pd.isna(email):
            return
        self.addKey(reg_id, email, "EMAIL", 50)
        ln = min(len(email.split('@')[0]), 7)
        self.addKey(reg_id, email[:ln], "SEMAIL", 30)


class paytm():
    def __init__(self, file, headers):
        print("In paytm class")
        self.transactions = {}
        self.confidence_breakdown = {}  # NEW
        self.l = logger("paytmpayments", "paytm", False)
        self.readPaytmTransactions(file, headers)

    def add_confidence_detail(self, reg_id, type, confidence):
        if reg_id not in self.confidence_breakdown:
            self.confidence_breakdown[reg_id] = {}
        if type not in self.confidence_breakdown[reg_id]:
            self.confidence_breakdown[reg_id][type] = 0
        self.confidence_breakdown[reg_id][type] += confidence

    def readPaytmTransactions(self, file, headers):
        print("In readPaytmTransactions")
        data = pd.read_csv(file)
        for i, row in data.iterrows():
            self.reconcileTransaction(
                row["Transaction_ID"],
                row["Transaction_Date"],
                row["Customer_Nickname"],
                row["Payment_Mobile_Number"],
                row["Payment_Email_Id"],
                row["Amount"],
                row["Customer_VPA"],
                row["AdditionalComments"]
            )

    def reconcileTransaction(self, transaction_id, transaction_date, nickname, mobile, email, amount, cust_vpa, comment):
        score = 0

        ret = self.findName(nickname)
        if ret:
            score += ret[2]
            self.add_confidence_detail(ret[0], ret[1], ret[2])
            self.storeTransaction(ret[0], score, transaction_date, transaction_id, nickname, mobile, email, cust_vpa, comment, amount)

        ret = self.findMobile(mobile)
        if ret:
            score += ret[2]
            self.add_confidence_detail(ret[0], ret[1], ret[2])
            self.storeTransaction(ret[0], score, transaction_date, transaction_id, nickname, mobile, email, cust_vpa, comment, amount)

        for ret in self.findEmail(email) + self.findCustomerVPA(cust_vpa) + self.findComments(comment):
            match = ret
            score += match[1]
            self.add_confidence_detail(match[0], match[2], match[1])
            self.storeTransaction(match[0], score, transaction_date, transaction_id, nickname, mobile, email, cust_vpa, comment, amount)

    def storeTransaction(self, reg_id, score, transaction_date, transaction_id, nickname, mobile, email, cust_vpa, comment, amount):
        txn = [transaction_date, transaction_id, nickname, mobile, email, cust_vpa, comment, score, amount]
        if reg_id not in self.transactions:
            self.transactions[reg_id] = [score]
        else:
            existing_score = self.transactions[reg_id][0]
            self.transactions[reg_id][0] = max(existing_score, score) 

        self.transactions[reg_id].append(txn) 


    def findName(self, name):
        if not pd.isna(name):
            for token in name.split():
                for key in keydb:
                    for entry in keydb[key]:
                        if self.compareStr(token, entry[0]):
                            return [key, entry[1], entry[2]]
        return None

    def findMobile(self, mobile):
        if not pd.isna(mobile) and "****" in mobile:
            tokens = mobile.split("****")
            for key in keydb:
                for entry in keydb[key]:
                    if self.compareStr(tokens[1], entry[0]):
                        return [key, entry[1], entry[2]]
        return None

    def findEmail(self, email):
        return self.findGeneric(email, "SEMAIL")

    def findCustomerVPA(self, customer_vpa):
        return self.findGeneric(customer_vpa, "SEMAIL")

    def findComments(self, comments):
        return self.findGeneric(comments, "SEMAIL")

    def findGeneric(self, field, keytype):
        ret_val = []
        if not pd.isna(field):
            token = field.split('@')[0].split("****")[0]
            for key in keydb:
                for entry in keydb[key]:
                    if self.hasStr(token, entry[0]):
                        ret_val.append([key, entry[2], entry[1]])
        return ret_val

    def compareStr(self, word1, word2):
        return word1.lower() == word2.lower()

    def hasStr(self, word1, word2):
        return word2.lower() in word1.lower()

    def getStudentName(self, reg_id):
        fname = lname = ""
        for entry in keydb[reg_id]:
            if entry[1] == "FNAME":
                fname = entry[0].capitalize()
            elif entry[1] == "LNAME":
                lname = entry[0].capitalize()
        return f"{fname} {lname}".strip() if fname or lname else reg_id

    def printFinalReport(self):
    	print("\n--- Final Report Grouped by Student ---\n")
    	for reg_id, entries in self.transactions.items():
            student_name = self.getStudentName(reg_id)
            total_score = entries[0]
            print(f"Student: {student_name} | Total Confidence: {total_score}")
            print("Transactions:")
            for txn in entries[1:]:
                amount = txn[8]
                print(f"  • ₹{amount} | TXN ID: {txn[1]} | Date: {txn[0]}")
            print(f"Confidence Breakdown: {self.confidence_breakdown.get(reg_id, {})}")
            print("---------------------------------------------------")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reconcile Paytm and Registration data.")
    parser.add_argument("--registration", required=True, help="Path to registration CSV file")
    parser.add_argument("--paytm", required=True, help="Path to paytm CSV file")

    args = parser.parse_args()

    reg_file = args.registration
    paytm_file = args.paytm

    g = ""
    r = registration(reg_file, g)
    r.printKeyDB()

    paytmdata = paytm(paytm_file, g)
    paytmdata.printFinalReport()
