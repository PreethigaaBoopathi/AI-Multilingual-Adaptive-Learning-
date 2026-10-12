import re
from typing import Dict, Any, List, Optional, Tuple, Set
from database import (
    get_concept_graph, get_concept_details,
    get_adaptive_concept_performance, get_user_misconceptions,
    record_user_concept_progress, get_user_concept_progress,
    get_chunks_for_textbook, record_assessment_attempt,
    resolve_misconception, upsert_misconception_profile,
    get_assessment_questions, save_assessment_question
)
from services.concept_graph_service import generate_course_concept_graph
from services.rag_service import answer_textbook_query
from services.explanation_service import generate_adaptive_explanation
from services.resource_index_service import (
    build_unified_resource_index,
    find_matching_resources_for_concept,
    select_best_multimodal_resource
)
from services.assessment_service import (
    evaluate_student_answer,
    diagnose_misconception,
    generate_dynamic_assessment_questions
)
from services.translation_service import translate_text

# =========================================================================
# INNOVATION: MULTIMODAL ADAPTIVE LEARNING PATH RECOMMENDATION SERVICE
# =========================================================================

def _normalize_name(name: str) -> str:
    """Normalizes string for robust matching."""
    return re.sub(r'[^a-zA-Z0-9]', '', (name or "").lower().strip())

def _clean_title(t: str) -> str:
    """Strips leading numbering/formatting for robust concept matching."""
    return re.sub(r'^(?:\d+[\.\)]*\s*)+', '', (t or "")).strip().lower()

def _match_concept_dict(concept_name: str, target_map: Dict[str, Any]) -> Optional[Any]:
    """Matches a concept against a dictionary keyed by concept names/strings."""
    if not concept_name or not target_map:
        return None
    c_lower = concept_name.lower().strip()
    c_clean = _clean_title(concept_name)
    c_norm = _normalize_name(concept_name)
    c_clean_norm = _normalize_name(c_clean)

    # 1. Exact direct matches
    if c_lower in target_map:
        return target_map[c_lower]
    if c_clean in target_map:
        return target_map[c_clean]

    # 2. Flexible normalized and substring matches
    for k, v in target_map.items():
        k_clean = _clean_title(k)
        k_norm = _normalize_name(k)
        if k_clean == c_clean or k_norm == c_norm or k_norm == c_clean_norm:
            return v
        if len(k_clean) > 3 and len(c_clean) > 3 and (k_clean in c_clean or c_clean in k_clean):
            return v
    return None

