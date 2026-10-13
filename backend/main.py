import os
import shutil
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Request, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import APP_TITLE, APP_VERSION, UPLOAD_DIR, MEDIA_DIR, DB_PATH, BASE_DIR
from database import (
    init_db, save_textbook, get_textbook, get_all_textbooks, 
    delete_textbook, clear_all_textbooks,
    get_chunks_for_textbook, get_user_performance, get_media_for_textbook,
    get_concept_graph, record_user_concept_progress, get_user_concept_progress,
    create_user, get_user_by_email, get_user_by_id, update_user_profile,
    set_user_reset_token, reset_user_password
)
from models import (
    UserLogin, UserRegister, UserResponse, UserProfileUpdate,
    ForgotPasswordRequest, ResetPasswordRequest,
    TextbookMetadata, SummarizeRequest, SummarizeResponse,
    ExplainRequest, ExplainResponse,
    VisualizeRequest, VisualizeResponse,
    ChatQueryRequest, ChatQueryResponse,
    QuizGenerateRequest, QuizGenerateResponse,
    QuizSubmitRequest, QuizSubmitResponse,
    PerformanceOverview, RecommendationPack,
    TranslateRequest, TranslateResponse,
    ConceptGraphResponse, ConceptDetailResponse,
    ConceptGraphGenerateRequest,
    AssessmentGenerateRequest, AssessmentGenerateResponse,
    AssessmentSubmitRequest, AssessmentSubmitResponse, SingleQuestionEvaluation,
    MisconceptionHypothesis,
    AdaptiveNextStepRequest, AdaptiveNextStepResponse,
    ClarifyReasoningRequest, ClarifyReasoningResponse,
    LearningPathStep, PersonalizedLearningPathResponse,
    PersonalizedLearningPathRequest, ConceptProgressUpdateRequest,
    ConceptProgressResponse, NodeExplanationRequest, NodeExplanationResponse,
    VerifyLearningPathStepRequest, VerifyLearningPathStepResponse,
    UnifiedCourseResourcesResponse, RecommendedResource, StudentLearningGapDiagnosis,
    AdaptiveExplainRequest, AdaptiveExplainResponse,
    DiagnosticQuestionRequest, DiagnosticQuestionResponse,
    DiagnosticSubmitRequest, DiagnosticSubmitResponse,
    AdaptivePracticeSubmitRequest, AdaptivePracticeSubmitResponse
)
from services.demo_data import get_demo_textbook_data, generate_sample_pdf_if_needed, SAMPLE_FILENAME
from services.pdf_service import extract_textbook_from_pdf
from services.multimodal_service import process_multimodal_file, detect_file_type
from services.concept_graph_service import (
    generate_course_concept_graph,
    get_concept_details as fetch_concept_details
)
from services.summarization_service import summarize_textbook_content
from services.explanation_service import (
    generate_adaptive_explanation,
    generate_adaptive_explanation_pipeline,
    generate_diagnostic_question_pipeline,
    evaluate_diagnostic_session_pipeline,
    evaluate_adaptive_practice_pipeline,
    determine_concept_mastery_level
)
from services.visualization_service import generate_visual_explanation
from services.learning_path_service import (
    generate_personalized_learning_path,
    explain_learning_path_node,
    verify_learning_path_step
)
from services.resource_index_service import build_unified_resource_index
from services.rag_service import answer_textbook_query
from services.quiz_service import generate_quiz, evaluate_quiz_submission
from services.assessment_service import (
    generate_dynamic_assessment_questions,
    evaluate_student_answer,
    select_adaptive_next_step,
    diagnose_misconception
)
from services.adaptive_service import get_personalized_recommendation
from services.translation_service import translate_text
from services.auth_service import (
    hash_password, verify_password, create_access_token, decode_access_token,
    validate_registration_input, generate_password_reset_token
)
from datetime import datetime, timedelta

# Initialize Database on startup
init_db()

# Auto-seed the sample textbook and concept graph so system works instantly
sample_pdf_path = UPLOAD_DIR / SAMPLE_FILENAME
generate_sample_pdf_if_needed(sample_pdf_path)
demo_data = get_demo_textbook_data()
save_textbook(demo_data["metadata"], demo_data["chunks"])
generate_course_concept_graph(demo_data["metadata"]["id"])

