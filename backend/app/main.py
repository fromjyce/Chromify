from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import os
from .utils import (
    normalize_to_byte_array,
    bytes_to_bitstring,
    chunk_bitstring,
    optimize_dna_sequence,
    validate_dna_sequence,
)

app = FastAPI()

UPLOAD_DIR = "static/uploads"

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    file_location = os.path.join(UPLOAD_DIR, file.filename)
    content = await file.read()
    with open(file_location, "wb") as f:
        f.write(content)

    byte_array = normalize_to_byte_array(content)
    bit_str = bytes_to_bitstring(byte_array)
    chunks = chunk_bitstring(bit_str, chunk_size=2)
    dna_sequence = optimize_dna_sequence(chunks, max_homopolymer=3)
    validation = validate_dna_sequence(dna_sequence)

    return JSONResponse(
        content={
            "filename": file.filename,
            "dna_sequence": dna_sequence,
            "length_bases": len(dna_sequence),
            "validation": validation
        },
        status_code=200,
    )
