from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# --- User & Auth Models ---
class UserLogin(BaseModel):
    email: str
    password: str
    remember_me: Optional[bool] = False

class UserRegister(BaseModel):
    name: str
    email: str
    password: str
    confirm_password: Optional[str] = None
    organisation: Optional[str] = ""
    org_type: Optional[str] = "College"  # College, University, School, Company, Other
    department: Optional[str] = ""
    role_year: Optional[str] = ""
    preferred_language: Optional[str] = "en"  # "en" or "ta"
    profile_picture: Optional[str] = ""

class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    organisation: Optional[str] = None
    org_type: Optional[str] = None
    department: Optional[str] = None
    role_year: Optional[str] = None
    preferred_language: Optional[str] = None
    profile_picture: Optional[str] = None

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    email: str
    reset_token: str
    new_password: str

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    organisation: Optional[str] = ""
    org_type: Optional[str] = "College"
    department: Optional[str] = ""
    role_year: Optional[str] = ""
    preferred_language: Optional[str] = "en"
    profile_picture: Optional[str] = ""
    token: Optional[str] = None
    created_at: Optional[str] = None

# --- Textbook & Structure Models ---
class SectionInfo(BaseModel):
    id: str
    title: str
    page_start: int
    page_end: int
    content: Optional[str] = ""

class ChapterInfo(BaseModel):
    id: str
    number: int
    title: str
    page_start: int
    page_end: int
    sections: List[SectionInfo] = []

class ExtractedMediaItem(BaseModel):
    id: str
    file_id: str
    filename: str
    source_type: str  # "pdf", "presentation", "video"
    content_type: str  # "image", "keyframe"
    page: Optional[int] = None
    slide: Optional[int] = None
    timestamp: Optional[str] = None
    media_path: str
    media_filename: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    format: Optional[str] = None
    description: Optional[str] = None

class TextbookChunk(BaseModel):
    id: str
    textbook_id: str
    material_id: Optional[str] = None
    source_type: Optional[str] = "pdf"
    filename: Optional[str] = None
    chapter_id: str
    chapter_title: str
    section_id: str
    section_title: str
    page: int
    slide_number: Optional[int] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    timestamp_str: Optional[str] = None
    content_type: Optional[str] = "text"
    content: str
    media_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class TextbookMetadata(BaseModel):
    id: str
    title: str
    filename: str
    source_type: Optional[str] = "pdf"
    total_pages: Optional[int] = 0
    total_slides: Optional[int] = None
    duration_seconds: Optional[float] = None
    duration_str: Optional[str] = None
    file_size_bytes: int
    extracted_images_count: Optional[int] = 0
    extracted_transcripts_count: Optional[int] = 0
    extracted_tables_count: Optional[int] = 0
    media_items: Optional[List[Dict[str, Any]]] = []
    chapters: List[ChapterInfo] = []
    created_at: str

# --- Summarization Models ---
class SummarizeRequest(BaseModel):
    textbook_id: str
    chapter_id: Optional[str] = None
    section_id: Optional[str] = None
    language: str = "en"  # "en" or "ta"

class SummarizeResponse(BaseModel):
    title: str
    summary: str
    key_concepts: List[str]
    important_points: List[str]
    quick_revision: List[str]
    language: str
    source_reference: str

# --- Adaptive Explanation Models ---
class ExplainRequest(BaseModel):
    textbook_id: str
    topic_or_concept: str
    level: str  # "beginner", "intermediate", "advanced"
    language: str = "en"  # "en" or "ta"

class ExplainResponse(BaseModel):
    concept: str
    level: str
    explanation: str
    key_terms: List[Dict[str, str]] = []  # term -> simple meaning
    example: str
    analogy: Optional[str] = None
    grounded_in_textbook: bool = True
    source_reference: str
    language: str

# --- Visual Explanation Models (Innovation 5) ---
class VisualizeRequest(BaseModel):
    textbook_id: str
    topic: str
    diagram_type: Optional[str] = "auto"  # "auto", "flowchart", "concept_map", "block_diagram", "sequence", "comparison", "timeline", "hierarchy", "cycle"
    user_query: Optional[str] = None
    language: Optional[str] = "en"
    level: Optional[str] = "intermediate"  # "beginner", "intermediate", "advanced"

class DiagramNodeItem(BaseModel):
    label: str
    description: str
    source_citation: Optional[Dict[str, Any]] = None
    is_supported: bool = True
    node_type: Optional[str] = "concept"  # "process_step", "decision", "actor", "component", "concept"