app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description="Backend API for AI-Powered Multilingual Textbook Summarization and Adaptive Learning System"
)

# Enable CORS for React frontend (Vite default port 5173 / 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Authentication & Session Security Dependency ---
security = HTTPBearer(auto_error=False)

def get_current_user(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    """
    Enforces authentication for protected endpoints.
    Accepts Bearer token in Authorization header, custom header, or access_token cookie.
    """
    token = None
    if creds and creds.credentials:
        token = creds.credentials
    elif "authorization" in request.headers:
        auth_header = request.headers["authorization"]
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
        else:
            token = auth_header.strip()
    elif "access_token" in request.cookies:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in to access learning resources.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired or is invalid. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user = get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found. Please register or sign in again.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user

def format_user_response(user: dict, token: Optional[str] = None) -> UserResponse:
    return UserResponse(
        id=user["id"],
        name=user["name"],
        email=user["email"],
        organisation=user.get("organisation", "") or "",
        org_type=user.get("org_type", "College") or "College",
        department=user.get("department", "") or "",
        role_year=user.get("role_year", "") or "",
        preferred_language=user.get("preferred_language", "en") or "en",
        profile_picture=user.get("profile_picture", "") or "",
        token=token,
        created_at=user.get("created_at")
    )

# --- Authentication Routes ---
@app.post("/api/auth/register", response_model=UserResponse)
def register(data: UserRegister):
    is_valid, err_msg = validate_registration_input(
        name=data.name,
        email=data.email,
        password=data.password,
        confirm_password=data.confirm_password,
        org_type=data.org_type,
        preferred_language=data.preferred_language
    )
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)

    existing = get_user_by_email(data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists. Please log in instead."
        )

    hashed_pwd = hash_password(data.password)
    user_id = f"usr_{uuid.uuid4().hex[:12]}"
    user_data = {
        "id": user_id,
        "name": data.name.strip(),
        "email": data.email.strip().lower(),
        "password_hash": hashed_pwd,
        "organisation": (data.organisation or "").strip(),
        "org_type": data.org_type or "College",
        "department": (data.department or "").strip(),
        "role_year": (data.role_year or "").strip(),
        "preferred_language": data.preferred_language or "en",
        "profile_picture": (data.profile_picture or "").strip(),
        "created_at": datetime.now().isoformat()
    }
    user = create_user(user_data)
    if not user:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create user account.")

    token, _ = create_access_token(user["id"], user["email"], user["name"], remember_me=False)
    return format_user_response(user, token)

@app.post("/api/auth/login", response_model=UserResponse)
def login(data: UserLogin):
    email = (data.email or "").strip().lower()
    if not email or not data.password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email and password are required.")

    user = get_user_by_email(email)
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Please verify your credentials."
        )

    token, _ = create_access_token(user["id"], user["email"], user["name"], remember_me=bool(data.remember_me))
    return format_user_response(user, token)

@app.get("/api/auth/me", response_model=UserResponse)
def get_me(current_user: dict = Depends(get_current_user)):
    return format_user_response(current_user)

