from pdf2image import convert_from_path
from PIL import Image
import pytesseract
import os
import sys

# ✅ Paths
pdf_folder = r"C:\Users\User\Downloads\Desktop\HACK\pdf"
output_folder = r"C:\Users\User\Downloads\Desktop\HACK\textedfolder"
poppler_path = r"C:\poppler-25.07.0\Library\bin"
tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ✅ Check folder existence
if not os.path.exists(pdf_folder):
    print(f"Error: PDF folder not found at {pdf_folder}")
    sys.exit(1)

if not os.path.exists(output_folder):
    os.makedirs(output_folder)

if not os.path.exists(poppler_path):
    print(f"Error: Poppler not found at {poppler_path}")
    sys.exit(1)

if not os.path.exists(tesseract_path):
    print(f"Error: Tesseract not found at {tesseract_path}")
    sys.exit(1)

# ✅ Set up Tesseract
pytesseract.pytesseract.tesseract_cmd = tesseract_path

# ✅ Process each PDF in folder
for filename in os.listdir(pdf_folder):
    if filename.lower().endswith(".pdf"):
        pdf_path = os.path.join(pdf_folder, filename)
        txt_filename = os.path.splitext(filename)[0] + ".txt"
        txt_path = os.path.join(output_folder, txt_filename)

        print(f"📄 Processing: {filename} ...")

        try:
            pages = convert_from_path(pdf_path, poppler_path=poppler_path)
        except Exception as e:
            print(f"❌ Error converting {filename}: {e}")
            continue

        text_output = ""

        for page_num, page in enumerate(pages):
            temp_image = f"temp_page_{page_num + 1}.jpg"
            page.save(temp_image, "JPEG")

            text = pytesseract.image_to_string(Image.open(temp_image))
            text_output += f"--- Page {page_num + 1} ---\n{text}\n"

            os.remove(temp_image)

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text_output)

        print(f"✅ Saved: {txt_path}")

print("\n🎉 All PDFs processed successfully! Check your 'textedfolder'.")
