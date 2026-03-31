from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routers import imports, papers, questions

app = FastAPI(
    title="Guguga Quiz API",
    description="線上測驗平台後端 API（管理與匯入）",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(imports.router, prefix="/api")
app.include_router(papers.router, prefix="/api")
app.include_router(questions.router, prefix="/api")


@app.get("/")
async def root():
    return {"status": "ok", "service": "Guguga Quiz API"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
