from fastapi import (
    Depends,
    FastAPI,
    UploadFile,
    File,
    HTTPException,
)
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backendd.auth_routes import (
    router as auth_router,
    get_current_user,
)
from backendd.schemas.chat import AskRequest
from backendd.schemas.profile import StudentProfile
from services.rag_service import ask_question
from services.scholarship_matcher import (
    find_matching_scholarships,
)
from services.database import (
    init_db,
    save_profile,
    get_profile,
    save_scholarship,
    get_saved_scholarships,
    remove_saved_scholarship,
    update_scholarship_status,
)

import tempfile
import os
from datetime import datetime

# ============================================================
# OPTIONAL TEXT TO SPEECH
# ============================================================

try:
    from gtts import gTTS
except ImportError:
    gTTS = None

# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="Scholarship Assistant API",
    description="Backend API for the Scholarship Assistant",
    version="1.0.0",
)

app.include_router(auth_router)

# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# DATABASE
# ============================================================

init_db()

print(
    "ScholarAI database initialized successfully.",
    flush=True,
)

# ============================================================
# WHISPER - LAZY LOADING
# ============================================================

whisper_model = None


def get_whisper_model():
    """Load Whisper only when transcription is requested."""
    global whisper_model

    if whisper_model is None:
        print(
            "Loading speech recognition model...",
            flush=True,
        )

        try:
            from faster_whisper import WhisperModel

            whisper_model = WhisperModel(
                "base",
                device="cpu",
                compute_type="int8",
            )

            print(
                "Speech recognition model loaded successfully.",
                flush=True,
            )

        except Exception as e:
            print(
                f"Failed to load speech recognition model: {e}",
                flush=True,
            )
            raise

    return whisper_model


# ============================================================
# REQUEST SCHEMAS
# ============================================================

class SaveScholarshipRequest(BaseModel):
    scholarship_id: str
    scholarship_name: str
    deadline: str | None = None


class ScholarshipStatusRequest(BaseModel):
    status: str


# ============================================================
# USER ACCESS VERIFICATION
# ============================================================

def verify_user_access(
    email: str,
    current_user: dict,
):
    """Ensure users can access only their own account data."""

    token_email = (
        current_user["user"]["email"]
        .strip()
        .lower()
    )

    requested_email = (
        email.strip().lower()
    )

    if token_email != requested_email:
        raise HTTPException(
            status_code=403,
            detail=(
                "You are not authorized "
                "to access this account."
            ),
        )


# ============================================================
# HOME
# ============================================================

@app.get("/")
def home():
    return {
        "message": "Scholarship Assistant API is running"
    }


# ============================================================
# ASK - WITH DIAGNOSTIC LOGGING
# ============================================================

@app.post("/ask")
def ask(request: AskRequest):
    print(
        "ASK DEBUG: Request reached /ask",
        flush=True,
    )

    try:
        question = request.question.strip()

        if not question:
            raise HTTPException(
                status_code=400,
                detail="Please enter a question.",
            )

        print(
            "ASK DEBUG: Starting RAG service",
            flush=True,
        )

        result = ask_question(question)

        print(
            "ASK DEBUG: RAG service completed",
            flush=True,
        )

        return {
            "question": question,
            "answer": result["answer"],
            "scholarships": result["scholarships"],
        }

    except HTTPException:
        raise

    except Exception as e:
        print(
            f"ASK DEBUG: Failed with {type(e).__name__}: {e}",
            flush=True,
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to generate an answer. Please try again.",
        )


# ============================================================
# TRANSCRIBE AUDIO
# ============================================================

@app.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
):
    temp_path = None

    try:
        if not file:
            raise HTTPException(
                status_code=400,
                detail="No audio file received.",
            )

        audio_data = await file.read()

        if not audio_data:
            raise HTTPException(
                status_code=400,
                detail="Audio file is empty.",
            )

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".m4a",
        ) as temp_file:
            temp_file.write(audio_data)
            temp_path = temp_file.name

        print("===================================", flush=True)
        print("AUDIO RECEIVED", flush=True)
        print("Filename:", file.filename, flush=True)
        print("Content type:", file.content_type, flush=True)
        print("Size:", len(audio_data), "bytes", flush=True)
        print("Temporary file:", temp_path, flush=True)
        print("===================================", flush=True)

        model = get_whisper_model()

        segments, info = model.transcribe(
            temp_path,
            beam_size=5,
            vad_filter=True,
            condition_on_previous_text=False,
        )

        text = " ".join(
            segment.text.strip()
            for segment in segments
        ).strip()

        print("Detected language:", info.language, flush=True)
        print(
            "Language probability:",
            info.language_probability,
            flush=True,
        )
        print("Transcribed text:", repr(text), flush=True)

        if not text:
            raise HTTPException(
                status_code=400,
                detail="No speech was detected in the audio.",
            )

        return {
            "text": text,
            "language": info.language,
            "language_probability": info.language_probability,
        }

    except HTTPException:
        raise

    except Exception as e:
        print(
            "TRANSCRIPTION ERROR:",
            str(e),
            flush=True,
        )

        raise HTTPException(
            status_code=500,
            detail=f"Speech transcription failed: {str(e)}",
        )

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


# ============================================================
# TEXT TO SPEECH
# ============================================================

@app.post("/speak")
async def speak_text(request: dict):
    text = request.get("text", "").strip()

    if not text:
        raise HTTPException(
            status_code=400,
            detail="No text provided.",
        )

    if gTTS is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Text-to-speech is temporarily "
                "unavailable on the deployed server."
            ),
        )

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".mp3",
        ) as temp_file:
            temp_path = temp_file.name

        tts = gTTS(
            text=text,
            lang="en",
        )

        tts.save(temp_path)

        return FileResponse(
            temp_path,
            media_type="audio/mpeg",
            filename="scholarai_answer.mp3",
        )

    except Exception as e:
        print("TTS error:", str(e), flush=True)

        raise HTTPException(
            status_code=500,
            detail=f"TTS failed: {str(e)}",
        )


