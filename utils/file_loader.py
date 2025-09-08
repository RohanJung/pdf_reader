import io
import fitz  # this is pymupdf

async def extract_text(file):
    contents = await file.read()

    if file.filename.endswith(".pdf"):
        pdf_stream = io.BytesIO(contents)
        doc = fitz.open(stream=pdf_stream, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text

    elif file.filename.endswith(".txt"):
        return contents.decode("utf-8")

    else:
        raise ValueError("Unsupported file type. Use .pdf or .txt")
