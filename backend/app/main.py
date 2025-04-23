from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from io import BytesIO
import os

app = FastAPI()

UPLOAD_DIR = "static/uploads"

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

def normalize_to_byte_array(content: bytes) -> bytearray:
    return bytearray(content)

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    file_location = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_location, "wb") as f:
        content = await file.read()
        f.write(content)
    
    byte_array = normalize_to_byte_array(content)
    print(byte_array)

    return JSONResponse(content={"filename": file.filename, "byte_array": list(byte_array)}, status_code=200)