class VisualizeResponse(BaseModel):
    topic: str
    detected_type: str
    mermaid_code: str
    description: str
    source_reference: str
    steps_or_nodes: List[Dict[str, Any]] = []
    is_sufficient_evidence: bool = True
    limitation_note: Optional[str] = None
    available_alternative_types: List[str] = []
    course_id: Optional[str] = None

# --- Grounded Q&A (RAG) Models (Innovation 3: Anti-Hallucination & Provenance) ---
class ChatQueryRequest(BaseModel):
    textbook_id: str
    query: str
    language: str = "en"
    enable_outside_knowledge: Optional[bool] = False
    conversation_history: Optional[List[Dict[str, Any]]] = []

class CitationInfo(BaseModel):
    id: Optional[str] = None
    filename: Optional[str] = None
    chapter: str
    section: str
    page: Optional[int] = None
    slide: Optional[int] = None
    timestamp: Optional[str] = None
    source_type: Optional[str] = "pdf"
    excerpt: str
    media_url: Optional[str] = None
    relevance_score: Optional[float] = None

class ValidatedClaim(BaseModel):
    claim: str
    is_supported: bool
    evidence_snippet: Optional[str] = None
    citation_index: Optional[int] = None

class RelatedConceptInfo(BaseModel):
    id: str
    name: str
    topic: Optional[str] = None
    relationship_type: Optional[str] = "related"
    source_types: Optional[List[str]] = []

class ChatQueryResponse(BaseModel):
    query: str
    answer: str
    evidence_status: str = "fully_grounded"  # "fully_grounded", "partially_grounded", "unsupported", "outside_knowledge"
    is_grounded: bool = True
    confidence: float = 1.0
    citations: List[CitationInfo] = []
    validated_claims: Optional[List[ValidatedClaim]] = []
    unsupported_claims: Optional[List[str]] = []
    related_concepts: Optional[List[RelatedConceptInfo]] = []
    outside_knowledge_used: Optional[bool] = False
    outside_knowledge_content: Optional[str] = None
    course_id: Optional[str] = None
    language: str = "en"

# --- Quiz Models ---
class QuizGenerateRequest(BaseModel):
    textbook_id: str
    topic: str
    difficulty: str = "medium"  # "easy", "medium", "hard"
    num_questions: int = 5  # 5, 10, 15
    language: Optional[str] = "en"  # "en" or "ta"

class QuizOption(BaseModel):
    key: str  # "A", "B", "C", "D"
    text: str

class QuizQuestion(BaseModel):
    id: int
    topic: str
    question: str
    options: List[QuizOption]
    correct_key: str
    explanation: str
    source_page: int
    difficulty: str

class QuizGenerateResponse(BaseModel):
    quiz_id: str
    topic: str
    difficulty: str
    questions: List[QuizQuestion]

class UserAnswer(BaseModel):
    question_id: int
    selected_key: str

class QuizSubmitRequest(BaseModel):
    quiz_id: str
    textbook_id: Optional[str] = "tb_dbms_norm_001"
    topic: str
    difficulty: str
    answers: List[UserAnswer]
    language: Optional[str] = "en"

class QuestionResult(BaseModel):
    question_id: int
    question: str
    topic: str
    selected_key: str
    correct_key: str
    is_correct: bool
    explanation: str
    source_page: int

class TopicScore(BaseModel):
    topic: str
    total_questions: int
    correct_questions: int
    percentage: float
    status: str  # "Strong", "Moderate", "Weak"

class QuizSubmitResponse(BaseModel):
    quiz_id: str
    total_questions: int
    correct_count: int
    score_percentage: float
    results: List[QuestionResult]
    topic_breakdown: List[TopicScore]
    weak_topics: List[str]
    recommendation: str

# --- Adaptive Learning & Performance Models ---
class TopicMastery(BaseModel):
    topic: str
    mastery_percentage: float
    quizzes_taken: int
    status: str  # "Strong", "Moderate", "Weak"
    last_practiced: str

class PerformanceOverview(BaseModel):
    overall_progress: float  # e.g. 72.0
    quizzes_completed: int
    questions_answered: int
    accuracy_percentage: float
    strong_topics: List[str]
    weak_topics: List[str]
    topic_masteries: List[TopicMastery]
    recent_activity: List[Dict[str, Any]]

