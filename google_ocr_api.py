from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse
import google.generativeai as genai
import os
import markdown
from tqdm import tqdm
from pdf2image import convert_from_path
from PIL import Image
import time
import base64
from typing import List
import logging

app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def pdf_to_images(pdf_path, output_dir="temp_images"):
    """Converts each page of a PDF to an image."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    try:
        images = convert_from_path(pdf_path)
        image_paths = []
        for i, image in enumerate(images):
            image_path = os.path.join(output_dir, f"page_{i}.png")
            image.save(image_path, "PNG")
            image_paths.append(image_path)
        return image_paths
    except Exception as e:
        logger.error(f"Error converting PDF to images: {e}")
        return []

def ocr_image_batch(image_paths, api_key, model_name, prompt="Extract the text from these images."):
    """Performs OCR on a batch of images using Gemini API."""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name=model_name)
        
        uploaded_files = []
        for image_path in image_paths:
            try:
                f = genai.upload_file(path=image_path)
                uploaded_files.append(f)
            except Exception as e:
                logger.error(f"Error uploading file {image_path}: {e}")
                return ""

        if not uploaded_files:
            logger.error("No files were uploaded successfully.")
            return ""
        
        response = model.generate_content([prompt, *uploaded_files])
        response.resolve()
        logger.debug(f"Gemini API response: {response.text}")
        return response.text
    except Exception as e:
        logger.error(f"Error during OCR: {e}")
        return ""


def append_to_markdown_file(markdown_text, output_file_path):
    """Appends Markdown text to a file."""
    try:
        with open(output_file_path, 'a', encoding='utf-8') as output_file:
            output_file.write(markdown_text)
    except Exception as e:
        logger.error(f"Error appending to file: {e}")

def cleanup_temp_files(temp_files):
    """Deletes temporary files."""
    for temp_file in temp_files:
        try:
            os.remove(temp_file)
        except Exception as e:
            logger.error(f"Error deleting temp file {temp_file}: {e}")

@app.post("/ocr")
async def ocr_pdf(
    pdf_file: UploadFile = File(...),
    api_key: str = Form("AIzaSyA4LXOUF-NjERVSpxbHo7puizn9z4cbDcQ"),
    model_name: str = Form("gemini-2.0-flash-exp"),
    batch_size: int = Form(10)
):
    """Processes a PDF file and returns the OCR output in Markdown format."""
    if not pdf_file:
        raise HTTPException(status_code=400, detail="No PDF file provided.")

    try:
        temp_pdf_path = "temp_uploaded.pdf"
        with open(temp_pdf_path, "wb") as f:
            f.write(await pdf_file.read())

        image_paths = pdf_to_images(temp_pdf_path)
        if not image_paths:
            raise HTTPException(status_code=500, detail="PDF to image conversion failed.")

        markdown_output = ""
        for i in tqdm(range(0, len(image_paths), batch_size), desc="Processing Image Batches", disable=True):
            batch = image_paths[i:i + batch_size]
            ocr_text = ocr_image_batch(batch, api_key, model_name)
            if ocr_text:
                markdown_text = ocr_text
                markdown_output += markdown_text
            time.sleep(6)

        cleanup_temp_files(image_paths)
        os.remove(temp_pdf_path)

        return JSONResponse(content={"markdown_output": markdown_output})

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)