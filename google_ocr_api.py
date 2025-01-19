from fastapi import FastAPI, File, UploadFile, HTTPException, Form
import google.generativeai as genai
import os
import asyncio
from pdf2image import convert_from_path
import logging
from uuid import uuid4
import aiofiles

app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Temporary storage for tasks
tasks = {}

# Rate limit configuration
MAX_REQUESTS_PER_MINUTE = 10
REQUEST_DELAY = 60 / MAX_REQUESTS_PER_MINUTE  # 6 seconds
rate_limit_semaphore = asyncio.Semaphore(1)  # Allows 1 request at a time

# Utility function for PDF-to-image conversion
def pdf_to_images_sync(pdf_path, output_dir="temp_images"):
    """Synchronous PDF to image conversion."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    images = convert_from_path(pdf_path)
    image_paths = []
    for i, image in enumerate(images):
        image_path = os.path.join(output_dir, f"page_{i}.png")
        image.save(image_path, "PNG")
        image_paths.append(image_path)
    return image_paths

async def pdf_to_images(pdf_path):
    """Asynchronous wrapper for PDF-to-image conversion."""
    return await asyncio.to_thread(pdf_to_images_sync, pdf_path)

# Utility function for OCR processing with rate limiting
async def ocr_image_batch(image_paths, api_key, model_name, prompt="Extract the text from these images."):
    """Performs OCR on a batch of images with rate limiting."""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name=model_name)

        uploaded_files = []
        for image_path in image_paths:
            # Enforce rate limit for uploads
            async with rate_limit_semaphore:
                try:
                    f = genai.upload_file(path=image_path)
                    uploaded_files.append(f)
                except Exception as e:
                    logger.error(f"Error uploading file {image_path}: {e}")
                await asyncio.sleep(REQUEST_DELAY)  # Delay after each upload

        if not uploaded_files:
            logger.error("No files were uploaded successfully.")
            return ""

        # Enforce rate limit for content generation
        async with rate_limit_semaphore:
            response = model.generate_content([prompt, *uploaded_files])
            response.resolve()
            logger.debug(f"Gemini API response: {response.text}")
            await asyncio.sleep(REQUEST_DELAY)  # Delay after generation
            return response.text
    except Exception as e:
        logger.error(f"Error during OCR: {e}")
        return ""

# Cleanup utility
def cleanup_temp_files(temp_files):
    """Deletes temporary files."""
    for temp_file in temp_files:
        try:
            os.remove(temp_file)
        except Exception as e:
            logger.error(f"Error deleting temp file {temp_file}: {e}")

@app.post("/ocr")
async def start_ocr(
    pdf_file: UploadFile = File(...),
    api_key: str = Form(...),
    model_name: str = Form("gemini-2.0-flash-exp"),
    batch_size: int = Form(10)
):
    """Starts the OCR processing task and returns a task ID immediately."""
    task_id = str(uuid4())
    tasks[task_id] = {"status": "processing", "result": None}  # Initialize the task

    # Read the file content immediately
    file_content = await pdf_file.read()

    async def process_task(content: bytes):
        """Background task to process the OCR."""
        try:
            # Save PDF content to a temporary file
            temp_pdf_path = f"temp_{task_id}.pdf"
            async with aiofiles.open(temp_pdf_path, "wb") as temp_pdf:
                await temp_pdf.write(content)  # Write the file content
                logger.debug(f"Saved PDF to temporary file {temp_pdf_path}")

            # Convert PDF to images
            image_paths = await pdf_to_images(temp_pdf_path)
            if not image_paths:
                tasks[task_id]["status"] = "failed"
                return

            # Process OCR in batches
            markdown_output = ""
            for i in range(0, len(image_paths), batch_size):
                batch = image_paths[i:i + batch_size]
                ocr_text = await ocr_image_batch(batch, api_key, model_name)
                markdown_output += ocr_text or ""

            # Cleanup and save results
            cleanup_temp_files(image_paths)
            os.remove(temp_pdf_path)
            logger.debug(f"Task {task_id} completed successfully.")

            tasks[task_id]["status"] = "completed"
            tasks[task_id]["result"] = markdown_output
        except Exception as e:
            logger.error(f"Error processing task {task_id}: {e}")
            tasks[task_id]["status"] = "failed"

    # Start the background task without awaiting
    asyncio.create_task(process_task(file_content))

    # Return the task ID immediately
    return {"task_id": task_id, "status": "processing"}

# Endpoint to check task status
@app.get("/ocr/status/{task_id}")
async def check_status(task_id: str):
    """Checks the status of an OCR task."""
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    return {"task_id": task_id, "status": task["status"], "result": task["result"]}

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)