class RecommendationPack(BaseModel):
    topic: str
    weakness_reason: str
    short_explanation: str
    important_points: List[str]
    mermaid_diagram: str
    practice_questions: List[QuizQuestion]
    action_button_label: str

# --- Translation Models ---
class TranslateRequest(BaseModel):
    text: str
    target_language: str = "ta"  # "ta" for Tamil, "en" for English
    source_language: str = "en"

class TranslateResponse(BaseModel):
    original_text: str
    translated_text: str
    target_language: str

# --- Innovation 2: Concept and Prerequisite Graph Models ---
class ConceptSourceItem(BaseModel):
    id: str
    concept_id: str
    content_unit_id: Optional[str] = None
    source_type: str  # "pdf", "presentation", "video"
    filename: Optional[str] = None
    page_number: Optional[int] = None
    slide_number: Optional[int] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    timestamp_str: Optional[str] = None
    excerpt: str = ""
    media_path: Optional[str] = None

class ConceptNode(BaseModel):
    id: str
    name: str
    topic: str
    subtopic: Optional[str] = ""
    description: str
    sources: List[ConceptSourceItem] = []
    source_types: List[str] = []
    cross_modal_count: int = 1
    prerequisites: List[str] = []
    dependents: List[str] = []

class ConceptRelationshipEdge(BaseModel):
    id: str
    source: str
    target: str
    source_concept_id: str
    target_concept_id: str
    source_concept_name: str
    target_concept_name: str
    relationship_type: str  # "prerequisite", "related_to", "part_of", "explains", "example_of", "similar_to", "contrasts_with"
    confidence: float = 1.0
    evidence: str

class TopicSummary(BaseModel):
    name: str
    count: int

class ConceptGraphStats(BaseModel):
    total_concepts: int
    total_relationships: int
    total_prerequisites: int
    total_sources: int
    cross_modal_concepts: int
    total_topics: int

class ConceptGraphResponse(BaseModel):
    course_id: str
    nodes: List[ConceptNode]
    edges: List[ConceptRelationshipEdge]
    topics: List[TopicSummary]
    stats: ConceptGraphStats
    learning_paths: Optional[List[List[str]]] = []

class ConceptDetailResponse(BaseModel):
    concept: ConceptNode
    prerequisites: List[Dict[str, Any]]
    dependents: List[Dict[str, Any]]
    related_concepts: List[Dict[str, Any]]
    sources: List[ConceptSourceItem]

class ConceptGraphGenerateRequest(BaseModel):
    course_id: str
    force_regenerate: bool = False

# --- Innovation 4: Misconception-Aware Adaptive Assessment Models ---

class AssessmentCitation(BaseModel):
    id: Optional[str] = None
    filename: Optional[str] = None
    chapter: Optional[str] = None
    section: Optional[str] = None
    page: Optional[int] = None
    slide: Optional[int] = None
    timestamp: Optional[str] = None
    source_type: Optional[str] = "pdf"
    excerpt: Optional[str] = ""

class AssessmentOption(BaseModel):
    key: str  # "A", "B", "C", "D"
    text: str
    distractor_rationale: Optional[str] = None

class AssessmentQuestion(BaseModel):
    id: str
    course_id: str
    topic: str
    concept_id: Optional[str] = None
    concept_name: Optional[str] = None
    difficulty: str = "medium"  # "easy", "medium", "hard"
    question_type: str = "mcq"  # "mcq", "short_answer", "numerical", "concept_relationship"
    question: str
    options: Optional[List[AssessmentOption]] = []
    correct_key: Optional[str] = None
    expected_answer: Optional[str] = None
    acceptable_terms: Optional[List[str]] = []
    numerical_value: Optional[float] = None
    numerical_tolerance: Optional[float] = 0.05
    explanation: str
    source_citation: Optional[AssessmentCitation] = None
    source_chunk_id: Optional[str] = None
    prerequisite_concept: Optional[str] = None

class AssessmentGenerateRequest(BaseModel):
    course_id: str
    topic: Optional[str] = "All"
    difficulty: Optional[str] = "medium"  # "easy", "medium", "hard", "adaptive"
    question_types: Optional[List[str]] = ["mcq", "short_answer", "numerical", "concept_relationship"]
    num_questions: int = 5
    user_id: Optional[str] = "demo_user"
    target_concept: Optional[str] = None
    focus_misconception: Optional[str] = None
    language: Optional[str] = "en"  # "en" or "ta"

