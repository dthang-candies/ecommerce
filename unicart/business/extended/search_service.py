"""AI search (Chapter 3.2, FR-20/21/22/23): hybrid semantic + keyword ranking, query understanding, image and voice.

Pipeline for every modality: text -> parse (price / brand / colour / size) -> embed -> cosine ranking blended with a
lexical score -> hard price & category filters -> sort -> page. If the AI cannot answer within the time limit the same
request is served by plain keyword search and flagged degraded (NFR-12)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .ai.gemini import AiBadInput, AiUnavailable, ImageUnderstanding, Transcript
from .ai.query_parser import COLOR_ALIASES, ParsedQuery, fold_chars, parse_query
from .ai.runtime import AiRuntime, dot
from ...domain.models import Product
from ...persistence.repositories import ProductRepository
from ..exceptions import BusinessError, ServiceUnavailable
from ..product_service import ProductService

# Tuned on the demo catalogue with gemini-embedding-001 @ 768 dims (see docs/AI_SEARCH.md).
BEST_MIN = 0.655      # if even the best product is below this, nothing is relevant (gibberish scores 0.60)
KEEP_MIN = 0.64       # cosine below this is noise (unrelated products cluster around 0.60-0.64)
WINDOW = 0.07         # keep results within this distance of the best match
SEM_LO, SEM_HI = 0.62, 0.78    # cosine range mapped to a 0..1 semantic score
W_SEM, W_LEX = 0.80, 0.20
BOOST_BRAND, BOOST_COLOR, BOOST_SIZE = 0.20, 0.10, 0.08
SOLD_OUT_FACTOR = 0.85


# Very common Vietnamese words (folded) that say nothing about which product is wanted.
STOP = {"may", "do", "cho", "va", "cua", "de", "la", "co", "khong", "nhung", "cai", "con", "chiec", "mot", "nhu",
        "gia", "re", "tot", "dep", "moi", "can", "tim", "mua", "toi", "muon"}


@dataclass
class SearchOutcome:
    items: list[Product]
    total: int
    parsed: ParsedQuery
    mode: str                                   # ai | filters | keyword
    degraded: bool = False                      # AI was wanted but unavailable -> keyword fallback
    scores: dict[int, float] = field(default_factory=dict)
    suggestion: str | None = None
    corrected: str | None = None                # the spelling actually searched when the query was auto-corrected
    recognized: ImageUnderstanding | None = None


class SearchService:
    def __init__(self, session, products: ProductRepository, product_service: ProductService, ai: AiRuntime | None):
        self.session, self.products, self.product_service, self.ai = session, products, product_service, ai

    # ------------------------------------------------------------------ public API
    def search(self, q: str | None, category_id: int | None = None, min_price=None, max_price=None,
               sort: str = "relevance", page: int = 1, size: int = 12, use_ai: bool = True,
               parsed: ParsedQuery | None = None, autocorrect: bool = True) -> SearchOutcome:
        out = self._search(q, category_id, min_price, max_price, sort, page, size, use_ai, parsed)
        if out.total == 0 and out.parsed.text:
            sug = self._typo_fix(out.parsed.text)
            if sug and autocorrect:
                fixed = ParsedQuery(out.parsed.original, sug, out.parsed.min_price, out.parsed.max_price,
                                    out.parsed.brands, out.parsed.colors, out.parsed.sizes)
                again = self._search(sug, category_id, min_price, max_price, sort, page, size, use_ai, fixed)
                if again.total:
                    again.corrected, again.suggestion = sug, None
                    return again
            out.suggestion = sug
        return out

    def _typo_fix(self, text: str) -> str | None:
        """Closest known product word/name when it differs by more than accents (accent-less typing is not a typo)."""
        sug = self.product_service.suggest(text)
        if not sug or fold_chars(sug) in fold_chars(text) or fold_chars(text) in fold_chars(sug):
            return None
        return sug

    def _search(self, q, category_id, min_price, max_price, sort, page, size, use_ai, parsed) -> SearchOutcome:
        q = " ".join((q or "").split())[:100]
        parsed = parsed or parse_query(q, self.products.brands())
        lo = min_price if min_price is not None else parsed.min_price
        hi = max_price if max_price is not None else parsed.max_price
        page, size = max(page, 1), max(1, min(size, 100))

        if use_ai and self.ai is not None and self.ai.ready:
            if not parsed.text:                                        # only filters, e.g. "dưới 500k"
                items, total = self.products.search(None, category_id, lo, hi, self._db_sort(sort), page, size)
                return SearchOutcome(items, total, parsed, "filters")
            try:
                return self._semantic(parsed, category_id, lo, hi, sort, page, size)
            except AiUnavailable:
                degraded = True
        else:
            degraded = use_ai and self.ai is not None and self.ai.enabled   # key set but index not ready yet
        items, total = self.products.search(parsed.text or None, category_id, lo, hi, self._db_sort(sort), page, size)
        return SearchOutcome(items, total, parsed, "keyword", degraded=degraded)

    def search_image(self, data: bytes, mime: str, page: int = 1, size: int = 12) -> SearchOutcome:
        ai = self._need_ai()
        try:
            seen = ai.gemini.understand_image(data, mime)
        except AiBadInput:
            raise BusinessError("Không đọc được ảnh này, hãy thử ảnh khác (JPEG, PNG hoặc WebP)")
        except AiUnavailable:
            raise ServiceUnavailable("Tìm kiếm bằng hình ảnh tạm thời không khả dụng, vui lòng thử lại sau")
        if not seen.query:
            raise BusinessError("Không nhận diện được sản phẩm trong ảnh, hãy thử ảnh rõ hơn")
        parsed = parse_query(seen.query, self.products.brands())
        for c in parse_query(seen.color).colors:
            if c not in parsed.colors:
                parsed.colors.append(c)
        for b in parse_query(seen.brand, self.products.brands()).brands:
            if b not in parsed.brands:
                parsed.brands.append(b)
        out = self.search(seen.query, None, None, None, "relevance", page, size, parsed=parsed, autocorrect=False)
        if out.total == 0 and seen.category:                     # too specific (a title, a model name): use the type
            generic = parse_query(seen.category, self.products.brands())
            out = self.search(generic.text, None, None, None, "relevance", page, size, parsed=generic, autocorrect=False)
        out.recognized = seen
        return out

    def transcribe(self, data: bytes, mime: str) -> Transcript:
        ai = self._need_ai()
        try:
            result = ai.gemini.transcribe(data, mime)
        except AiBadInput:
            raise BusinessError("Không đọc được đoạn ghi âm, hãy thử lại")
        except AiUnavailable:
            raise ServiceUnavailable("Tìm kiếm bằng giọng nói tạm thời không khả dụng, vui lòng thử lại sau")
        if not result.text:
            raise BusinessError("Không nghe rõ, bạn hãy nói lại gần micro hơn nhé")
        return result

    # ------------------------------------------------------------------ internals
    def _need_ai(self) -> AiRuntime:
        if self.ai is None or not self.ai.enabled:
            raise ServiceUnavailable("Tính năng AI chưa được bật trên máy chủ")
        return self.ai

    @staticmethod
    def _db_sort(sort: str) -> str:
        return sort if sort in ("price_asc", "price_desc", "name", "newest") else "newest"

    @staticmethod
    def _lexical(tokens: list[str], p: Product) -> float:
        if not tokens:
            return 0.0
        tokens = [t for t in tokens if t not in STOP]
        if not tokens:
            return 0.0
        words = set(re.findall(r"[a-z0-9]+", fold_chars(f"{p.name} {p.brand or ''} {p.category.name if p.category else ''} {p.sku}")))
        # whole words only ('an' must not match 'nhan'); longer tokens may be a word prefix ('laptop' ~ 'laptops')
        hit = lambda t: t in words or (len(t) >= 5 and any(w.startswith(t) for w in words))
        return sum(1 for t in tokens if hit(t)) / len(tokens)

    @staticmethod
    def _attr_match(p: Product, keys: tuple[str, ...], wanted: set[str]) -> bool:
        attrs = p.attributes or {}
        return any(str(attrs.get(k, "")).lower() in wanted for k in keys)

    def _semantic(self, parsed: ParsedQuery, category_id, lo, hi, sort, page, size) -> SearchOutcome:
        qvec = self.ai.embed_query(parsed.text)                         # may raise AiUnavailable -> keyword fallback
        vectors = self.ai.vectors()
        tokens = parsed.tokens()
        brands = {fold_chars(b) for b in parsed.brands}
        colors = set().union(*(COLOR_ALIASES.get(c, {c}) for c in parsed.colors)) if parsed.colors else set()
        sizes = {s.lower() for s in parsed.sizes}

        rows: list[tuple[float, float, float, bool, Product]] = []      # score, cosine, lexical, brand hit, product
        best = 0.0                                                      # best cosine over the WHOLE catalogue
        for p in self.products.all_active():
            v = vectors.get(p.id)
            cos = dot(qvec, v) if v is not None else 0.0
            best = max(best, cos)               # thresholds must not drift to noise when the real match is filtered out
            if category_id and p.category_id != category_id:
                continue
            if (lo is not None and p.price < lo) or (hi is not None and p.price > hi):
                continue
            lex = self._lexical(tokens, p)
            brand_hit = bool(brands) and fold_chars(p.brand or "") in brands
            sem = min(max((cos - SEM_LO) / (SEM_HI - SEM_LO), 0.0), 1.0)
            score = W_SEM * sem + W_LEX * lex
            if brand_hit:
                score += BOOST_BRAND
            if colors and self._attr_match(p, ("color", "colour"), colors):
                score += BOOST_COLOR
            if sizes and self._attr_match(p, ("size", "shoesSize"), sizes):
                score += BOOST_SIZE
            if not (p.inventory and p.inventory.quantity > 0):
                score *= SOLD_OUT_FACTOR                                # sold out: still findable, ranked lower
            rows.append((score, cos, lex, brand_hit, p))

        relevant = best >= BEST_MIN
        kept = [r for r in rows if (relevant and r[1] >= KEEP_MIN and r[1] >= best - WINDOW) or r[2] >= 0.5 or r[3]]
        if sort in ("price_asc", "price_desc", "name", "newest"):
            key = {"price_asc": lambda r: r[4].price, "price_desc": lambda r: -r[4].price,
                   "name": lambda r: r[4].name.lower(), "newest": lambda r: -r[4].id}[sort]
            kept.sort(key=key)
        else:
            kept.sort(key=lambda r: -r[0])
        window = kept[(page - 1) * size: page * size]
        return SearchOutcome([r[4] for r in window], len(kept), parsed, "ai",
                             scores={r[4].id: round(r[0], 3) for r in window})
