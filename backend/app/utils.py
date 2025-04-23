from typing import List

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