class AssessmentGenerateResponse(BaseModel):
    course_id: str
    topic: str
    difficulty: str
    questions: List[AssessmentQuestion]
    total_generated: int
    message: Optional[str] = None

class AssessmentSubmitAnswer(BaseModel):
    question_id: str
    student_answer: str
    question_text: Optional[str] = None
    topic: Optional[str] = None
    concept_name: Optional[str] = None
    question_type: Optional[str] = "mcq"
    difficulty: Optional[str] = "medium"
    clarifying_answer: Optional[str] = None

class MisconceptionHypothesis(BaseModel):
    concept_name: str
    topic: str
    misconception_title: str
    hypothesis_text: str
    expected_understanding: str
    confidence: str = "medium"  # "high", "medium", "low"
    clarifying_question: Optional[str] = None
    evidence_excerpt: Optional[str] = None
    source_citation: Optional[AssessmentCitation] = None

class SingleQuestionEvaluation(BaseModel):
    question_id: str
    is_correct: bool
    score: float  # 0.0 to 1.0
    evaluation_status: str  # "correct", "partially_correct", "incorrect"
    student_answer: str
    expected_answer: Optional[str] = None
    feedback: str
    explanation: str
    source_citation: Optional[AssessmentCitation] = None
    misconception: Optional[MisconceptionHypothesis] = None
    clarifying_question: Optional[str] = None

class AssessmentSubmitRequest(BaseModel):
    course_id: str
    answers: List[AssessmentSubmitAnswer]
    user_id: Optional[str] = "demo_user"
    language: Optional[str] = "en"  # "en" or "ta"

class AssessmentSubmitResponse(BaseModel):
    course_id: str
    total_questions: int
    correct_count: int
    score_percentage: float
    evaluations: List[SingleQuestionEvaluation]
    detected_misconceptions: List[MisconceptionHypothesis]
    weak_concepts: List[str]
    strong_concepts: List[str]
    next_recommendation: str

class AdaptiveNextStepRequest(BaseModel):
    course_id: str
    user_id: Optional[str] = "demo_user"
    current_topic: Optional[str] = None
    current_concept: Optional[str] = None
    last_question_id: Optional[str] = None
    last_was_correct: Optional[bool] = None

class AdaptiveNextStepResponse(BaseModel):
    action_type: str  # "difficulty_increase", "difficulty_decrease", "remediation_practice", "prerequisite_drill", "misconception_resolution", "mastery_check"
    rationale: str
    next_question: Optional[AssessmentQuestion] = None
    prerequisite_concept: Optional[str] = None
    remediation_explanation: Optional[str] = None
    active_misconceptions: Optional[List[Dict[str, Any]]] = []

class ClarifyReasoningRequest(BaseModel):
    course_id: str
    user_id: Optional[str] = "demo_user"
    question_id: str
    concept_name: str
    clarifying_answer: str

class ClarifyReasoningResponse(BaseModel):
    status: str
    confirmed_misconception: bool
    confidence: str
    updated_feedback: str
    next_practice_question: Optional[AssessmentQuestion] = None


# =========================================================================
# =========================================================================
# INNOVATION 5 & MULTIMODAL ADAPTIVE LEARNING PATH MODELS
# =========================================================================

class RecommendedResource(BaseModel):
    resource_id: str
    course_id: str
    resource_type: str  # "pdf_passage", "presentation_slide", "video_segment", "diagram", "visual_model", "worked_example", "targeted_quiz"
    title: str
    filename: str
    concept_name: str
    topic: Optional[str] = None
    content_snippet: str
    page_number: Optional[int] = None
    slide_number: Optional[int] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    timestamp_str: Optional[str] = None
    media_path: Optional[str] = None
    provenance_ref: str
    difficulty_level: Optional[str] = "intermediate"
    selection_criteria: Optional[str] = ""
    ranking_score: Optional[float] = 0.0
    navigation_target: Optional[Dict[str, Any]] = None
    question_data: Optional[Dict[str, Any]] = None

class StudentLearningGapDiagnosis(BaseModel):
    has_assessment_history: bool = False
    total_attempts: int = 0
    active_misconceptions_count: int = 0
    demonstrated_gaps_count: int = 0
    untested_prerequisites_count: int = 0
    verified_prerequisites_count: int = 0
    primary_blocker_concept: Optional[str] = None
    diagnostic_summary: str = ""

