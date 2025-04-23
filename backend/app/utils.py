from typing import List

def normalize_to_byte_array(content: bytes) -> bytearray:
    return bytearray(content)

BIT_TO_BASE = {
    "00": "A",
    "01": "C",
    "10": "G",
    "11": "T",
}

def bytes_to_bitstring(data: bytearray) -> str:
    return "".join(f"{byte:08b}" for byte in data)

def chunk_bitstring(bitstr: str, chunk_size: int = 2) -> List[str]:
    pad_len = (-len(bitstr)) % chunk_size
    bitstr_padded = bitstr + ("0" * pad_len)
    return [bitstr_padded[i : i + chunk_size] for i in range(0, len(bitstr_padded), chunk_size)]

def bit_chunks_to_dna(chunks: List[str]) -> str:
    return "".join(BIT_TO_BASE[chunk] for chunk in chunks)