from typing import List, Dict
import re
import random
import math
from reedsolo import RSCodec

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