class LearningPathStep(BaseModel):
    concept_id: str
    concept_name: str
    topic: str
    step_number: int
    is_prerequisite: bool = False
    is_target: bool = False
    is_followup: bool = False
    mastery_status: str = "ready"  # "mastered", "needs_revision", "in_progress", "ready", "locked", "studied", "untested"
    mastery_percentage: Optional[float] = None
    accuracy_score: Optional[float] = None
    assessment_attempts_count: int = 0
    has_active_misconception: bool = False
    active_misconception_title: Optional[str] = None
    recommendation_reason: str = ""
    description: str = ""
    source_citations: List[Dict[str, Any]] = []
    prerequisites_needed: List[str] = []
    dependents_unlocked: List[str] = []
    
    # Multimodal Adaptive Recommendation fields
    learning_gap_type: Optional[str] = "untested"  # "demonstrated_gap", "active_misconception", "untested_prerequisite", "verified_foundation", "untested"
    suitable_level: Optional[str] = "beginner"  # "beginner", "intermediate", "advanced"
    measurable_objective: Optional[str] = ""
    recommended_resource: Optional[RecommendedResource] = None
    alternative_resources: Optional[List[RecommendedResource]] = []
    targeted_assessment: Optional[Dict[str, Any]] = None

class PersonalizedLearningPathResponse(BaseModel):
    course_id: str
    target_concept: str
    target_concept_id: Optional[str] = None
    is_personalized_with_assessment: bool = True
    total_steps: int
    completed_steps: int
    next_recommended_concept: str
    next_recommended_step_number: int
    recommendation_rationale: str
    recommended_action_type: str = "study_target"  # "review_prerequisite", "study_target", "resolve_misconception", "advance_next", "begin_foundations"
    steps: List[LearningPathStep]
    active_misconceptions: List[Dict[str, Any]] = []
    prerequisite_graph_stats: Dict[str, Any] = {}
    available_target_concepts: List[str] = []
    
    # Multimodal Adaptive Recommendation top fields
    next_recommended_resource: Optional[RecommendedResource] = None
    student_learning_gap_diagnosis: Optional[StudentLearningGapDiagnosis] = None
    diagnostic_question: Optional[Dict[str, Any]] = None

class PersonalizedLearningPathRequest(BaseModel):
    course_id: str
    target_concept: Optional[str] = None
    user_id: Optional[str] = "demo_user"
    language: Optional[str] = "en"  # "en" or "ta"

class VerifyLearningPathStepRequest(BaseModel):
    course_id: str
    concept_id: Optional[str] = None
    concept_name: str
    question_id: str
    student_answer: str
    user_id: Optional[str] = "demo_user"
    target_concept: Optional[str] = None
    step_id: Optional[str] = None
    question_type: Optional[str] = "mcq"
    question_text: Optional[str] = ""
    correct_answer: Optional[str] = ""
    options: Optional[List[Any]] = []
    language: Optional[str] = "en"  # "en" or "ta"

class VerifyLearningPathStepResponse(BaseModel):
    status: str  # "verified", "needs_revision", "error"
    is_correct: bool
    score: float
    feedback: str
    concept_name: str
    updated_accuracy_score: float
    updated_mastery_status: str
    active_misconception: Optional[Dict[str, Any]] = None
    next_recommended_concept: str
    next_recommended_action: str
    feedback_rationale: str
    refreshed_learning_path: Optional[PersonalizedLearningPathResponse] = None
    language: Optional[str] = "en"

class UnifiedCourseResourcesResponse(BaseModel):
    course_id: str
    total_resources: int
    resource_types_available: List[str] = []
    counts_by_modality: Optional[Dict[str, int]] = {}
    resources: List[RecommendedResource] = []


class ConceptProgressUpdateRequest(BaseModel):
    course_id: str
    concept_id: str
    concept_name: str
    status: str = "studied"  # "studied", "needs_review", "bookmarked"
    user_id: Optional[str] = "demo_user"
    notes: Optional[str] = None

class ConceptProgressResponse(BaseModel):
    status: str
    user_id: str
    course_id: str
    progress_items: List[Dict[str, Any]]

class NodeExplanationRequest(BaseModel):
    course_id: str
    topic: str
    node_label: str
    context_excerpt: Optional[str] = None
    language: Optional[str] = "en"

class NodeExplanationResponse(BaseModel):
    course_id: str
    topic: str
    node_label: str
    simple_explanation: str
    analogy: Optional[str] = None
    grounded_evidence: str
    source_citation: Optional[Dict[str, Any]] = None
    related_concepts: List[str] = []
    language: str = "en"


