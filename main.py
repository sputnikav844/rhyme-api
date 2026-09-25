from fastapi import FastAPI
from pydantic import BaseModel
from phonetic_rhyme import do_rhyme, rhyme_key

app = FastAPI(title="Russian Rhyme API")


class RhymeRequest(BaseModel):
    word1: str
    word2: str
    stress1: int | None = None
    stress2: int | None = None


@app.get("/")
def home():
    return {"status": "ok", "service": "Russian Rhyme API"}


@app.post("/rhyme")
def check_rhyme(data: RhymeRequest):
    key1 = rhyme_key(data.word1, stress=data.stress1)
    key2 = rhyme_key(data.word2, stress=data.stress2)

    result = do_rhyme(
        data.word1,
        data.word2,
        data.stress1,
        data.stress2,
    )

    return {
        "word1": data.word1,
        "word2": data.word2,
        "key1": key1,
        "key2": key2,
        "rhymes": result,
    }