def find_concept_in_graph(graph: Dict[str, Any], query_name: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Finds a concept node in graph matching query name by exact, normalized, or fuzzy matching.
    """
    nodes = graph.get("nodes", [])
    if not nodes:
        return None

    if not query_name or not query_name.strip():
        # Pick concept with highest in-degree (most prerequisites) or last non-trivial node
        prereq_edges = [e for e in graph.get("edges", []) if e.get("relationship_type") == "prerequisite"]
        target_counts: Dict[str, int] = {}
        for e in prereq_edges:
            tgt = e["target_concept_id"]
            target_counts[tgt] = target_counts.get(tgt, 0) + 1
        
        if target_counts:
            best_id = max(target_counts.items(), key=lambda x: x[1])[0]
            for n in nodes:
                if n["id"] == best_id:
                    return n
        return nodes[-1] if len(nodes) > 1 else nodes[0]

    q_norm = _normalize_name(query_name)
    q_lower = query_name.strip().lower()

    # 1. Exact ID or Name match
    for n in nodes:
        if n["id"].lower() == q_lower or n["name"].lower() == q_lower:
            return n

    # 2. Normalized match
    for n in nodes:
        if _normalize_name(n["name"]) == q_norm:
            return n

    # 3. Substring match
    for n in nodes:
        if q_lower in n["name"].lower() or n["name"].lower() in q_lower:
            return n

    # 4. Fallback to first node
    return nodes[0]

def validate_and_sort_prerequisites_dag(
    graph: Any, 
    target_node_id: Any
) -> Any:
    """
    Traverses the directed prerequisite graph with strict cycle detection and breaking.
    Prerequisite edge: Source (Prerequisite) -> Target (Dependent).
    Detects and safely breaks cycles, and performs topological sort using Kahn's algorithm.
    """
    if isinstance(graph, list):
        concepts = graph
        prereqs = target_node_id or {}
        nodes = list(concepts)
        in_degrees = {c: 0 for c in nodes}
        adj = {c: [] for c in nodes}
        for tgt, parents in prereqs.items():
            for p in parents:
                if p in adj and tgt in in_degrees:
                    adj[p].append(tgt)
                    in_degrees[tgt] += 1
        zero_in = [c for c in nodes if in_degrees[c] == 0]
        topo = []
        while zero_in:
            curr = zero_in.pop(0)
            topo.append(curr)
            for ch in adj.get(curr, []):
                in_degrees[ch] -= 1
                if in_degrees[ch] == 0:
                    zero_in.append(ch)
        had_cycle = len(topo) < len(nodes)
        for c in nodes:
            if c not in topo:
                topo.append(c)
        return topo, had_cycle

    nodes = {n["id"]: n for n in graph.get("nodes", [])}
    edges = [e for e in graph.get("edges", []) if e.get("relationship_type") == "prerequisite"]


    # Incoming edges: child_id -> [parent prerequisite IDs]
    prereq_of: Dict[str, List[str]] = {n_id: [] for n_id in nodes}
    dependents_of: Dict[str, List[str]] = {n_id: [] for n_id in nodes}

    # Filter out self-loops and collect initial edges
    for e in edges:
        src = e["source_concept_id"]
        tgt = e["target_concept_id"]
        if src in nodes and tgt in nodes and src != tgt:
            prereq_of[tgt].append(src)
            dependents_of[src].append(tgt)

    # 1. Collect all prerequisite ancestors via BFS, with cycle guarding
    visited_prereqs = set()
    queue = [target_node_id]
    while queue:
        curr = queue.pop(0)
        for p_id in prereq_of.get(curr, []):
            if p_id not in visited_prereqs and p_id != target_node_id:
                visited_prereqs.add(p_id)
                queue.append(p_id)

    # 2. Topological Sort with Cycle Detection (Kahn's algorithm)
    subgraph_nodes = list(visited_prereqs) + [target_node_id]
    in_degrees = {n_id: 0 for n_id in subgraph_nodes}
    adj: Dict[str, List[str]] = {n_id: [] for n_id in subgraph_nodes}

    for tgt in subgraph_nodes:
        for src in prereq_of.get(tgt, []):
            if src in in_degrees:
                adj[src].append(tgt)
                in_degrees[tgt] += 1

    topo_order = []
    zero_in = [n_id for n_id, deg in in_degrees.items() if deg == 0]

    while zero_in:
        curr = zero_in.pop(0)
        topo_order.append(curr)
        for child in adj[curr]:
            in_degrees[child] -= 1
            if in_degrees[child] == 0:
                zero_in.append(child)

    # Cycle breaking: if any nodes in subgraph were part of a cycle, append remaining safely
    for n_id in subgraph_nodes:
        if n_id not in topo_order:
            topo_order.append(n_id)

    ordered_prereqs = [nodes[n_id] for n_id in topo_order if n_id in nodes]

    # 3. Collect 1-2 forward dependent follow-up concepts
    followups = []
    for dep_id in dependents_of.get(target_node_id, []):
        if dep_id in nodes and dep_id not in visited_prereqs and dep_id != target_node_id:
            followups.append(nodes[dep_id])

    return ordered_prereqs, followups[:2]

def synthesize_measurable_objective(concept_name: str, is_prereq: bool, is_target: bool) -> str:
    """Generates an explicit, measurable pedagogical objective for a learning step."""
    if is_target:
        return f"Synthesize core theory, algorithmic mechanics, and problem-solving mastery for target concept '{concept_name}'."
    elif is_prereq:
        return f"Build and verify essential foundational principles of '{concept_name}' to unblock subsequent learning steps."
    else:
        return f"Apply advanced concepts and system design trade-offs extending '{concept_name}'."


def generate_personalized_learning_path(
    course_id: str,
    target_concept: Optional[str] = None,
    user_id: str = "demo_user",
    language: str = "en"
) -> Dict[str, Any]:
    """
    Creates an end-to-end Multimodal Adaptive Learning Path for a student based on:
    1. Innovation 2 Concept Graph (grounded prerequisite DAG with cycle validation).
    2. Innovation 4 Assessment Engine (genuine accuracy, error streaks, diagnosed misconceptions).
    3. Multimodal Unified Resource Index (matching actual uploaded PDF pages, slides, video timestamps, diagrams).
    4. Pedagogical Resource Ranking (selecting the best format for learner gap & mastery level).
    5. Target-aligned verification assessments attached to each step.
    """
    # 1. Retrieve or generate course concept graph
    graph = get_concept_graph(course_id)
    if not graph or not graph.get("nodes"):
        try:
            graph = generate_course_concept_graph(course_id, force_regenerate=False)
        except Exception:
            graph = {"nodes": [], "edges": [], "topics": [], "stats": {}}

    all_nodes = graph.get("nodes", [])
    if not all_nodes:
        return {
            "course_id": course_id,
            "target_concept": target_concept or "General Course Overview",
            "target_concept_id": None,
            "is_personalized_with_assessment": False,
            "total_steps": 0,
            "completed_steps": 0,
            "next_recommended_concept": target_concept or "None",
            "next_recommended_step_number": 1,
            "recommendation_rationale": "No concepts have been indexed for this course yet. Please upload course materials to generate an adaptive learning path.",
            "recommended_action_type": "begin_foundations",
            "steps": [],
            "active_misconceptions": [],
            "prerequisite_graph_stats": {},
            "available_target_concepts": [],
            "next_recommended_resource": None,
            "student_learning_gap_diagnosis": None,
            "diagnostic_question": None
        }

    available_concept_names = [n["name"] for n in all_nodes]

    # 2. Resolve Target Concept
    target_node = find_concept_in_graph(graph, target_concept)
    target_concept_name = target_node["name"] if target_node else all_nodes[0]["name"]
    target_concept_id = target_node["id"] if target_node else all_nodes[0]["id"]

    # 3. Identify prerequisite DAG ancestors & follow-ups with cycle breaking
    ordered_ancestors, followups = validate_and_sort_prerequisites_dag(graph, target_concept_id)

    # 4. Fetch student's genuine assessment performance, misconceptions & study progress
    perf_data = get_adaptive_concept_performance(user_id, course_id)
    active_misconceptions = get_user_misconceptions(user_id, course_id, status="active")
    user_progress_items = {p["concept_id"]: p for p in get_user_concept_progress(user_id, course_id)}

    concept_stats_map = {c["concept"].lower(): c for c in perf_data.get("concept_stats", [])}
    has_assessment_history = perf_data.get("total_attempts", 0) > 0

    misconception_by_concept = {}
    for m in active_misconceptions:
        c_k = m.get("concept_name", "").lower()
        misconception_by_concept[c_k] = m

    # 5. Build Unified Multimodal Resource Index for this Course
    course_resources = build_unified_resource_index(course_id)

    # 6. Assemble Ordered Path Nodes
    all_path_nodes = []
    for idx, n in enumerate(ordered_ancestors):
        is_target = (n["id"] == target_concept_id)
        all_path_nodes.append((n, not is_target, is_target, False))

    for idx, fn in enumerate(followups):
        all_path_nodes.append((fn, False, False, True))

    steps_list = []
    completed_steps_count = 0
    struggling_step = None
    first_unmastered_prereq = None
    all_prereqs_mastered = True

    demonstrated_gaps_count = 0
    untested_prereqs_count = 0
    verified_prereqs_count = 0

    for idx, (node, is_prereq, is_target, is_followup) in enumerate(all_path_nodes):
        step_num = idx + 1
        n_name = node["name"]
        n_id = node["id"]

        # Check performance metrics using flexible matching
        stat = _match_concept_dict(n_name, concept_stats_map)
        misc = _match_concept_dict(n_name, misconception_by_concept)
        user_prog = user_progress_items.get(n_id)

        accuracy = stat["percentage"] if stat else None
        attempts_count = stat["total"] if stat else 0
        consecutive_incorrect = stat.get("consecutive_incorrect", 0) if stat else 0

        has_active_misc = (misc is not None)
        active_misc_title = misc.get("misconception_title") if misc else None

        # Determine Learning Gap Type & Mastery Status
        if has_active_misc:
            learning_gap_type = "active_misconception"
            mastery_status = "needs_revision"
            suitable_level = "beginner"
            rec_reason = f"Active Misconception: '{active_misc_title}'. Recommended targeted visual explanation and concept practice drill."
            demonstrated_gaps_count += 1
            if is_prereq or is_target:
                all_prereqs_mastered = False
                if not struggling_step:
                    struggling_step = (step_num, n_name, "resolve_misconception", rec_reason)
        elif stat and (stat.get("status") == "Weak" or consecutive_incorrect >= 2 or (accuracy is not None and accuracy < 60.0)):
            learning_gap_type = "demonstrated_gap"
            mastery_status = "needs_revision"
            suitable_level = "beginner"
            rec_reason = f"Demonstrated Learning Gap: Recent assessment accuracy ({accuracy}% across {attempts_count} drills). Review foundational textbook material before advancing."
            demonstrated_gaps_count += 1
            if is_prereq or is_target:
                all_prereqs_mastered = False
                if not struggling_step:
                    struggling_step = (step_num, n_name, "review_prerequisite", rec_reason)
        elif stat and stat.get("status") == "Strong" and accuracy is not None and accuracy >= 75.0:
            learning_gap_type = "verified_foundation"
            mastery_status = "mastered"
            suitable_level = "advanced" if is_target or is_followup else "intermediate"
            rec_reason = f"Demonstrated Mastery: Verified by adaptive assessment ({accuracy}% accuracy across {attempts_count} drills)."
            completed_steps_count += 1
            if is_prereq:
                verified_prereqs_count += 1
        elif stat and attempts_count > 0:
            learning_gap_type = "demonstrated_gap"
            mastery_status = "in_progress"
            suitable_level = "intermediate"
            rec_reason = f"In Progress: Current accuracy {accuracy}%. Complete targeted drill to confirm mastery."
            if is_prereq:
                all_prereqs_mastered = False
                if not first_unmastered_prereq:
                    first_unmastered_prereq = (step_num, n_name, "study_target", rec_reason)
        elif user_prog and user_prog.get("status") == "studied":
            learning_gap_type = "untested"
            mastery_status = "studied"
            suitable_level = "intermediate"
            rec_reason = "Self-studied by student. Take targeted verification question to establish verified mastery."
            completed_steps_count += 1
        else:
            # Untested concept (no assessment data yet)
            learning_gap_type = "untested_prerequisite" if is_prereq else "untested"
            mastery_status = "ready"
            suitable_level = "beginner" if is_prereq else "intermediate"
            rec_reason = f"Sequential prerequisite: Study this foundation to prepare for '{target_concept_name}'."
            if is_prereq:
                untested_prereqs_count += 1
                all_prereqs_mastered = False
                if not first_unmastered_prereq:
                    first_unmastered_prereq = (step_num, n_name, "study_target", rec_reason)

        # 7. Select & Rank Best Multimodal Resource for this step
        candidate_res = find_matching_resources_for_concept(course_resources, n_name)
        recommended_res, alt_resources, selection_rationale, rank_score = select_best_multimodal_resource(
            concept_name=n_name,
            gap_type=learning_gap_type,
            mastery_percentage=accuracy,
            accuracy_score=accuracy,
            has_active_misconception=has_active_misc,
            candidate_resources=candidate_res
        )

        # 8. Find or Dynamically Generate Targeted Assessment Question for this step
        targeted_q = None
        # Check if candidate resources contained a targeted quiz
        for cr in candidate_res:
            if cr.get("resource_type") == "targeted_quiz" and cr.get("question_data"):
                targeted_q = cr.get("question_data")
                break
        
        # If no stored question found, check question bank or generate on-demand
        if not targeted_q:
            stored_qs = get_assessment_questions(course_id, topic=n_name, limit=1)
            if stored_qs:
                targeted_q = stored_qs[0]
            else:
                # Dynamically generate 1 question using existing assessment service
                try:
                    gen_pack = generate_dynamic_assessment_questions(
                        course_id=course_id,
                        topic=node.get("topic", "General"),
                        difficulty="easy" if suitable_level == "beginner" else ("hard" if suitable_level == "advanced" else "medium"),
                        num_questions=1,
                        user_id=user_id,
                        target_concept=n_name
                    )
                    if gen_pack.get("questions"):
                        targeted_q = gen_pack["questions"][0]
                except Exception as q_err:
                    print(f"[LearningPath] Question generation notice for {n_name}: {q_err}")

        # Prerequisite dependencies for this step
        prereqs_raw = node.get("prerequisites", [])
        prereq_names = [p["name"] if isinstance(p, dict) else str(p) for p in prereqs_raw] if isinstance(prereqs_raw, list) else []

        dependents_raw = node.get("dependents", [])
        dependents_names = [d["name"] if isinstance(d, dict) else str(d) for d in dependents_raw] if isinstance(dependents_raw, list) else []

        step_data = {
            "concept_id": n_id,
            "concept_name": n_name,
            "topic": node.get("topic", "General"),
            "step_number": step_num,
            "is_prerequisite": is_prereq,
            "is_target": is_target,
            "is_followup": is_followup,
            "mastery_status": mastery_status,
            "mastery_percentage": accuracy,
            "accuracy_score": accuracy,
            "assessment_attempts_count": attempts_count,
            "has_active_misconception": has_active_misc,
            "active_misconception_title": active_misc_title,
            "recommendation_reason": rec_reason,
            "description": node.get("description", f"Core educational concept in {node.get('topic', 'course')}."),
            "source_citations": node.get("sources", []),
            "prerequisites_needed": prereq_names,
            "dependents_unlocked": dependents_names,
            # Multimodal Adaptive fields
            "learning_gap_type": learning_gap_type,
            "suitable_level": suitable_level,
            "measurable_objective": synthesize_measurable_objective(n_name, is_prereq, is_target),
            "recommended_resource": recommended_res,
            "alternative_resources": alt_resources,
            "targeted_assessment": targeted_q
        }
        steps_list.append(step_data)

    # 9. Next Recommended Concept & Pedagogical Rationale Synthesis
    if struggling_step:
        rec_step_num, rec_concept, rec_action, rationale_base = struggling_step
        rationale = f"Adaptive Recommendation: Review prerequisite '{rec_concept}'. {rationale_base} Resolving this gap is necessary before advancing toward '{target_concept_name}'."
    elif first_unmastered_prereq:
        rec_step_num, rec_concept, rec_action, _ = first_unmastered_prereq
        rationale = f"Next Step: Study foundational prerequisite '{rec_concept}' to build essential background knowledge for '{target_concept_name}'."
    elif all_prereqs_mastered:
        target_step_obj = next((s for s in steps_list if s["is_target"]), None)
        if target_step_obj and target_step_obj["mastery_status"] != "mastered":
            rec_concept = target_concept_name
            rec_step_num = target_step_obj["step_number"]
            rec_action = "study_target"
            rationale = f"All prerequisite foundations verified! You are fully prepared to master target concept '{target_concept_name}'."
        elif followups:
            rec_concept = followups[0]["name"]
            rec_step_num = len(steps_list)
            rec_action = "advance_next"
            rationale = f"Mastery verified for '{target_concept_name}'! We recommend advancing to higher-order follow-up concept '{rec_concept}'."
        else:
            rec_concept = target_concept_name
            rec_step_num = len(steps_list)
            rec_action = "study_target"
            rationale = f"Mastery achieved for target concept '{target_concept_name}'."
    else:
        rec_concept = target_concept_name
        rec_step_num = 1
        rec_action = "study_target"
        rationale = f"Sequential learning pathway for '{target_concept_name}'."

    # Top Next Recommended Resource
    top_recommended_res = None
    for s in steps_list:
        if s["step_number"] == rec_step_num and s.get("recommended_resource"):
            top_recommended_res = s["recommended_resource"]
            break
    if not top_recommended_res and steps_list and steps_list[0].get("recommended_resource"):
        top_recommended_res = steps_list[0]["recommended_resource"]

    # 10. Student Learning Gap Diagnosis Object
    primary_blocker = struggling_step[1] if struggling_step else (first_unmastered_prereq[1] if first_unmastered_prereq else None)
    diag_summary = (
        f"Identified {demonstrated_gaps_count} demonstrated gap(s), {len(active_misconceptions)} active misconception(s), "
        f"and {untested_prereqs_count} untested prerequisite(s). Primary focus: '{primary_blocker or target_concept_name}'."
        if has_assessment_history else
        f"No assessment history recorded yet. Path arranged by course prerequisite DAG. Take a diagnostic drill to unlock personalized mastery diagnosis."
    )

    gap_diagnosis = {
        "has_assessment_history": has_assessment_history,
        "total_attempts": perf_data.get("total_attempts", 0),
        "active_misconceptions_count": len(active_misconceptions),
        "demonstrated_gaps_count": demonstrated_gaps_count,
        "untested_prerequisites_count": untested_prereqs_count,
        "verified_prerequisites_count": verified_prereqs_count,
        "primary_blocker_concept": primary_blocker,
        "diagnostic_summary": diag_summary
    }

    # 11. Diagnostic Question for unassessed learners
    diag_question = None
    if not has_assessment_history and steps_list:
        diag_step = steps_list[0]
        diag_question = diag_step.get("targeted_assessment")

    # Localize rationales and instructions to Tamil if requested
    if language in ["ta", "tamil"]:
        rationale = translate_text(rationale, "ta")
        if gap_diagnosis and "diagnostic_summary" in gap_diagnosis:
            gap_diagnosis["diagnostic_summary"] = translate_text(gap_diagnosis["diagnostic_summary"], "ta")
        for s in steps_list:
            if s.get("recommendation_reason"):
                s["recommendation_reason"] = translate_text(s["recommendation_reason"], "ta")
            if s.get("description"):
                s["description"] = translate_text(s["description"], "ta")
            if s.get("measurable_objective"):
                s["measurable_objective"] = translate_text(s["measurable_objective"], "ta")
            if s.get("targeted_assessment") and isinstance(s["targeted_assessment"], dict):
                ta = s["targeted_assessment"]
                if ta.get("question"):
                    ta["question"] = translate_text(ta["question"], "ta")
                if ta.get("options") and isinstance(ta["options"], list):
                    for o in ta["options"]:
                        if isinstance(o, dict) and o.get("text"):
                            o["text"] = translate_text(o["text"], "ta")
                if ta.get("explanation"):
                    ta["explanation"] = translate_text(ta["explanation"], "ta")

    return {
        "course_id": course_id,
        "target_concept": target_concept_name,
        "target_concept_id": target_concept_id,
        "is_personalized_with_assessment": has_assessment_history,
        "total_steps": len(steps_list),
        "completed_steps": completed_steps_count,
        "next_recommended_concept": rec_concept,
        "next_recommended_step_number": rec_step_num,
        "recommendation_rationale": rationale,
        "recommended_action_type": rec_action,
        "steps": steps_list,
        "active_misconceptions": active_misconceptions,
        "prerequisite_graph_stats": graph.get("stats", {}),
        "available_target_concepts": available_concept_names,
        "next_recommended_resource": top_recommended_res,
        "student_learning_gap_diagnosis": gap_diagnosis,
        "diagnostic_question": diag_question,
        "language": language
    }


def verify_learning_path_step(
    course_id: str,
    concept_id: Optional[str] = None,
    concept_name: str = "",
    question_id: str = "",
    student_answer: str = "",
    user_id: str = "demo_user",
    target_concept: Optional[str] = None,
    step_id: Optional[str] = None,
    question_type: Optional[str] = "mcq",
    question_text: Optional[str] = "",
    correct_answer: Optional[str] = "",
    options: Optional[List[Any]] = None,
    language: str = "en"
) -> Dict[str, Any]:
    """
    Verification & Feedback Loop:
    1. Evaluates student answer against real course evidence using assessment service.
    2. Records the submission in the persistent database.
    3. If correct: resolves misconceptions, records progress, updates mastery.
    4. If incorrect: diagnoses misconception hypothesis and flags for revision.
    5. Dynamically refreshes and returns the updated learning path, advancing to next step if verified.
    """
    if not concept_id:
        concept_id = step_id or (concept_name.lower().replace(" ", "_") if concept_name else "c_unknown")

    # 1. Retrieve Question Definition
    stored_questions = get_assessment_questions(course_id, limit=50)
    matched_q = next((q for q in stored_questions if q.get("id") == question_id), None)

    if not matched_q:
        # Check course unified resource index
        course_resources = build_unified_resource_index(course_id)
        for r in course_resources:
            if r.get("resource_type") == "targeted_quiz" and r.get("question_data", {}).get("id") == question_id:
                matched_q = r["question_data"]
                break

    if not matched_q:
        formatted_opts = []
        c_key = "A"
        if options:
            letters = ["A", "B", "C", "D", "E"]
            for idx, opt in enumerate(options):
                if isinstance(opt, dict):
                    formatted_opts.append(opt)
                    if correct_answer and (opt.get("text") == correct_answer or opt.get("key") == correct_answer):
                        c_key = opt.get("key", "A")
                else:
                    let = letters[idx] if idx < len(letters) else str(idx)
                    opt_str = str(opt).strip()
                    formatted_opts.append({"key": let, "text": opt_str})
                    if correct_answer and (opt_str.lower() == str(correct_answer).strip().lower() or let == str(correct_answer).upper()):
                        c_key = let
        elif correct_answer:
            c_key = str(correct_answer).strip().upper()

        if correct_answer and len(str(correct_answer).strip()) == 1:
            c_key = str(correct_answer).strip().upper()

        matched_q = {
            "id": question_id,
            "course_id": course_id,
            "concept_name": concept_name,
            "topic": concept_name,
            "question_type": question_type or "mcq",
            "question": question_text or f"Explain the core function and properties of {concept_name}.",
            "expected_answer": correct_answer or f"Core principles of {concept_name}",
            "options": formatted_opts,
            "correct_key": c_key,
            "explanation": f"Grounded principles of {concept_name} from course material.",
            "source_citation": {"filename": "Course Material", "concept": concept_name}
        }



    # 2. Evaluate Student Answer
    eval_result = evaluate_student_answer(
        question_dict=matched_q,
        student_answer=student_answer,
        user_id=user_id,
        course_id=course_id,
        language=language
    )

    is_correct = eval_result.get("is_correct", False)
    score = eval_result.get("score", 0.0)
    feedback = eval_result.get("feedback", "")
    misconception = eval_result.get("misconception")

    # 3. Record Assessment Attempt in Persistence Layer
    record_assessment_attempt({
        "user_id": user_id,
        "course_id": course_id,
        "question_id": question_id,
        "question_text": matched_q.get("question", ""),
        "topic": matched_q.get("topic", concept_name),
        "concept_name": concept_name,
        "question_type": matched_q.get("question_type", "mcq"),
        "difficulty": matched_q.get("difficulty", "medium"),
        "student_answer": student_answer,
        "is_correct": is_correct,
        "score": score,
        "evaluation_status": eval_result.get("evaluation_status", "correct" if is_correct else "incorrect"),
        "feedback": feedback,
        "misconception": misconception,
        "source_citation": matched_q.get("source_citation")
    })

    # 4. Update Mastery & Misconception State
    if is_correct:
        resolve_misconception(user_id, course_id, concept_name)
        record_user_concept_progress(
            user_id=user_id,
            course_id=course_id,
            concept_id=concept_id,
            concept_name=concept_name,
            status="studied",
            notes=f"Verified through assessment scoring {int(score * 100)}%"
        )
        updated_status = "mastered" if score >= 0.75 else "in_progress"
    else:
        if misconception:
            upsert_misconception_profile(user_id, course_id, misconception)
        updated_status = "needs_revision"

    # 5. Refresh the Personalized Learning Path with new evidence
    refreshed_path = generate_personalized_learning_path(
        course_id=course_id,
        target_concept=target_concept or concept_name,
        user_id=user_id,
        language=language
    )

    next_concept = refreshed_path.get("next_recommended_concept", concept_name)
    next_action = refreshed_path.get("recommended_action_type", "study_target")

    if is_correct:
        status_label = "verified"
        feedback_rationale = f"Great work! Understanding for '{concept_name}' has been verified with genuine assessment evidence. Path updated to recommend '{next_concept}'."
    else:
        status_label = "needs_revision"
        feedback_rationale = f"Concept '{concept_name}' flagged for revision based on assessment results. Review recommended visual explanation before re-testing."

    if language in ["ta", "tamil"]:
        feedback_rationale = translate_text(feedback_rationale, "ta")

    return {
        "status": status_label,
        "is_correct": is_correct,
        "score": score,
        "feedback": feedback,
        "concept_name": concept_name,
        "updated_accuracy_score": round(score * 100.0, 1),
        "updated_mastery_status": updated_status,
        "active_misconception": misconception,
        "next_recommended_concept": next_concept,
        "next_recommended_action": next_action,
        "feedback_rationale": feedback_rationale,
        "refreshed_learning_path": refreshed_path,
        "language": language
    }


def explain_learning_path_node(
    course_id: str,
    topic: str,
    node_label: str,
    context_excerpt: Optional[str] = None,
    language: str = "en"
) -> Dict[str, Any]:
    """
    Bridges learning path steps or diagram nodes directly to the evidence-grounded AI tutor,
    providing simplified, accessible explanations grounded in course content.
    """
    chunks = get_chunks_for_textbook(course_id)
    if not chunks:
        from services.demo_data import get_demo_textbook_data
        chunks = get_demo_textbook_data()["chunks"]

    # 1. Use existing grounded tutor
    query = f"Explain the concept or step '{node_label}' from topic '{topic}' in simple language with an analogy and its exact role."
    tutor_res = answer_textbook_query(
        chunks=chunks,
        query=query,
        language=language,
        course_id=course_id,
        enable_outside_knowledge=False
    )

    # 2. Extract explanation and top citation
    top_citation = tutor_res.get("citations", [{}])[0] if tutor_res.get("citations") else None

    # 3. Generate adaptive explanation for key terms and analogy
    adaptive_exp = generate_adaptive_explanation(
        chunks=chunks,
        topic=node_label,
        level="beginner",
        language=language
    )

    simple_exp = adaptive_exp.get("explanation") or tutor_res.get("answer", "")
    analogy = adaptive_exp.get("analogy")

    return {
        "course_id": course_id,
        "topic": topic,
        "node_label": node_label,
        "simple_explanation": simple_exp,
        "analogy": analogy,
        "grounded_evidence": tutor_res.get("answer", ""),
        "source_citation": top_citation,
        "related_concepts": [r["name"] for r in tutor_res.get("related_concepts", [])] if tutor_res.get("related_concepts") else [],
        "language": language
    }
