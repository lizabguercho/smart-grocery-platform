print("Script started", flush=True)
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from data_extraction_config import SHUFERSAL_CATEGORY_URL, ShufersalPriceCategory
from urllib.parse import urljoin
from urllib.parse import urlparse
import gzip
import xml.etree.ElementTree as ET
import utils
from datetime import datetime

chain_name = "shufersal"
# downloads the webpage and returns the HTML as a string.
def get_page(category_id: ShufersalPriceCategory = ShufersalPriceCategory.PRICES_FULL, store_id: int = 0):
    response = requests.get(SHUFERSAL_CATEGORY_URL, params={"catID":category_id.value, "storeId":store_id}, timeout=30)
    response.raise_for_status()
    return response.text

# parses that HTML and extracts the download URLs, which it returns as a list of strings.
def extract_download_prices_full_links(html:str)->list[str]:    
    soup = BeautifulSoup(html, "html.parser")
    return [
        urljoin(SHUFERSAL_CATEGORY_URL, link["href"])
        for link in soup.find_all("a", href=True)
        if "pricefull" in link["href"].lower()
]

# downloads the files from the links and saves them to the current directory.
def download_files(links: list[str]) -> list[Path]:
    output_dir = Path("data/raw/shufersal")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    downloaded_files = []
    
    for link in links:
        filename = Path(urlparse(link).path).name
        
        if not filename:
            raise ValueError(f"Could not extract filename from URL: {link}")
        
        output_path = output_dir / filename
        
        with requests.get(link, timeout=60, stream=True) as response:
            response.raise_for_status()

            with output_path.open("wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
        
        
        downloaded_files.append(output_path)
    
    return downloaded_files

# extracts the date from the filename and returns it as a string.
def extract_date_from_filename(file_path: Path) -> str:
    filename = file_path.stem
    parts = filename.split("-")

    # Expected format:
    # PriceFull7290027600007-001-001-20260722-030000

    if len(parts) < 5:
        raise ValueError(f"Unexpected filename format: {file_path.name}")

    date_text = parts[-2]

    try:
        extraction_date = datetime.strptime(date_text, "%Y%m%d").date()
    except ValueError:
        raise ValueError(f"Invalid date '{date_text}' in filename: {file_path.name}")

    return extraction_date.isoformat()


#  Parses the PriceFull files and returns one dictionary per product.
def parse_price_full_files(downloaded_files: list[Path]) -> list[dict[str, str | None]]:
    products = []
    
    for file_path in downloaded_files:
        with gzip.open(file_path, "rt",encoding="utf-8") as xml_file:
           tree = ET.parse(xml_file)
           root = tree.getroot()
        
        store_id = root.findtext("StoreID")
        chain_id = root.findtext("ChainID")
        subchain_id = root.findtext("SubChainID")
        extraction_date = extract_date_from_filename(file_path)
        
          
        items = root.find("Items")
        
        if items is None:
            continue
        
        for item in items:
            product = {
                child.tag: child.text
                for child in item
            }
            
            product["StoreID"] = store_id
            product["ChainID"] = chain_id
            product["SubChainID"] = subchain_id
            product["SourceFile"] = file_path.name
            product["ExtractionDate"] = extraction_date
            products.append(product)
    
    return products  # returns a list of dictionaries, where each dictionary contains the data for a single product.
 
           
# main function that downloads the files from the links and saves them to the current directory. It calls the other functions in the correct order.
def main() -> list[dict[str, str | None]]:
    print("1. Getting Shufersal webpage...", flush=True)
    html = get_page()
    print("Webpage downloaded.", flush=True)

    print("2. Extracting download links...", flush=True)
    links = extract_download_prices_full_links(html)
    print(f"Found {len(links)} links.", flush=True)

    print("3. Downloading files...", flush=True)
    downloaded_files = download_files(links)
    print(f"Downloaded {len(downloaded_files)} files.", flush=True)

    print("4. Parsing product files...", flush=True)
    products = parse_price_full_files(downloaded_files)
    print(f"Parsed {len(products)} product records.", flush=True)

    print("5. Saving CSV...", flush=True)
    utils.save_to_csv(products, chain_name)
    print("CSV saved successfully.", flush=True)

    return products


if __name__ == "__main__":
    main()