# =========================================================================
# INNOVATION 6: ADAPTIVE EXPLANATION & VISUAL LEARNING MODELS
# =========================================================================

class AdaptiveExplainRequest(BaseModel):
    textbook_id: str
    topic_or_concept: str
    user_id: Optional[str] = "demo_user"
    requested_level: Optional[str] = "auto"  # "auto", "beginner", "intermediate", "advanced"
    preferred_visual_format: Optional[str] = "auto"  # "auto", "flowchart", "concept_map", "block_diagram", "sequence", "comparison", "timeline", "hierarchy", "cycle", "none"
    language: Optional[str] = "en"

class AdaptiveExplainResponse(BaseModel):
    concept: str
    topic: str
    level: str  # "beginner", "intermediate", "advanced"
    level_determination_method: str  # "assessment_mastery", "misconception_driven", "prerequisite_fallback", "diagnostic_calibrated", "user_selected", "cold_start_default"
    mastery_score: Optional[float] = None
    mastery_status: str = "Unassessed"  # "Mastered", "Developing", "Needs Remediation", "Prerequisite Remediation Needed", "Unassessed"
    observed_attempts_count: int = 0
    active_misconception: Optional[Dict[str, Any]] = None
    explanation: str
    key_terms: List[Dict[str, str]] = []
    example: str
    analogy: Optional[str] = None
    formal_notes_or_limitations: Optional[str] = None
    visual_format: str = "concept_map"
    visual_representation: Optional[Dict[str, Any]] = None
    practice_question: Optional[Dict[str, Any]] = None
    is_sufficient_evidence: bool = True
    limitation_note: Optional[str] = None
    citations: List[Dict[str, Any]] = []
    source_reference: str = ""
    course_id: str = ""
    language: str = "en"
    available_levels: List[str] = ["beginner", "intermediate", "advanced"]
    available_visual_formats: List[str] = ["flowchart", "concept_map", "block_diagram", "sequence", "comparison", "timeline", "hierarchy", "cycle"]

class DiagnosticQuestionRequest(BaseModel):
    textbook_id: str
    concept: str
    user_id: Optional[str] = "demo_user"
    language: Optional[str] = "en"

class DiagnosticQuestionResponse(BaseModel):
    concept: str
    course_id: str
    total_questions: int = 1
    questions: List[Dict[str, Any]] = []
    prerequisites_covered: List[str] = []
    is_sufficient_evidence: bool = True
    limitation_note: Optional[str] = None
    question: Optional[Dict[str, Any]] = None  # for backward compatibility

class DiagnosticAnswerItem(BaseModel):
    question_id: str
    question_type: str = "mcq"
    student_answer: str
    concept_name: Optional[str] = None
    topic: Optional[str] = None
    is_prerequisite: bool = False
    prerequisite_concept: Optional[str] = None

class DiagnosticSubmitRequest(BaseModel):
    course_id: str
    concept_name: str
    user_id: Optional[str] = "demo_user"
    answers: List[DiagnosticAnswerItem]
    language: Optional[str] = "en"

class DiagnosticSubmitResponse(BaseModel):
    concept_name: str
    course_id: str
    total_questions: int
    correct_count: int
    score_percentage: float
    calibrated_level: str  # "beginner", "intermediate", "advanced"
    recommended_visual_format: str
    demonstrated_strengths: List[str] = []
    knowledge_gaps: List[str] = []
    possible_misconceptions: List[Dict[str, Any]] = []
    diagnostic_summary: str
    recommended_action: str = "study_calibrated_level"
    is_sufficient_evidence: bool = True
    limitation_note: Optional[str] = None
    evaluations: List[Dict[str, Any]] = []
    updated_mastery_status: str = "Developing"
    updated_mastery_percentage: Optional[float] = None

class AdaptivePracticeSubmitRequest(BaseModel):
    course_id: str
    concept_name: str
    user_id: Optional[str] = "demo_user"
    question_id: str
    question_type: str = "mcq"
    student_answer: str
    current_level: str = "beginner"
    language: Optional[str] = "en"

class AdaptivePracticeSubmitResponse(BaseModel):
    is_correct: bool
    score: float
    feedback: str
    explanation: str
    diagnosed_misconception: Optional[Dict[str, Any]] = None
    current_level: str
    next_recommended_level: str
    adaptation_summary: str
    updated_mastery_percentage: Optional[float] = None
    recommended_action: str = "continue_practice"  # "level_up", "level_down", "review_prerequisite", "continue_practice"



