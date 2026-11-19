# ABC Online Shop – FastAPI skeleton

Kiến trúc 4 tầng: Presentation -> Business -> Persistence -> Domain

    pip install -r requirements.txt
    uvicorn app.main:app --reload      # Swagger: http://127.0.0.1:8000/docs

Mọi method chưa có logic đều `raise NotImplementedError` (TODO).
