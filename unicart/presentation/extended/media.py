"""Recognise uploaded images/audio by their magic bytes (never trust the client's Content-Type) and cap their size."""
from fastapi import Request

from ...business.exceptions import BusinessError


class PayloadTooLarge(BusinessError):
    http_status, code = 413, "PAYLOAD_TOO_LARGE"


class UnsupportedMedia(BusinessError):
    http_status, code = 415, "UNSUPPORTED_MEDIA"


async def read_limited(request: Request, limit: int) -> bytes:
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > limit:
        raise PayloadTooLarge(f"Tệp quá lớn (tối đa {limit // 1024 // 1024} MB)")
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            raise PayloadTooLarge(f"Tệp quá lớn (tối đa {limit // 1024 // 1024} MB)")
        chunks.append(chunk)
    data = b"".join(chunks)
    if not data:
        raise BusinessError("Không nhận được dữ liệu")
    return data


def sniff_image(b: bytes) -> str:
    if b[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if b[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if b[:4] == b"RIFF" and b[8:12] == b"WEBP":
        return "image/webp"
    raise UnsupportedMedia("Chỉ hỗ trợ ảnh JPEG, PNG hoặc WebP")


def sniff_audio(b: bytes) -> str:
    if b[:4] == b"RIFF" and b[8:12] == b"WAVE":
        return "audio/wav"
    if b[:3] == b"ID3" or (len(b) > 1 and b[0] == 0xFF and b[1] & 0xE0 == 0xE0):
        return "audio/mp3"
    if b[:4] == b"OggS":
        return "audio/ogg"
    if b[:4] == b"fLaC":
        return "audio/flac"
    if b[:4] == b"FORM" and b[8:12] in (b"AIFF", b"AIFC"):
        return "audio/aiff"
    raise UnsupportedMedia("Định dạng âm thanh chưa được hỗ trợ (dùng WAV, MP3, OGG, FLAC hoặc AIFF)")
