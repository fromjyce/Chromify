from typing import List, Dict
import re
import random
import math
from collections import defaultdict
from reedsolo import RSCodec, ReedSolomonError
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from Bio import SeqIO
import json
import os

def normalize_to_byte_array(content: bytes) -> bytearray:
    return bytearray(content)

BIT_TO_BASE = {
    "00": "A",
    "01": "C",
    "10": "G",
    "11": "T",
}

ALTERNATE_BASES = {
    "A": ["C", "G", "T"],
    "C": ["A", "G", "T"],
    "G": ["A", "C", "T"],
    "T": ["A", "C", "G"],
}

def bytes_to_bitstring(data: bytearray) -> str:
    return "".join(f"{byte:08b}" for byte in data)

def chunk_bitstring(bitstr: str, chunk_size: int = 2) -> List[str]:
    pad_len = (-len(bitstr)) % chunk_size
    bitstr_padded = bitstr + ("0" * pad_len)
    return [bitstr_padded[i : i + chunk_size] for i in range(0, len(bitstr_padded), chunk_size)]

def bit_chunks_to_dna(chunks: List[str]) -> str:
    return "".join(BIT_TO_BASE[chunk] for chunk in chunks)

def calculate_gc_content(dna_sequence: str) -> float:
    gc_count = dna_sequence.count('G') + dna_sequence.count('C')
    return (gc_count / len(dna_sequence)) * 100 if dna_sequence else 0

def has_homopolymer(dna_sequence: str, max_run_length: int = 3) -> bool:
    current_base = ""
    count = 0
    for base in dna_sequence:
        if base == current_base:
            count += 1
            if count > max_run_length:
                return True
        else:
            current_base = base
            count = 1
    return False

def validate_dna_sequence(dna_sequence: str, gc_min: float = 40.0, gc_max: float = 60.0, max_homopolymer: int = 3) -> dict:
    gc_content = calculate_gc_content(dna_sequence)
    homopolymer_exists = has_homopolymer(dna_sequence, max_homopolymer)
    
    is_valid = (gc_min <= gc_content <= gc_max) and not homopolymer_exists
    return {
        "is_valid": is_valid,
        "gc_content": round(gc_content, 2),
        "homopolymer_violation": homopolymer_exists
    }

def optimize_dna_sequence(
    chunks: List[str],
    max_homopolymer: int = 3
) -> str:
    dna_seq = []
    last_base = None
    run_length = 0

    for bits in chunks:
        base = BIT_TO_BASE[bits]
        if base == last_base and run_length >= max_homopolymer:
            for alt in ALTERNATE_BASES[base]:
                if alt != last_base:
                    base = alt
                    break
        dna_seq.append(base)
        if base == last_base:
            run_length += 1
        else:
            last_base = base
            run_length = 1

    return "".join(dna_seq)

def max_homopolymer_run(dna_seq: str) -> int:
    runs = re.findall(r"(A+|C+|G+|T+)", dna_seq)
    return max((len(run) for run in runs), default=0)

def extract_segment_features(dna_seq: str) -> Dict[str, float]:
    return {
        "gc_content": calculate_gc_content(dna_seq),
        "max_homopolymer": float(max_homopolymer_run(dna_seq)),
        "secondary_structure_score": 0.0,
    }
class SequenceSuccessModel:
    def predict_proba(self, features: Dict[str, float]) -> float:
        gc_score = max(0, 1 - abs(features["gc_content"] - 50) / 50)
        hp_score = max(0, 1 - (features["max_homopolymer"] - 1) / 10)
        return 0.5 * gc_score + 0.5 * hp_score

