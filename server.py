import os
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agent import tatai_agent

load_dotenv()

app = FastAPI(title="TATAI API")

# Allow the HTML UI to call this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the UI at /
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_ui():
    return FileResponse("static/index.html")

# --- ADK setup ---
session_service = InMemorySessionService()
APP_NAME = "tatai_app"

runners: dict[str, Runner] = {}  # one Runner per session

def get_runner(session_id: str) -> Runner:
    if session_id not in runners:
        runners[session_id] = Runner(
            agent=tatai_agent,
            app_name=APP_NAME,
            session_service=session_service,
        )
    return runners[session_id]

# --- Request/Response models ---
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    lang: Optional[str] = "en"

class ChatResponse(BaseModel):
    reply: str
    session_id: str

# --- Chat endpoint ---
@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        try:
            existing = await session_service.get_session(
                app_name=APP_NAME,
                user_id=req.session_id,
                session_id=req.session_id,
            )
        except Exception:
            existing = None

        if existing is None:
            await session_service.create_session(
                app_name=APP_NAME,
                user_id=req.session_id,
                session_id=req.session_id,
            )

        runner = get_runner(req.session_id)

        lang_hint = "(Reply in Thai, use lang='th' in all tool calls)" if req.lang == "th" \
               else "(Reply in English, use lang='en' in all tool calls)"

        message = types.Content(
            role="user",
            parts=[types.Part(text=f"{lang_hint}\n\n{req.message}")]
        )

        reply_text = ""
        async for event in runner.run_async(
            user_id=req.session_id,
            session_id=req.session_id,
            new_message=message,
        ):
            # Log every event so we can see what the agent is doing
            print(f"[EVENT] author={event.author} | final={event.is_final_response()}")
            if hasattr(event, 'content') and event.content:
                for part in event.content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        print(f"[TOOL CALL] {part.function_call.name}({part.function_call.args})")
                    if hasattr(part, 'text') and part.text:
                        print(f"[TEXT] {part.text[:100]}")

            if event.is_final_response():
                reply_text = event.content.parts[0].text
                break

        if not reply_text:
            reply_text = "ขออภัยครับ ไม่สามารถตอบได้ในขณะนี้" if req.lang == "th" \
                    else "Sorry, I couldn't get a response right now."

        return ChatResponse(reply=reply_text, session_id=req.session_id)

    except Exception as e:
        print(f"[ERROR] {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Debug endpoint: test TAT API directly ---
@app.get("/debug/places")
async def debug_places(keyword: str = "beach", province_id: int = 350, lang: str = "en"):
    import requests as req
    url = "https://tatdataapi.io/api/v2/places"
    headers = {
        "x-api-key": os.getenv("TAT_API_KEY"),
        "Accept-Language": lang,
    }
    params = {"keyword": keyword, "province_id": province_id, "limit": 5}
    r = req.get(url, headers=headers, params=params, timeout=10)
    return {"status": r.status_code, "body": r.json()}

# --- Health check ---
@app.get("/health")
async def health():
    return {"status": "ok", "agent": "TATAI"}
