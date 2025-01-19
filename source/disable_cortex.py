import snowflake.connector
import os
from dotenv import load_dotenv

load_dotenv()

# Load Snowflake credentials
SNOWFLAKE_USER = os.getenv('SNOWFLAKE_USER')
SNOWFLAKE_PASSWORD = os.getenv('SNOWFLAKE_PASSWORD')
SNOWFLAKE_ACCOUNT = os.getenv('SNOWFLAKE_ACCOUNT')
SNOWFLAKE_DATABASE = os.getenv('SNOWFLAKE_DATABASE')
SNOWFLAKE_SCHEMA = os.getenv('SNOWFLAKE_SCHEMA')
SNOWFLAKE_WAREHOUSE = os.getenv('SNOWFLAKE_WAREHOUSE')

DROP_CORTEX_SERVICE_SQL = """
DROP CORTEX SEARCH SERVICE drug_data_search_service;
"""

def connect_to_snowflake():
    return snowflake.connector.connect(
        user=SNOWFLAKE_USER,
        password=SNOWFLAKE_PASSWORD,
        account=SNOWFLAKE_ACCOUNT,
        warehouse=SNOWFLAKE_WAREHOUSE,
        database=SNOWFLAKE_DATABASE,
        schema=SNOWFLAKE_SCHEMA,
    )

def drop_cortex_service():
    try:
        conn = connect_to_snowflake()
        cursor = conn.cursor()
        print("Connected to Snowflake.")
        print("Dropping Cortex Search Service...")
        cursor.execute(DROP_CORTEX_SERVICE_SQL)
        print("Cortex Search Service dropped successfully.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    drop_cortex_service()