def optimize_with_ml(
    dna_sequence: str,
    segment_size: int = 100,
    beam_width: int = 3,
    iterations: int = 5
) -> str:
    model = SequenceSuccessModel()
    optimized = list(dna_sequence)

    for seg_start in range(0, len(dna_sequence), segment_size):
        seg_end = min(seg_start + segment_size, len(dna_sequence))
        segment = dna_sequence[seg_start:seg_end]
        beam = [segment]

        for _ in range(iterations):
            candidates = []
            for seq_variant in beam:
                for _ in range(beam_width):
                    pos = random.randrange(len(seq_variant))
                    orig_base = seq_variant[pos]
                    alt_base = random.choice(ALTERNATE_BASES[orig_base])
                    mutated = list(seq_variant)
                    mutated[pos] = alt_base
                    candidates.append("".join(mutated))
            scored = [(model.predict_proba(extract_segment_features(seq)), seq) 
                      for seq in candidates]
            scored.sort(key=lambda x: x[0], reverse=True)
            beam = [seq for _, seq in scored[:beam_width]]
        best_segment = beam[0]
        optimized[seg_start:seg_end] = list(best_segment)

    return "".join(optimized)

def enforce_hard_constraints(
    dna_sequence: str,
    max_homopolymer: int = 3
) -> str:
    seq_list = list(dna_sequence)
    run_base = seq_list[0]
    run_start = 0

    for i in range(1, len(seq_list)+1):
        if i < len(seq_list) and seq_list[i] == run_base:
            continue
        run_length = i - run_start
        if run_length > max_homopolymer:
            break_pos = run_start + run_length // 2
            orig = seq_list[break_pos]
            seq_list[break_pos] = next(b for b in ALTERNATE_BASES[orig] if b != orig)
        if i < len(seq_list):
            run_base = seq_list[i]
            run_start = i

    return "".join(seq_list)

def encode_with_rs(dna_sequence: str, nsym: int = 10) -> str:
    if len(dna_sequence) < 2:
        return dna_sequence
    
    base_map = {"A": 0, "C": 1, "G": 2, "T": 3}
    try:
        data = bytes([base_map[b] for b in dna_sequence])
        max_possible_nsym = len(data) - 1
        nsym = min(nsym, max_possible_nsym) if max_possible_nsym > 0 else 1
        
        rsc = RSCodec(nsym)
        encoded = rsc.encode(data)
        bits = "".join(f"{byte:08b}" for byte in encoded)
        chunks = chunk_bitstring(bits, 2)
        return bit_chunks_to_dna(chunks)
    except Exception:
        return dna_sequence

def tune_ecc_nsym(dna_length: int, target_error_rate: float = 0.01) -> int:
    if dna_length <= 1:
        return 0
    estimated = math.ceil(dna_length * target_error_rate * 2)
    max_possible = dna_length - 1
    return min(estimated, max_possible)

def write_fasta_and_metadata(
    dna_sequence: str,
    ecc_symbols: int,
    ml_params: dict,
    segment_size: int,
    output_dir: str,
    base_filename: str
) -> dict:
    os.makedirs(output_dir, exist_ok=True)
    fasta_path = os.path.join(output_dir, f"{base_filename}.fasta")
    meta_path  = os.path.join(output_dir, f"{base_filename}_metadata.json")
    
    records = []
    metadata = {
        "segments": [],
        "ecc_symbols": ecc_symbols,
        "ml_params": ml_params,
        "segment_size": segment_size
    }

    for idx in range(0, len(dna_sequence), segment_size):
        seg_seq = dna_sequence[idx : idx + segment_size]
        seg_id  = f"{base_filename}_seg{idx//segment_size}"
        records.append(SeqRecord(Seq(seg_seq), id=seg_id, description=""))
        metadata["segments"].append({
            "id": seg_id,
            "start": idx,
            "length": len(seg_seq)
        })

    with open(fasta_path, "w") as fasta_file:
        SeqIO.write(records, fasta_file, "fasta")

    with open(meta_path, "w") as meta_file:
        json.dump(metadata, meta_file, indent=2)

    return {
        "fasta_path": fasta_path,
        "metadata_path": meta_path,
        "metadata": metadata
    }

