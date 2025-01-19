import json
import os
import pdb
import re
from snowflake.snowpark import Session
from dotenv import load_dotenv

load_dotenv()

def connect_to_snowflake():
    connection_params = {
        "account": os.getenv("SNOWFLAKE_ACCOUNT"),
        "user": os.getenv("SNOWFLAKE_USER"),
        "password": os.getenv("SNOWFLAKE_PASSWORD"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
        "database": os.getenv("SNOWFLAKE_DATABASE"),
        "schema": os.getenv("SNOWFLAKE_SCHEMA"),
    }
    session = Session.builder.configs(connection_params).create()
    return session

import re

def extract_category(input_string: str):
    # Define regex pattern to find the category
    pattern = r'"category":\s*"([^"]+)"'
    
    # Search for the pattern in the input string
    match = re.search(pattern, input_string)
    
    # If a match is found, return the category
    if match:
        return match.group(1)
    else:
        return "Category not found"



def classify_medicine(session, medicine_name):
    """
    Classifies a medicine name using Snowflake Cortex with Mistral LLM.
    Returns the category as a string.
    """
    prompt = """
You are a medical classification assistant. Given a chemical compound or drug, categorize it into one of the following categories mentioned only. Provide the category that best describes the drug's primary use and activity. If unsure, categorize it as 'Other'.

Categories:

    - Analgesic
    - Antibiotic
    - Antihistamine
    - Antipyretic
    - Antiseptic
    - Antidepressant
    - Anticonvulsant
    - Antifungal
    - Anesthetic
    - Antiviral
    - Anticancer
    - Antidiabetic
    - Antihypertensive
    - Antiplatelet
    - Anticoagulant
    - Antiemetic
    - Anxiolytic
    - Mood stabilizer
    - Immunosuppressant
    - Steroid
    - Vasodilator
    - Neuroprotective
    - Cognitive Enhancer
    - Nootropic
    - Mood Regulator
    - Cholinergic
    - Nutritional Supplements
    - Dermatology
    - Antimicrobial
    - Expectorant
    - Anti-inflammatory
    - Diuretic
    - Beta-blocker
    - Probiotic
    - Chemotherapy
    - Growth Hormone
    - Blood Thinner

For the keyword provided, categorize it into its corresponding category and return the result in the following JSON format:

{
    "category": "<category>",
}

"""

    query = session.sql(f"""
        SELECT TRIM(SNOWFLAKE.CORTEX.COMPLETE(
            'mistral-7B',
            '{prompt} {medicine_name}'
        ), '\\n') AS category
    """)
    result = query.collect()

    if result:
        # pdb.set_trace()
        category_json_str = result[0]["CATEGORY"]
        
        try:
            category = extract_category(category_json_str)
            return category
        except json.JSONDecodeError:
            return "Unknown"
    else:
        return "Unknown"