@app.put("/api/auth/profile", response_model=UserResponse)
def update_profile(data: UserProfileUpdate, current_user: dict = Depends(get_current_user)):
    updates = {}
    if data.name is not None:
        if len(data.name.strip()) < 2:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Full name must be at least 2 characters.")
        updates["name"] = data.name.strip()
    if data.organisation is not None:
        updates["organisation"] = data.organisation.strip()
    if data.org_type is not None:
        if data.org_type not in ["College", "University", "School", "Company", "Other"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid organization type.")
        updates["org_type"] = data.org_type
    if data.department is not None:
        updates["department"] = data.department.strip()
    if data.role_year is not None:
        updates["role_year"] = data.role_year.strip()
    if data.preferred_language is not None:
        if data.preferred_language not in ["en", "ta"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Preferred language must be 'en' or 'ta'.")
        updates["preferred_language"] = data.preferred_language
    if data.profile_picture is not None:
        updates["profile_picture"] = data.profile_picture

    updated_user = update_user_profile(current_user["id"], updates)
    return format_user_response(updated_user)

@app.post("/api/auth/forgot-password")
def forgot_password(data: ForgotPasswordRequest):
    email = (data.email or "").strip().lower()
    user = get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No registered account found with that email address.")

    reset_token = generate_password_reset_token()
    expiry_iso = (datetime.now() + timedelta(minutes=15)).isoformat()
    set_user_reset_token(email, reset_token, expiry_iso)
    return {
        "status": "success",
        "message": f"Password reset verification code generated for {email}.",
        "reset_token": reset_token
    }

@app.post("/api/auth/reset-password")
def reset_password(data: ResetPasswordRequest):
    email = (data.email or "").strip().lower()
    if len(data.new_password) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must be at least 6 characters long.")

    new_hash = hash_password(data.new_password)
    success = reset_user_password(email, data.reset_token.strip(), new_hash)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset code. Please request a new code.")

    return {
        "status": "success",
        "message": "Password successfully reset. You can now log in with your new password."
    }

@app.post("/api/auth/logout")
def logout():
    return {
        "status": "success",
        "message": "Session terminated successfully."
    }


# --- Textbook Management & Upload Routes ---
@app.get("/api/textbooks", response_model=List[TextbookMetadata])
def list_textbooks(current_user: dict = Depends(get_current_user)):
    return get_all_textbooks(user_id=current_user["id"])

@app.get("/api/textbook/{textbook_id}")
def get_textbook_details(textbook_id: str, current_user: dict = Depends(get_current_user)):
    tb = get_textbook(textbook_id)
    if not tb:
        raise HTTPException(status_code=404, detail="Textbook not found")
    return tb

@app.delete("/api/textbooks/{textbook_id}")
def remove_textbook_endpoint(textbook_id: str, current_user: dict = Depends(get_current_user)):
    success = delete_textbook(textbook_id, user_id=current_user["id"])
    if not success:
        raise HTTPException(status_code=404, detail="Material not found or access denied")
    return {
        "status": "success",
        "message": "Material removed successfully",
        "deleted_id": textbook_id
    }

@app.delete("/api/textbooks")
def clear_textbooks_endpoint(current_user: dict = Depends(get_current_user)):
    deleted_count = clear_all_textbooks(user_id=current_user["id"])
    return {
        "status": "success",
        "message": f"All materials cleared ({deleted_count} items removed)",
        "deleted_count": deleted_count
    }

@app.post("/api/sample-textbook")
def load_sample_textbook(current_user: dict = Depends(get_current_user)):
    data = get_demo_textbook_data()
    save_textbook(data["metadata"], data["chunks"])
    generate_course_concept_graph(data["metadata"]["id"], force_regenerate=True)
    return {
        "status": "success",
        "message": "Sample DBMS textbook loaded successfully",
        "textbook": data["metadata"]
    }

@app.post("/api/upload")
def upload_textbook(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    filename = file.filename
    ext = Path(filename).suffix.lower()
    
    # Validate supported formats: PDF, PPT/PPTX, MP4
    if ext not in [".pdf", ".ppt", ".pptx", ".mp4"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file format '{ext}'. TextIQ supports PDF textbooks (.pdf), PowerPoint lecture slides (.ppt, .pptx), and MP4 lecture videos (.mp4)."
        )
        
    file_path = UPLOAD_DIR / filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        metadata, chunks, media_items = process_multimodal_file(file_path, filename)
        metadata["user_id"] = current_user["id"]
        save_textbook(metadata, chunks, media_items)
        
        # Dynamically build and cache concept graph for this course
        try:
            generate_course_concept_graph(metadata["id"], force_regenerate=True)
        except Exception as ge:
            print(f"Concept graph indexing note: {ge}")
        
        source_label = metadata.get("source_type", "file").capitalize()
        return {
            "status": "success",
            "message": f"{source_label} '{metadata['title']}' processed and indexed into course knowledge base with concept graph",
            "metadata": metadata
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process {filename}: {str(e)}")

# --- Innovation 2: Concept & Prerequisite Graph Routes ---
@app.get("/api/concept-graph/{textbook_id}", response_model=ConceptGraphResponse)
def get_course_concept_graph(textbook_id: str, current_user: dict = Depends(get_current_user)):
    try:
        graph = generate_course_concept_graph(textbook_id, force_regenerate=False)
        return ConceptGraphResponse(**graph)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating concept graph: {str(e)}")

@app.post("/api/concept-graph/generate", response_model=ConceptGraphResponse)
def regenerate_concept_graph(req: ConceptGraphGenerateRequest, current_user: dict = Depends(get_current_user)):
    try:
        graph = generate_course_concept_graph(req.course_id, force_regenerate=req.force_regenerate)
        return ConceptGraphResponse(**graph)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating concept graph: {str(e)}")

@app.get("/api/concept-graph/{textbook_id}/concept/{concept_id}", response_model=ConceptDetailResponse)
def get_single_concept_details(textbook_id: str, concept_id: str, current_user: dict = Depends(get_current_user)):
    details = fetch_concept_details(textbook_id, concept_id)
    if not details:
        raise HTTPException(status_code=404, detail="Concept not found")
    return ConceptDetailResponse(**details)

@app.get("/api/concept-graph/{textbook_id}/learning-paths")
def get_course_learning_paths(textbook_id: str, current_user: dict = Depends(get_current_user)):
    graph = generate_course_concept_graph(textbook_id)
    return {
        "course_id": textbook_id,
        "learning_paths": graph.get("learning_paths", []),
        "total_prerequisites": graph["stats"]["total_prerequisites"]
    }

# --- Summarization Route ---
@app.post("/api/summarize", response_model=SummarizeResponse)
def summarize(req: SummarizeRequest, current_user: dict = Depends(get_current_user)):
    tb = get_textbook(req.textbook_id)
    if not tb:
        raise HTTPException(status_code=404, detail="Textbook not found")
        
    chunks = get_chunks_for_textbook(req.textbook_id, chapter_id=req.chapter_id, section_id=req.section_id)
    if not chunks:
        chunks = get_chunks_for_textbook(req.textbook_id)
        
    chapter_title = "Overall Textbook Summary"
    if req.chapter_id and tb.get("chapters"):
        for ch in tb["chapters"]:
            if ch["id"] == req.chapter_id:
                chapter_title = ch["title"]
                break
                
    summary_data = summarize_textbook_content(chunks, chapter_title, language=req.language)
    return SummarizeResponse(**summary_data)

# --- Adaptive Explanation Route (Legacy & Enhanced) ---
@app.post("/api/explain", response_model=ExplainResponse)
def explain_concept(req: ExplainRequest, current_user: dict = Depends(get_current_user)):
    chunks = get_chunks_for_textbook(req.textbook_id)
    if not chunks:
        chunks = get_demo_textbook_data()["chunks"]
        
    explanation_data = generate_adaptive_explanation(
        chunks=chunks,
        topic=req.topic_or_concept,
        level=req.level,
        language=req.language
    )
    return ExplainResponse(**explanation_data)

# --- Innovation 6: Full Adaptive Explanation & Visual Learning Route ---
@app.post("/api/adaptive-explain", response_model=AdaptiveExplainResponse)
def adaptive_explain_concept(req: AdaptiveExplainRequest, current_user: dict = Depends(get_current_user)):
    try:
        explanation_data = generate_adaptive_explanation_pipeline(
            course_id=req.textbook_id,
            topic_or_concept=req.topic_or_concept,
            user_id=current_user["id"],
            requested_level=req.requested_level or "auto",
            preferred_visual_format=req.preferred_visual_format or "auto",
            language=req.language or "en"
        )
        return AdaptiveExplainResponse(**explanation_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating adaptive explanation: {str(e)}")

@app.post("/api/adaptive-explain/diagnostic", response_model=DiagnosticQuestionResponse)
def get_diagnostic_question(req: DiagnosticQuestionRequest, current_user: dict = Depends(get_current_user)):
    try:
        diag_data = generate_diagnostic_question_pipeline(
            course_id=req.textbook_id,
            concept=req.concept,
            user_id=current_user["id"],
            language=req.language or "en"
        )
        return DiagnosticQuestionResponse(**diag_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating diagnostic question: {str(e)}")

@app.post("/api/adaptive-explain/diagnostic/submit", response_model=DiagnosticSubmitResponse)
def submit_diagnostic_session(req: DiagnosticSubmitRequest, current_user: dict = Depends(get_current_user)):
    try:
        eval_result = evaluate_diagnostic_session_pipeline(
            course_id=req.course_id,
            concept_name=req.concept_name,
            answers=[a.dict() for a in req.answers],
            user_id=current_user["id"],
            language=req.language or "en"
        )
        return DiagnosticSubmitResponse(**eval_result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error evaluating diagnostic session: {str(e)}")

@app.post("/api/adaptive-explain/submit-practice", response_model=AdaptivePracticeSubmitResponse)
def submit_adaptive_practice(req: AdaptivePracticeSubmitRequest, current_user: dict = Depends(get_current_user)):
    try:
        eval_result = evaluate_adaptive_practice_pipeline(
            course_id=req.course_id,
            concept_name=req.concept_name,
            question_id=req.question_id,
            question_type=req.question_type or "mcq",
            student_answer=req.student_answer,
            current_level=req.current_level or "beginner",
            user_id=current_user["id"],
            language=req.language or "en"
        )
        return AdaptivePracticeSubmitResponse(**eval_result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error evaluating practice answer: {str(e)}")

@app.get("/api/adaptive-explain/concept-status/{textbook_id}/{concept_name}")
def get_concept_status(textbook_id: str, concept_name: str, current_user: dict = Depends(get_current_user)):
    try:
        status_info = determine_concept_mastery_level(
            course_id=textbook_id,
            topic_or_concept=concept_name,
            user_id=current_user["id"],
            requested_level="auto"
        )
        return {
            "course_id": textbook_id,
            "concept_name": concept_name,
            "user_id": current_user["id"],
            **status_info
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving concept status: {str(e)}")

# --- Innovation 5: Visual Explanation Route ---
@app.post("/api/visualize", response_model=VisualizeResponse)
def visualize_concept(req: VisualizeRequest, current_user: dict = Depends(get_current_user)):
    chunks = get_chunks_for_textbook(req.textbook_id)
    if not chunks:
        chunks = get_demo_textbook_data()["chunks"]
        
    visual_data = generate_visual_explanation(
        chunks=chunks,
        topic=req.topic,
        diagram_type=req.diagram_type or "auto",
        user_query=req.user_query,
        language=req.language or "en",
        level=req.level or "intermediate"
    )
    return VisualizeResponse(**visual_data)

# --- Innovation 5: Personalized Learning Paths & Node Explanations ---
@app.post("/api/learning-path/personalized", response_model=PersonalizedLearningPathResponse)
def get_personalized_path(req: PersonalizedLearningPathRequest, current_user: dict = Depends(get_current_user)):
    try:
        path_data = generate_personalized_learning_path(
            course_id=req.course_id,
            target_concept=req.target_concept,
            user_id=current_user["id"],
            language=req.language or "en"
        )
        return PersonalizedLearningPathResponse(**path_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating learning path: {str(e)}")

@app.get("/api/learning-path/personalized/{course_id}", response_model=PersonalizedLearningPathResponse)
def get_personalized_path_get(
    course_id: str, 
    target_concept: Optional[str] = Query(None), 
    current_user: dict = Depends(get_current_user)
):
    try:
        path_data = generate_personalized_learning_path(
            course_id=course_id,
            target_concept=target_concept,
            user_id=current_user["id"]
        )
        return PersonalizedLearningPathResponse(**path_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating learning path: {str(e)}")

@app.post("/api/learning-path/progress", response_model=ConceptProgressResponse)
def update_concept_progress(req: ConceptProgressUpdateRequest, current_user: dict = Depends(get_current_user)):
    try:
        record_user_concept_progress(
            user_id=current_user["id"],
            course_id=req.course_id,
            concept_id=req.concept_id,
            concept_name=req.concept_name,
            status=req.status,
            notes=req.notes
        )
        progress_items = get_user_concept_progress(current_user["id"], req.course_id)
        return ConceptProgressResponse(
            status="success",
            user_id=current_user["id"],
            course_id=req.course_id,
            progress_items=progress_items
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error recording progress: {str(e)}")

@app.get("/api/learning-path/progress/{course_id}", response_model=ConceptProgressResponse)
def fetch_concept_progress(course_id: str, current_user: dict = Depends(get_current_user)):
    try:
        progress_items = get_user_concept_progress(current_user["id"], course_id)
        return ConceptProgressResponse(
            status="success",
            user_id=current_user["id"],
            course_id=course_id,
            progress_items=progress_items
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching progress: {str(e)}")

@app.post("/api/learning-path/node-explain", response_model=NodeExplanationResponse)
def explain_node_endpoint(req: NodeExplanationRequest, current_user: dict = Depends(get_current_user)):
    try:
        data = explain_learning_path_node(
            course_id=req.course_id,
            topic=req.topic,
            node_label=req.node_label,
            context_excerpt=req.context_excerpt,
            language=req.language or "en"
        )
        return NodeExplanationResponse(**data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error explaining node: {str(e)}")

@app.get("/api/learning-path/resources/{course_id}", response_model=UnifiedCourseResourcesResponse)
def get_unified_course_resources(course_id: str, current_user: dict = Depends(get_current_user)):
    try:
        resources = build_unified_resource_index(course_id)
        counts_by_modality = {}
        for r in resources:
            mod = r.get("resource_type", "other")
            counts_by_modality[mod] = counts_by_modality.get(mod, 0) + 1
        return UnifiedCourseResourcesResponse(
            course_id=course_id,
            total_resources=len(resources),
            resource_types_available=list(counts_by_modality.keys()),
            counts_by_modality=counts_by_modality,
            resources=resources
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving unified resources: {str(e)}")

@app.post("/api/learning-path/verify-step", response_model=VerifyLearningPathStepResponse)
def verify_step_endpoint(req: VerifyLearningPathStepRequest, current_user: dict = Depends(get_current_user)):
    try:
        result = verify_learning_path_step(
            course_id=req.course_id,
            step_id=req.step_id,
            concept_name=req.concept_name,
            question_id=req.question_id,
            question_type=req.question_type or "mcq",
            question_text=req.question_text,
            student_answer=req.student_answer,
            correct_answer=req.correct_answer,
            options=req.options or [],
            user_id=current_user["id"],
            language=req.language or "en"
        )
        return VerifyLearningPathStepResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error verifying learning path step: {str(e)}")

# --- Grounded Q&A (RAG) Route (Innovation 3: Anti-Hallucination Tutor) ---
@app.post("/api/chat", response_model=ChatQueryResponse)
def chat_with_textbook(req: ChatQueryRequest, current_user: dict = Depends(get_current_user)):
    chunks = get_chunks_for_textbook(req.textbook_id)
    if not chunks and req.textbook_id == "tb_dbms_norm_001":
        chunks = get_demo_textbook_data()["chunks"]
        
    qa_data = answer_textbook_query(
        chunks=chunks,
        query=req.query,
        language=req.language,
        course_id=req.textbook_id,
        enable_outside_knowledge=req.enable_outside_knowledge or False,
        conversation_history=req.conversation_history or []
    )
    return ChatQueryResponse(**qa_data)

# --- Quiz Generation & Evaluation Routes ---
@app.post("/api/quiz/generate", response_model=QuizGenerateResponse)
def create_quiz(req: QuizGenerateRequest, current_user: dict = Depends(get_current_user)):
    quiz_data = generate_quiz(
        textbook_id=req.textbook_id,
        topic=req.topic,
        difficulty=req.difficulty,
        num_questions=req.num_questions,
        language=req.language or "en"
    )
    return QuizGenerateResponse(**quiz_data)

@app.post("/api/quiz/submit", response_model=QuizSubmitResponse)
def submit_quiz(req: QuizSubmitRequest, current_user: dict = Depends(get_current_user)):
    answers_payload = [a.model_dump() for a in req.answers]
    result_data = evaluate_quiz_submission(
        user_id=current_user["id"],
        textbook_id=req.textbook_id,
        quiz_id=req.quiz_id,
        topic=req.topic,
        difficulty=req.difficulty,
        answers=answers_payload,
        language=req.language or "en"
    )
    return QuizSubmitResponse(**result_data)

# --- Innovation 4: Misconception-Aware Adaptive Assessment Routes ---
@app.post("/api/assessment/generate", response_model=AssessmentGenerateResponse)
def generate_assessment(req: AssessmentGenerateRequest, current_user: dict = Depends(get_current_user)):
    try:
        data = generate_dynamic_assessment_questions(
            course_id=req.course_id,
            topic=req.topic,
            difficulty=req.difficulty or "medium",
            question_types=req.question_types,
            num_questions=req.num_questions,
            user_id=current_user["id"],
            target_concept=req.target_concept,
            focus_misconception=req.focus_misconception,
            language=req.language or "en"
        )
        return AssessmentGenerateResponse(**data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating assessment: {str(e)}")

@app.post("/api/assessment/submit", response_model=AssessmentSubmitResponse)
def submit_assessment(req: AssessmentSubmitRequest, current_user: dict = Depends(get_current_user)):
    try:
        from database import get_assessment_questions
        # Fetch question details from DB to evaluate server-side
        db_qs = {q["id"]: q for q in get_assessment_questions(req.course_id, limit=100)}
        
        evaluations = []
        correct_count = 0
        diagnosed_misconceptions = []
        weak_concepts = []
        strong_concepts = []
        
        for ans in req.answers:
            q_data = db_qs.get(ans.question_id)
            if not q_data:
                # Build transient question data from request if not in DB cache
                q_data = {
                    "id": ans.question_id,
                    "course_id": req.course_id,
                    "question": ans.question_text or "Assessment Question",
                    "topic": ans.topic or "General",
                    "concept_name": ans.concept_name or ans.topic or "General",
                    "question_type": ans.question_type or "mcq",
                    "difficulty": ans.difficulty or "medium",
                    "explanation": "Evidence evaluated against course content.",
                    "source_citation": {}
                }
            
            ev = evaluate_student_answer(
                question_dict=q_data,
                student_answer=ans.student_answer,
                user_id=current_user["id"],
                course_id=req.course_id,
                language=req.language or "en"
            )
            
            if ev["is_correct"]:
                correct_count += 1
                strong_concepts.append(q_data.get("concept_name", q_data.get("topic", "General")))
            else:
                weak_concepts.append(q_data.get("concept_name", q_data.get("topic", "General")))
                
            if ev.get("misconception"):
                diagnosed_misconceptions.append(MisconceptionHypothesis(**ev["misconception"]))
                
            evaluations.append(SingleQuestionEvaluation(**ev))
            
        total_q = len(evaluations)
        score_pct = round((correct_count / total_q) * 100, 1) if total_q > 0 else 0.0
        
        # Build intelligent recommendation
        if diagnosed_misconceptions:
            top_m = diagnosed_misconceptions[0]
            rec_text = f"Possible Misconception Hypothesis on '{top_m.concept_name}': {top_m.hypothesis_text} Review corrective practice in Adaptive Remediation."
        elif weak_concepts:
            rec_text = f"We detected lower accuracy on '{weak_concepts[0]}'. An adaptive practice drill has been prepared for this concept."
        else:
            rec_text = f"Outstanding performance! Score: {score_pct}%. Ready to advance to higher difficulty assessment drills."
            
        return AssessmentSubmitResponse(
            course_id=req.course_id,
            total_questions=total_q,
            correct_count=correct_count,
            score_percentage=score_pct,
            evaluations=evaluations,
            detected_misconceptions=diagnosed_misconceptions,
            weak_concepts=list(set(weak_concepts)),
            strong_concepts=list(set(strong_concepts)),
            next_recommendation=rec_text
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error evaluating assessment: {str(e)}")

@app.post("/api/assessment/adaptive-next", response_model=AdaptiveNextStepResponse)
def get_adaptive_next_question(req: AdaptiveNextStepRequest, current_user: dict = Depends(get_current_user)):
    try:
        next_step = select_adaptive_next_step(
            course_id=req.course_id,
            user_id=current_user["id"],
            current_topic=req.current_topic,
            current_concept=req.current_concept,
            last_question_id=req.last_question_id,
            last_was_correct=req.last_was_correct
        )
        return AdaptiveNextStepResponse(**next_step)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting adaptive next step: {str(e)}")

@app.get("/api/assessment/misconceptions/{course_id}")
def fetch_user_misconceptions(course_id: str, current_user: dict = Depends(get_current_user)):
    from database import get_user_misconceptions
    misconceptions = get_user_misconceptions(user_id=current_user["id"], course_id=course_id, status="active")
    return {"course_id": course_id, "user_id": current_user["id"], "misconceptions": misconceptions}

@app.post("/api/assessment/clarify-reasoning", response_model=ClarifyReasoningResponse)
def clarify_student_reasoning(req: ClarifyReasoningRequest, current_user: dict = Depends(get_current_user)):
    try:
        clean_ans = req.clarifying_answer.strip()
        confirmed = len(clean_ans) > 5 and not any(w in clean_ans.lower() for w in ["typo", "misread", "mistake", "slip", "misclick"])
        conf_level = "high" if confirmed else "low"
        
        feedback = (
            f"Thank you for clarifying your reasoning on '{req.concept_name}'. "
            f"Your explanation helps refine our adaptive understanding. "
            f"{'We have confirmed the conceptual nuance and scheduled a targeted contrast drill.' if confirmed else 'We noted this was a phrasing/reading slip and updated your profile.'}"
        )
        
        gen_res = generate_dynamic_assessment_questions(
            course_id=req.course_id,
            target_concept=req.concept_name,
            difficulty="medium",
            num_questions=1,
            user_id=current_user["id"]
        )
        next_q = gen_res["questions"][0] if gen_res.get("questions") else None
        
        return ClarifyReasoningResponse(
            status="success",
            confirmed_misconception=confirmed,
            confidence=conf_level,
            updated_feedback=feedback,
            next_practice_question=next_q
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing clarification: {str(e)}")

@app.get("/api/assessment/history/{course_id}")
def get_assessment_attempt_history(course_id: str, current_user: dict = Depends(get_current_user)):
    from database import get_user_assessment_history
    history = get_user_assessment_history(user_id=current_user["id"], course_id=course_id, limit=25)
    return {"course_id": course_id, "history": history}

# --- Performance & Recommendations Routes ---
@app.get("/api/performance", response_model=PerformanceOverview)
def get_performance(
    user_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    target_user_id = user_id or current_user.get("id", "demo_user")
    perf = get_user_performance(target_user_id)
    return PerformanceOverview(**perf)

@app.get("/api/recommendations", response_model=RecommendationPack)
def get_recommendation(
    topic: Optional[str] = None,
    course_id: Optional[str] = "tb_dbms_norm_001",
    language: Optional[str] = Query("en"),
    current_user: dict = Depends(get_current_user)
):
    rec = get_personalized_recommendation(
        user_id=current_user["id"], 
        target_topic=topic, 
        course_id=course_id, 
        language=language or "en"
    )
    return RecommendationPack(**rec)

# --- Translation Route ---
@app.post("/api/translate", response_model=TranslateResponse)
def translate_endpoint(req: TranslateRequest, current_user: dict = Depends(get_current_user)):
    translated = translate_text(
        text=req.text,
        target_lang=req.target_language,
        source_lang=req.source_language
    )
    return TranslateResponse(
        original_text=req.text,
        translated_text=translated,
        target_language=req.target_language
    )

# Mount Static Directory for Vanilla HTML/CSS/JS UI and Media
STATIC_DIR = BASE_DIR / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Mount Media Directory for extracted figures, diagrams, and video keyframes
if MEDIA_DIR.exists():
    app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")

from fastapi.responses import FileResponse

@app.get("/")
def root(request: Request):
    accept_header = request.headers.get("accept", "")
    index_file = STATIC_DIR / "index.html"
    if "text/html" in accept_header or not ("application/json" in accept_header):
        if index_file.exists():
            return FileResponse(str(index_file))
    return {
        "status": "online",
        "app": APP_TITLE,
        "version": APP_VERSION
    }

@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "app": APP_TITLE,
        "version": APP_VERSION,
        "endpoints": [
            "/api/textbooks", "/api/upload", "/api/sample-textbook",
            "/api/concept-graph/{textbook_id}", "/api/concept-graph/generate",
            "/api/concept-graph/{textbook_id}/concept/{concept_id}",
            "/api/concept-graph/{textbook_id}/learning-paths",
            "/api/summarize", "/api/explain", "/api/visualize",
            "/api/chat", "/api/quiz/generate", "/api/quiz/submit",
            "/api/assessment/generate", "/api/assessment/submit",
            "/api/assessment/adaptive-next", "/api/assessment/misconceptions/{course_id}",
            "/api/learning-path/personalized", "/api/learning-path/resources/{course_id}",
            "/api/learning-path/verify-step", "/api/learning-path/progress",
            "/api/learning-path/node-explain",
            "/api/performance", "/api/recommendations", "/api/translate"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
