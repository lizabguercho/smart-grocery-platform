STORES_NOT_IMPLEMENTED_MESSAGE = "Stores extraction is not implemented yet."

DEFAULT_MAX_FILES = 3
DEFAULT_MAX_PAGES = 2

EXTRACT_STEP_MESSAGE = "1. Extracting..."
PARSE_STEP_MESSAGE = "2. Parsing..."
LOAD_STEP_MESSAGE = "3. Loading..."

EXTRACTED_FILES_MESSAGE = "Extracted {count} file(s)."
PARSED_RECORDS_MESSAGE = "Parsed {count} record(s)."
USING_FILES_MESSAGE = "Using {count} files."
FOUND_LINKS_MESSAGE = "Found {count} links."
FOUND_LOCAL_FILES_MESSAGE = "Found {count} local files."
SKIPPING_DOWNLOAD_MESSAGE = "Skipping download. Using local files only..."
MISSING_LOCAL_FILES_MESSAGE = (
    "No {file_label} files found in {raw_dir}. "
    "Run with download enabled first, or place files there manually."
)
SNAPSHOT_SELECTION_MESSAGE = (
    "Latest date {latest_date}: selected {count} store snapshot(s)."
)
