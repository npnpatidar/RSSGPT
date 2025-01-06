import streamlit as st
import google.generativeai as genai
import os
from tqdm import tqdm
from pdf2image import convert_from_path
from PIL import Image
import time
import base64
import logging

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

def ocr_image_batch(image_paths, api_key="your_api_key_here", model_name="gemini-2.0-flash-exp", prompt="Extract the text from these images."):
    """Performs OCR on a batch of images using Gemini API."""
    try:
        genai.configure(api_key=api_key)  # Use your API key here
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

def display_pdf(pdf_path, height=600):
    """Displays a PDF in an iframe with a fixed height and scrollable container."""
    try:
        with open(pdf_path, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
        pdf_display = f"""
            <div style="height: {height}px; overflow-y: auto; width: 100%;">
                <iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="{height}" type="application/pdf"></iframe>
            </div>
        """
        st.markdown(pdf_display, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error displaying PDF: {e}")

def main():
    st.set_page_config(layout="wide")  # Set layout to wide
    st.title("PDF OCR with Gemini API")

    # Sidebar Inputs
    with st.sidebar:
        api_key = st.text_input("Gemini API Key", type="password")
        model_name = st.selectbox("Gemini Model", ["gemini-2.0-flash-exp", "gemini-1.5-pro"])
        batch_size = st.number_input("Batch Size", min_value=1, value=10, step=1)
        uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])
        process_button = st.button("Process PDF")

    # Main Area
    col1, col2 = st.columns([.5, .5])  # Create two columns with equal width

    if uploaded_file and process_button:
        with col1:
            st.subheader("Uploaded PDF")
            temp_pdf_path = "temp_uploaded.pdf"
            with open(temp_pdf_path, "wb") as f:
                f.write(uploaded_file.read())
            display_pdf(temp_pdf_path)

        with col2:
            st.subheader("OCR Output")
            output_file_path = "output.md"
            image_paths = pdf_to_images(temp_pdf_path)
            if not image_paths:
                st.error("PDF to image conversion failed.")
            else:
                markdown_output = ""
                for i in tqdm(range(0, len(image_paths), batch_size), desc="Processing Image Batches", disable=True):
                    batch = image_paths[i:i + batch_size]
                    ocr_text = ocr_image_batch(batch, api_key, model_name)
                    if ocr_text:
                        markdown_output += ocr_text
                    time.sleep(6)
                st.text(markdown_output)
                cleanup_temp_files(image_paths)
                os.remove(temp_pdf_path)

if __name__ == "__main__":
    main()