from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import os
from .utils import (
    normalize_to_byte_array,
    bytes_to_bitstring,
    chunk_bitstring,
    optimize_dna_sequence,
    validate_dna_sequence,
    optimize_with_ml,
    enforce_hard_constraints,
    tune_ecc_nsym,
    encode_with_rs, write_fasta_and_metadata
)

app = FastAPI()

UPLOAD_DIR = "static/uploads"

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_location = os.path.join(UPLOAD_DIR, file.filename)
        content = await file.read()
        if not content:
            return JSONResponse({"error": "Empty file provided"}, status_code=400)
            
        with open(file_location, "wb") as f:
            f.write(content)

        byte_array = normalize_to_byte_array(content)
        bit_str = bytes_to_bitstring(byte_array)
        chunks = chunk_bitstring(bit_str, chunk_size=2)
        if not chunks:
            return JSONResponse({"error": "No data to encode"}, status_code=400)
            
        dna_sequence = optimize_dna_sequence(chunks, max_homopolymer=3)
        dna_sequence = optimize_with_ml(
            dna_sequence,
            segment_size=100,
            beam_width=5,
            iterations=10
        )
        dna_sequence = enforce_hard_constraints(dna_sequence, max_homopolymer=3)
        if len(dna_sequence) <= 1:
            return JSONResponse({"error": "Resulting DNA sequence is too short"}, status_code=400)
            
        nsym = tune_ecc_nsym(len(dna_sequence), target_error_rate=0.01)
        dna_sequence_ecc = encode_with_rs(dna_sequence, nsym=nsym)
        validation = validate_dna_sequence(dna_sequence_ecc)

        ml_params = {
        "beam_width": 5,
        "iterations": 10
        }
        storage = write_fasta_and_metadata(
            dna_sequence=dna_sequence_ecc,
            ecc_symbols=nsym,
            ml_params=ml_params,
            segment_size=100,
            output_dir=os.path.join(UPLOAD_DIR, "storage", file.filename),
            base_filename=os.path.splitext(file.filename)[0]
        )

        return JSONResponse({
            "filename": file.filename,
            "dna_sequence": dna_sequence,
            "dna_sequence_ecc": dna_sequence_ecc,
            "length_bases": len(dna_sequence),
            "ecc_symbols": nsym,
            "validation": validation,
            "fasta_file": storage["fasta_path"],
            "metadata_file": storage["metadata_path"],
            "metadata": storage["metadata"]
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)