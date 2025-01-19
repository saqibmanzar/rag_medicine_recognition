import snowflake.connector
import os
from dotenv import load_dotenv

load_dotenv()

SNOWFLAKE_USER = os.getenv('SNOWFLAKE_USER')
SNOWFLAKE_PASSWORD = os.getenv('SNOWFLAKE_PASSWORD')
SNOWFLAKE_ACCOUNT = os.getenv('SNOWFLAKE_ACCOUNT')
SNOWFLAKE_DATABASE = os.getenv('SNOWFLAKE_DATABASE')
SNOWFLAKE_SCHEMA = os.getenv('SNOWFLAKE_SCHEMA')
WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE")  

# SQL command to create Cortex Search Service
CREATE_CORTEX_SERVICE_SQL = """
CREATE OR REPLACE CORTEX SEARCH SERVICE drug_data_search_service
  ON chunk
  ATTRIBUTES category
  WAREHOUSE = COMPUTE_WH
  TARGET_LAG = '1 day'
  EMBEDDING_MODEL = 'snowflake-arctic-embed-l-v2.0'
  AS (
    SELECT
        chunk,
        heading,
        category,
        record_title
    FROM DRUG_DATA
  );

"""

def connect_to_snowflake():
    return snowflake.connector.connect(
        user=SNOWFLAKE_USER,
        password=SNOWFLAKE_PASSWORD,
        account=SNOWFLAKE_ACCOUNT,
        warehouse=WAREHOUSE,
        database=SNOWFLAKE_DATABASE,
        schema=SNOWFLAKE_SCHEMA,
    )

def create_cortex_service():
    try:
        conn = connect_to_snowflake()
        cursor = conn.cursor()
        print("Connected to Snowflake.")
        print("Creating Cortex Search Service...")
        cursor.execute(CREATE_CORTEX_SERVICE_SQL)
        print("Cortex Search Service created successfully.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    create_cortex_service()
