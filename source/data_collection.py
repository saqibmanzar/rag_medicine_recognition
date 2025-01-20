import time
import requests
import os
import pdb
import concurrent.futures
from typing import Any, Dict, List, Optional
from datetime import datetime

from drug_classifier import connect_to_snowflake, classify_medicine

from transformers import GPT2TokenizerFast

from dataclasses import dataclass
from dotenv import load_dotenv
from snowflake.connector import connect
from snowflake.connector.errors import ProgrammingError
from langchain.text_splitter import RecursiveCharacterTextSplitter


load_dotenv()

@dataclass
class DrugDetails:
    record_title: str
    details: Dict[str, str]

class DataCollection:
    def __init__(self):
        self.connection = self.connect_to_snowflake()
        self.session = requests.Session()  # Reuse HTTP connection
        self.toc_heading = ["Names and Identifiers", "Drug and Medication Information"]
        self.create_table()
        self.tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")


    def token_length(self, text):
        return len(self.tokenizer.encode(text))

    def connect_to_snowflake(self):
        """Establish a connection to Snowflake with retry logic."""
        max_retries = 3
        retry_delay = 5  

        for attempt in range(max_retries):
            try:
                conn = connect(
                    user=os.getenv('SNOWFLAKE_USER'),
                    password=os.getenv('SNOWFLAKE_PASSWORD'),
                    account=os.getenv('SNOWFLAKE_ACCOUNT'),
                    warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
                    database=os.getenv('SNOWFLAKE_DATABASE'),
                    schema=os.getenv('SNOWFLAKE_SCHEMA')
                )
                print("Connected to Snowflake successfully.")
                return conn
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"Connection attempt {attempt + 1} failed: {e}. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    raise Exception(f"Failed to connect to Snowflake after {max_retries} attempts: {e}")

    def create_table(self):
        """Create the drug_data table if it doesn't exist."""
        cursor = self.connection.cursor()
        try:
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS drug_data (
                id NUMBER AUTOINCREMENT,
                record_title VARCHAR(500),
                heading VARCHAR(100),
                chunk VARCHAR(16777216),
                category VARCHAR(100),
                created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
                PRIMARY KEY (id)
            )
            """
            cursor.execute(create_table_sql)
            print("Table creation verified.")
        except ProgrammingError as e:
            print(f"Error creating table: {e}")
            raise
        finally:
            cursor.close()

    def bulk_insert_into_snowflake(self, chunked_details: List[Dict[str, Any]]) -> None:
        print(f"chunked_details: {chunked_details}")

        """Bulk insert chunked details into Snowflake."""
        if not self.connection:
            raise ConnectionError("Snowflake connection not established.")

        cursor = self.connection.cursor()
        try:
            values = []
            for detail in chunked_details:
                for mapp in detail:
                    if isinstance(mapp, dict):
                        record_title = mapp.get('title')  # Use actual record title if available
                        heading = mapp.get('heading')
                        chunk = mapp.get('chunk')
                        category = mapp.get('category')

                        if heading and chunk and record_title and category:
                            values.append((record_title, heading, chunk, category))

            # Insert the data into Snowflake
            sql = """
            INSERT INTO drug_data (record_title, heading, chunk, category)
            VALUES (%s, %s, %s, %s)
            """
            cursor.executemany(sql, values)
            self.connection.commit()
            print(f"Bulk inserted {len(values)} records into Snowflake.")
        except Exception as e:
            print(f"Failed to insert data into Snowflake: {e}")
            self.connection.rollback()
        finally:
            cursor.close()


    def drug_download(self, drug_id: int) -> Optional[Dict[str, Any]]:
        """Fetch drug information from the PubChem API with retry logic."""
        max_retries = 3
        base_delay = 2  # seconds

        for attempt in range(max_retries):
            try:
                url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{drug_id}/JSON/"
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                delay = base_delay * (attempt + 1)
                if attempt < max_retries - 1:
                    print(f"Attempt {attempt + 1} failed for drug ID {drug_id}: {e}. Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    print(f"Failed to fetch drug ID {drug_id} after {max_retries} attempts: {e}")
                    return None
            except ValueError as e:
                print(f"Invalid JSON response for drug ID {drug_id}: {e}")
                return None

    def data_preprocessing(self, data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Process raw API data into structured format and apply chunking."""
        if 'Record' not in data:
            return None

        record = data['Record']
        record_title = record.get('RecordTitle', "Unknown Title")

        if record_title == "Unknown Title":
            return None
        
        sections = record.get('Section', [])
        details = {}

        for section in sections:
            heading = section.get("TOCHeading")
            if heading in self.toc_heading:
                extracted_info = self._extract_information(section)
                if extracted_info:
                    details[heading] = [record_title, extracted_info]
        
        if "Drug and Medication Information" in details:
            # Apply chunking to the details text here
            #pdb.set_trace()
            chunked_details = self.apply_chunking(details)
            return chunked_details
        return None
    
    def apply_chunking(self, details: Dict[str, str]) -> List[Dict[str, Any]]:
        """Apply chunking to the extracted details."""
        chunked_data = []
        session = connect_to_snowflake()
        for heading, text in details.items():
            # Apply the text_chunker (chunking function)
            chunks = self.split_text(text[1])  

            category = classify_medicine(session, text[0])
            if category == 'None' or category == 'N/A':
                continue
            else:
                for chunk in chunks:
                    chunked_data.append({
                        "title": text[0],
                        "heading": heading,
                        "chunk": chunk,
                        "category": category
                    })

        session.close()
        return chunked_data
    
    def split_text(self, text: str) -> List[str]:
        """Split text using the Langchain chunking logic."""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500, 
            chunk_overlap=50,
            length_function=self.token_length,
            is_separator_regex=False
        )
        chunks = text_splitter.split_text(text)
        return chunks

    def _extract_information(self, section: Dict[str, Any]) -> str:
        """Extract and clean information from section."""
        details_list = []
        for sub_section in section.get('Section', []):
            for info in sub_section.get('Information', []):
                if "Value" in info and "StringWithMarkup" in info["Value"]:
                    for detail in info["Value"]["StringWithMarkup"]:
                        text = detail.get('String', '').strip()
                        if text:
                            details_list.append(text)
        return " ".join(details_list)

    def start_process(self, drug_id_start: int, drug_id_limit: int) -> None:
        """Process drug IDs in batches with progress tracking."""
        start_time = time.perf_counter()
        drug_ids = range(drug_id_start, drug_id_limit + 1)
        
        batch_size = 100
        batches = [drug_ids[i:i + batch_size] for i in range(0, len(drug_ids), batch_size)]
        total_batches = len(batches)

        try:
            for batch_num, batch in enumerate(batches, start=1):
                print(f"\nProcessing batch {batch_num}/{total_batches}...")
                processed_drugs = []

                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                    future_to_id = {executor.submit(self.drug_download, drug_id): drug_id for drug_id in batch}
                    
                    for future in concurrent.futures.as_completed(future_to_id):
                        drug_id = future_to_id[future]
                        try:
                            drug_data = future.result()
                            if drug_data:
                                drug_details = self.data_preprocessing(drug_data)
                                if drug_details:
                                    processed_drugs.append(drug_details)
                        except Exception as e:
                            print(f"Error processing drug ID {drug_id}: {e}")

                if processed_drugs:
                    self.bulk_insert_into_snowflake(processed_drugs)

                if batch_num < total_batches:
                    print(f"Batch {batch_num} completed. Pausing for 5 sec...")
                    time.sleep(5)

        except KeyboardInterrupt:
            print("\nProcess interrupted by user. Cleaning up...")
        finally:
            self.connection.close()
            self.session.close()
            end_time = time.perf_counter()
            print(f"\nTotal execution time: {end_time - start_time:.2f} seconds")


if __name__ == "__main__":
    obj = DataCollection()
    obj.start_process(drug_id_start=501, drug_id_limit=10000)