# ============================================================
# SAVE PROFILE
# ============================================================

@app.post("/profile")
def save_student_profile(profile: StudentProfile):
    save_profile(profile)

    saved_profile = get_profile(profile.email)

    return {
        "message": "Student profile saved successfully",
        "profile": saved_profile,
    }


# ============================================================
# GET PROFILE
# ============================================================

@app.get("/profile/{email}")
def get_student_profile(
    email: str,
    current_user: dict = Depends(get_current_user),
):
    verify_user_access(email, current_user)

    profile = get_profile(email)

    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Student profile not found",
        )

    return {"profile": profile}


# ============================================================
# GET PERSONALIZED MATCHES
# ============================================================

@app.get("/matches/{email}")
def get_matches(
    email: str,
    current_user: dict = Depends(get_current_user),
):
    verify_user_access(email, current_user)

    profile = get_profile(email)

    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Student profile not found",
        )

    matches = find_matching_scholarships(profile)

    eligible_count = sum(
        1
        for scholarship in matches
        if scholarship.get("status") == "matched"
    )

    verification_count = sum(
        1
        for scholarship in matches
        if scholarship.get("status") == "needs_verification"
    )

    formatted_matches = []

    for scholarship in matches:
        item = dict(scholarship)

        if item.get("status") == "matched":
            item["status"] = "eligible"
        elif item.get("status") == "needs_verification":
            item["status"] = "needs_verification"

        formatted_matches.append(item)

    return {
        "email": email,
        "total_matches": len(formatted_matches),
        "eligible_count": eligible_count,
        "verification_count": verification_count,
        "matches": formatted_matches,
    }


# ============================================================
# SAVE SCHOLARSHIP
# ============================================================

@app.post("/saved/{email}")
def save_scholarship_endpoint(
    email: str,
    request: SaveScholarshipRequest,
    current_user: dict = Depends(get_current_user),
):
    verify_user_access(email, current_user)

    profile = get_profile(email)

    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Student profile not found",
        )

    save_scholarship(
        email=email,
        scholarship_id=request.scholarship_id,
        scholarship_name=request.scholarship_name,
        deadline=request.deadline,
    )

    return {
        "message": "Scholarship saved successfully",
        "scholarship_id": request.scholarship_id,
        "scholarship_name": request.scholarship_name,
    }


# ============================================================
# GET SAVED SCHOLARSHIPS
# ============================================================

@app.get("/saved/{email}")
def get_saved(
    email: str,
    current_user: dict = Depends(get_current_user),
):
    verify_user_access(email, current_user)

    profile = get_profile(email)

    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Student profile not found",
        )

    saved = get_saved_scholarships(email)

    return {
        "email": email,
        "total_saved": len(saved),
        "saved": saved,
    }


# ============================================================
# REMOVE SAVED SCHOLARSHIP
# ============================================================

@app.delete("/saved/{email}/{scholarship_id}")
def delete_saved(
    email: str,
    scholarship_id: str,
    current_user: dict = Depends(get_current_user),
):
    verify_user_access(email, current_user)

    profile = get_profile(email)

    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Student profile not found",
        )

    removed = remove_saved_scholarship(
        email,
        scholarship_id,
    )

    if not removed:
        raise HTTPException(
            status_code=404,
            detail="Saved scholarship not found",
        )

    return {
        "message": "Scholarship removed successfully",
        "scholarship_id": scholarship_id,
    }


# ============================================================
# UPDATE SCHOLARSHIP STATUS
# ============================================================

@app.patch("/saved/{email}/{scholarship_id}")
def change_scholarship_status(
    email: str,
    scholarship_id: str,
    request: ScholarshipStatusRequest,
    current_user: dict = Depends(get_current_user),
):
    verify_user_access(email, current_user)

    profile = get_profile(email)

    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Student profile not found",
        )

    allowed_statuses = {
        "saved",
        "applied",
        "not_applied",
    }

    if request.status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid status. Use: "
                "saved, applied, not_applied"
            ),
        )

    updated = update_scholarship_status(
        email,
        scholarship_id,
        request.status,
    )

    if not updated:
        raise HTTPException(
            status_code=404,
            detail="Saved scholarship not found",
        )

    return {
        "message": "Scholarship status updated",
        "scholarship_id": scholarship_id,
        "status": request.status,
    }


# ============================================================
# DEADLINE INFORMATION
# ============================================================

@app.get("/deadline/{deadline}")
def get_deadline_info(deadline: str):
    if not deadline:
        return {
            "deadline": None,
            "days_remaining": None,
            "status": "unknown",
        }

    formats = [
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y-%m-%d",
        "%d %B %Y",
        "%d %b %Y",
    ]

    parsed_date = None

    for date_format in formats:
        try:
            parsed_date = datetime.strptime(
                deadline,
                date_format,
            )
            break
        except ValueError:
            continue

    if parsed_date is None:
        return {
            "deadline": deadline,
            "days_remaining": None,
            "status": "check_portal",
        }

    today = datetime.now().date()
    deadline_date = parsed_date.date()
    days_remaining = (deadline_date - today).days

    if days_remaining < 0:
        status = "expired"
    elif days_remaining <= 3:
        status = "urgent"
    elif days_remaining <= 7:
        status = "soon"
    else:
        status = "open"

    return {
        "deadline": deadline,
        "days_remaining": days_remaining,
        "status": status,
    }