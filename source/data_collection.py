import requests
import time
import concurrent.futures
from typing import Any, Dict

from pdf_converter import write_to_pdf


class DataCollection:
    def __init__(self):
        self.output = ""

    def drug_download(self, drug_id: int) -> Dict[str, Any]:
        """Fetch drug information from the PubChem API."""
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{drug_id}/JSON/"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching drug data for ID {drug_id}: {e}")
            return {}
        except ValueError:
            print(f"Invalid JSON response for drug ID {drug_id}")
            return {}

    def data_preprocessing(self, data: Dict[str, Any]) -> None:
        toc_heading = ["Names and Identifiers", "Drug and Medication Information"]
        if 'Record' not in data:
            return

        record = data['Record']
        record_title = record.get('RecordTitle', "Unknown Title")

        if record_title == "Unknown Title":
            return
        
        sections = record.get('Section', [])
        drug_details = {"RecordTitle": record_title, "Details": {}}

        for section in sections:
            heading = section.get("TOCHeading")
            if heading in toc_heading:
                extracted_info = self._extract_information(section)
                if extracted_info:
                    drug_details["Details"][heading] = extracted_info
        
        if "Drug and Medication Information" in drug_details["Details"]:
            write_to_pdf(drug_details, record_title)

    def _extract_information(self, section: Dict[str, Any]) -> str:
        details_list = []
        for sub_section in section.get('Section', []):
            for info in sub_section.get('Information', []):
                if "Value" in info and "StringWithMarkup" in info["Value"]:
                    for detail in info["Value"]["StringWithMarkup"]:
                        details_list.append(detail.get('String', ''))
        return " ".join(details_list)

    def start_process(self, drug_id_start, drug_id_limit) -> None:
        start_time = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            drug_ids = range(drug_id_start, drug_id_limit + 1)
            # Use map to download and process data in parallel
            results = executor.map(self.drug_download, drug_ids)

            count = drug_id_start
            for drug_data in results:
                if drug_data:
                    count += 1
                    self.data_preprocessing(drug_data)
                    print(f"Processed drug ID count: {count}")

        end_time = time.perf_counter()
        print("Total time: ", end_time - start_time)


if __name__ == "__main__":
    obj = DataCollection()
    obj.start_process(drug_id_start=201, drug_id_limit=500)
