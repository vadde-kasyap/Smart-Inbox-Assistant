import pdfplumber
from typing import List
from app.schemas.canonical import TableData

def extract_tables_from_pdf(file_path: str) -> List[TableData]:
    """
    Extracts structured tables from PDF using pdfplumber.
    Preserves column headers, rows, and page numbers.
    """
    tables: List[TableData] = []
    try:
        with pdfplumber.open(file_path) as pdf:
            for page_index, page in enumerate(pdf.pages):
                page_num = page_index + 1
                extracted = page.extract_tables()
                for tbl in extracted:
                    if not tbl or len(tbl) < 2:
                        continue
                    
                    # Clean table data
                    raw_header = tbl[0]
                    headers = [str(col).strip() if col is not None else "" for col in raw_header]
                    
                    rows = []
                    for row in tbl[1:]:
                        clean_row = [str(cell).strip() if cell is not None else "" for cell in row]
                        # only include if not completely empty
                        if any(clean_row):
                            rows.append(clean_row)
                            
                    if rows:
                        tables.append(TableData(
                            columns=headers,
                            rows=rows,
                            page_number=page_num
                        ))
    except Exception:
        # Fallback if pdfplumber encounters non-standard font or corrupted xref
        pass

    return tables