def simulate_synthesis_errors(
    dna_sequence: str,
    sub_rate: float = 0.005,
    ins_rate: float = 0.002,
    del_rate: float = 0.002
) -> str:
    bases = ["A", "C", "G", "T"]
    corrupted = []
    for base in dna_sequence:
        r = random.random()
        if r < del_rate:
            continue
        r -= del_rate
        if r < ins_rate:
            corrupted.append(random.choice(bases))
        r -= ins_rate
        if r < sub_rate:
            alt = random.choice([b for b in bases if b != base])
            corrupted.append(alt)
        else:
            corrupted.append(base)
    return "".join(corrupted)

def simulate_strand_loss(
    dna_sequence: str,
    segment_size: int,
    loss_rate: float = 0.1
) -> str:
    degraded = []
    for i in range(0, len(dna_sequence), segment_size):
        segment = dna_sequence[i : i + segment_size]
        if random.random() < loss_rate:
            continue
        degraded.append(segment)
    return "".join(degraded)

def cluster_reads_by_segment(fasta_path: str) -> Dict[str, List[str]]:
    clusters = defaultdict(list)
    for record in SeqIO.parse(fasta_path, "fasta"):
        seg_id = record.id.split('_')[0]
        clusters[seg_id].append(str(record.seq))
    return dict(clusters)

class BaseCallerModel:
    def __init__(self):
        self.error_probs = {
            'A': {'A': 0.98, 'C': 0.01, 'G': 0.005, 'T': 0.005},
            'C': {'C': 0.97, 'A': 0.02, 'G': 0.005, 'T': 0.005},
            'G': {'G': 0.96, 'A': 0.02, 'C': 0.01, 'T': 0.01},
            'T': {'T': 0.95, 'A': 0.02, 'C': 0.02, 'G': 0.01},
        }
    
    def predict_probs(self, observed_base: str) -> Dict[str, float]:
        return self.error_probs.get(observed_base, 
                                  {'A': 0.25, 'C': 0.25, 'G': 0.25, 'T': 0.25})

def build_consensus_sequence(
    reads: List[str], 
    min_coverage: int = 3,
    model: BaseCallerModel = None
) -> str:
    if not reads:
        return ""
    
    if model is None:
        model = BaseCallerModel()
    
    seq_length = max(len(read) for read in reads)
    consensus = []
    
    for pos in range(seq_length):
        base_weights = defaultdict(float)
        total_weight = 0
        
        for read in reads:
            if pos >= len(read):
                continue
                
            observed_base = read[pos]
            probs = model.predict_probs(observed_base)
            
            for base, prob in probs.items():
                base_weights[base] += prob
                total_weight += prob
        
        if total_weight == 0 or len(base_weights) == 0:
            continue
            
        if len([w for w in base_weights.values() if w > 0]) < min_coverage:
            continue
        best_base = max(base_weights.items(), key=lambda x: x[1])[0]
        consensus.append(best_base)
    
    return "".join(consensus)

def decode_with_rs(dna_sequence: str, nsym: int) -> str:
    if nsym <= 0 or len(dna_sequence) < 2:
        return dna_sequence
    
    base_map = {"A": 0, "C": 1, "G": 2, "T": 3}
    inv_base_map = {v: k for k, v in base_map.items()}
    
    try:
        data = bytes([base_map[b] for b in dna_sequence])
        rsc = RSCodec(nsym)
        decoded_bytes = rsc.decode(data)[0]
        return "".join(inv_base_map[b] for b in decoded_bytes)
    except ReedSolomonError:
        return dna_sequence
    except Exception:
        return dna_sequence
    
def dna_to_bytes(dna_sequence: str) -> bytearray:
    base_to_bits = {
        "A": "00",
        "C": "01",
        "G": "10",
        "T": "11"
    }
    
    bit_str = "".join(base_to_bits[base] for base in dna_sequence)
    byte_arr = bytearray()
    for i in range(0, len(bit_str), 8):
        byte_bits = bit_str[i:i+8]
        if len(byte_bits) < 8:
            break 
        byte_arr.append(int(byte_bits, 2))
    
    return byte_arr
