"""Deterministic stand-in for GeminiClient: bag-of-words vectors with a shared offset, so unrelated texts have
cosine ~0.6 and texts sharing words score higher (like the real model). No network, no quota."""
import copy
import hashlib
import math

from unicart.business.extended.ai.gemini import AiBadInput, AiQuotaExceeded, AiUnavailable, ImageUnderstanding, Transcript
from unicart.business.extended.ai.query_parser import fold_chars

DIM, OFFSET = 1024, math.sqrt(1.5)


def vectorize(text: str) -> list[float]:
    bag = [0.0] * DIM
    for tok in "".join(c if c.isalnum() else " " for c in fold_chars(text)).split():
        bag[1 + int(hashlib.md5(tok.encode()).hexdigest(), 16) % (DIM - 1)] += 1.0
    norm = math.sqrt(sum(x * x for x in bag)) or 1.0
    vec = [x / norm for x in bag]
    vec[0] = OFFSET
    n = math.sqrt(sum(x * x for x in vec))
    return [x / n for x in vec]


class FakeGemini:
    embed_model, dim, query_timeout = "fake-embedding", DIM, 2.0

    def __init__(self):
        self.fail = False                       # simulate outage / quota exhausted
        self.embedded: list[str] = []           # every document text sent for embedding
        self.query_calls = 0
        self.image = ImageUnderstanding(query="laptop màu bạc", category="laptop", color="bạc", brand="")
        self.speech = Transcript(text="laptop dưới 30 triệu", language="vi")
        self.reject_media = False
        self.quota_failures = 0                 # next N document-embedding calls answer HTTP 429
        self.chat_script: list[list[dict]] = []  # answers (Gemini `parts`) handed out one per chat_turn call
        self.chat_calls: list[dict] = []        # what the chatbot sent: {"system", "contents"} per call

    def embed(self, texts, task, timeout=None):
        if self.fail:
            raise AiUnavailable("simulated outage")
        if task == "RETRIEVAL_DOCUMENT":
            if self.quota_failures > 0:
                self.quota_failures -= 1
                raise AiQuotaExceeded("quota")
            self.embedded += texts
        else:
            self.query_calls += 1
        return [vectorize(t) for t in texts]

    def understand_image(self, data, mime):
        if self.fail:
            raise AiUnavailable("simulated outage")
        if self.reject_media:
            raise AiBadInput("bad image")
        return self.image

    def transcribe(self, data, mime):
        if self.fail:
            raise AiUnavailable("simulated outage")
        if self.reject_media:
            raise AiBadInput("bad audio")
        return self.speech

    def chat_turn(self, system, contents, tools, timeout=None):
        if self.fail:
            raise AiUnavailable("simulated outage")
        self.chat_calls.append({"system": system, "contents": copy.deepcopy(contents), "tools": [t["name"] for t in tools], "timeout": timeout})
        return self.chat_script.pop(0) if self.chat_script else [{"text": "Xin chào, mình có thể giúp gì cho bạn?"}]
