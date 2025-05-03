import time
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import json
from .utils import (
    normalize_to_byte_array,
    bytes_to_bitstring,
    chunk_bitstring,
    optimize_dna_sequence,
    validate_dna_sequence,
    optimize_with_ml,
    enforce_hard_constraints,
    tune_ecc_nsym,
    encode_with_rs, write_fasta_and_metadata,
    simulate_synthesis_errors,
    simulate_strand_loss,
    cluster_reads_by_segment,dna_to_bytes,decode_with_rs,build_consensus_sequence
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "static/uploads"

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

@app.post("/upload")
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
        
        upload_id = os.path.splitext(file.filename)[0] + "_" + str(int(time.time()))
        output_dir = os.path.join(UPLOAD_DIR, "storage", upload_id)
        
        storage = write_fasta_and_metadata(
            dna_sequence=dna_sequence_ecc,
            ecc_symbols=nsym,
            ml_params=ml_params,
            segment_size=100,
            output_dir=output_dir,
            base_filename="encoded"
        )

        errored_sequence = simulate_synthesis_errors(
            dna_sequence_ecc,
            sub_rate=0.005,
            ins_rate=0.002,
            del_rate=0.002
        )

        degraded_sequence = simulate_strand_loss(
            errored_sequence,
            segment_size=100,
            loss_rate=0.1
        )
        
        degraded_validation = validate_dna_sequence(degraded_sequence)
        # degraded_fasta_path = os.path.join(output_dir, "degraded.fasta")
        # degraded_record = SeqRecord(Seq(degraded_sequence), id="degraded", description="Simulated degraded sequence")
        # SeqIO.write([degraded_record], degraded_fasta_path, "fasta")

        return JSONResponse({
            "filename": file.filename,
            "upload_id": upload_id,
            "dna_sequence": dna_sequence,
            "dna_sequence_ecc": dna_sequence_ecc,
            "length_bases": len(dna_sequence),
            "ecc_symbols": nsym,
            "validation": validation,
            "storage": {
                "fasta_file": storage["fasta_path"],
                "metadata_file": storage["metadata_path"],
                # "degraded_fasta": degraded_fasta_path,
                "directory": output_dir
            },
            "degraded_sequence": degraded_sequence,
            "degraded_validation": degraded_validation,
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    
@app.post("/decode/")
async def decode_file(file: UploadFile = File(...), metadata: UploadFile = File(...)):
    try:
        fasta_path = os.path.join(UPLOAD_DIR, file.filename)
        meta_path = os.path.join(UPLOAD_DIR, metadata.filename)
        
        with open(fasta_path, "wb") as f:
            f.write(await file.read())
        
        with open(meta_path, "wb") as f:
            f.write(await metadata.read())
        
        with open(meta_path) as f:
            meta = json.load(f)
        
        clusters = cluster_reads_by_segment(fasta_path)
        
        decoded_segments = []
        ecc_symbols = meta.get("ecc_symbols", 10)

        for seg_id, reads in clusters.items():
            consensus = build_consensus_sequence(reads)
            
            if not consensus:
                continue

            corrected = decode_with_rs(consensus, ecc_symbols)
            decoded_segments.append((seg_id, corrected))

        seg_order = {seg["id"]: seg["start"] for seg in meta["segments"]}
        decoded_segments.sort(key=lambda x: seg_order.get(x[0], 0))
        full_dna = "".join(seg[1] for seg in decoded_segments)
        
        byte_data = dna_to_bytes(full_dna)

        output_path = os.path.join(UPLOAD_DIR, f"decoded_{file.filename}")
        with open(output_path, "wb") as f:
            f.write(byte_data)
        
        return JSONResponse({
            "status": "success",
            "decoded_file": output_path,
            "segments_recovered": len(decoded_segments),
            "total_segments": len(meta["segments"]),
            "recovery_rate": f"{len(decoded_segments)/len(meta['segments'])*100:.1f}%"
        })
        
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)