import pdfplumber
import io
import os

def convert_pdf_to_text(pdf_content: bytes) -> str:
    """
    Converts PDF content to plain text.

    Args:
        pdf_content (bytes): The content of the PDF file as bytes.
    
    Returns:
        str: The extracted text from the PDF.
    """

    if not isinstance(pdf_content, bytes):
        raise ValueError("PDF content must be in bytes format")
        return ""
    
    extracted_text = ""
    try:
        with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    extracted_text += page_text + "\n"
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""
    return extracted_text.strip()

if __name__ == "__main__":
    # Ensure pdfplumber is installed
    # pip install pdfplumber

    # --- Option 1: Using an existing PDF file on your system ---
    # REPLACE 'path/to/your/actual_resume.pdf' with the actual path to your PDF file
    your_pdf_file_path = "/Users/raghavraghunath/Resume/Raghav_Resume (5).pdf"

    if os.path.exists(your_pdf_file_path):
        print(f"\n--- Testing with your PDF file: {your_pdf_file_path} ---")
        try:
            with open(your_pdf_file_path, "rb") as f:
                your_pdf_bytes = f.read()
            
            extracted_text_from_file = convert_pdf_to_text(your_pdf_bytes)

            if extracted_text_from_file:
                print("\n--- Extracted Text from Your PDF File ---")
                print(extracted_text_from_file)
                print("\n--- End of Extracted Text ---")
            else:
                print("\nFailed to extract text from your PDF file.")
        except Exception as e:
            print(f"Error reading your PDF file: {e}")
    else:
        print(f"\nWarning: Your specified PDF file '{your_pdf_file_path}' does not exist.")
        print("Please update 'your_pdf_file_path' to a valid path on your system to test this option.")