import os
import json
import re
import time
import uuid
from datetime import datetime
from backend.services.priority import calculate_priority_score
from backend.services.matching import select_best_resource
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from groq import Groq
from pydantic import BaseModel, Field
from backend.database import (

    save_emergency,

    save_assignment,

    update_emergency_status,

    initialize_resources,

    get_resources,

    reserve_resource_db,

    release_resource_db,

    update_assignment_status,

    get_waiting_emergencies,

    reset_demo_database,

)

# CONFIG

load_dotenv()

st.set_page_config(
    page_title="Disaster Relief Coordination System",
    page_icon="🚨",
    layout="wide",

)



MODEL = "openai/gpt-oss-120b"

# ============================================================



# DATA MODELS



# ============================================================

class EmergencyAnalysis(BaseModel):



    emergency_type: str = Field(



        description="Main category such as FLOOD_RESCUE, MEDICAL, SUPPLIES, SHELTER"



    )



    people_affected: int = 1



    children: int = 0



    injured_people: int = 0



    elderly_people: int = 0







    location: str = "Unknown"







    immediate_danger: bool = False



    rising_water: bool = False



    people_trapped: bool = False







    required_resources: list[str] = Field(default_factory=list)







    summary: str



    ai_reason: str


# ============================================================



# INITIAL DEMO RESOURCES



# ============================================================







DEFAULT_RESOURCES = [



    {



        "id": "BOAT-01",



        "name": "Rescue Boat #1",



        "type": "RESCUE_BOAT",



        "capacity": 8,



        "distance_km": 8.4,



        "status": "AVAILABLE",



    },



    {



        "id": "BOAT-02",



        "name": "Rescue Boat #2",



        "type": "RESCUE_BOAT",



        "capacity": 6,



        "distance_km": 2.3,



        "status": "AVAILABLE",



    },



    {



        "id": "BOAT-03",



        "name": "Rescue Boat #3",



        "type": "RESCUE_BOAT",



        "capacity": 10,



        "distance_km": 1.8,



        "status": "BUSY",



    },



    {



        "id": "AMB-01",



        "name": "Ambulance #1",



        "type": "AMBULANCE",



        "capacity": 4,



        "distance_km": 3.1,



        "status": "AVAILABLE",



    },



    {



        "id": "MED-01",



        "name": "Medical Team #1",



        "type": "MEDICAL_TEAM",



        "capacity": 5,



        "distance_km": 4.0,



        "status": "AVAILABLE",



    },



    {



        "id": "SUP-01",



        "name": "Supply Team #1",



        "type": "SUPPLY_TEAM",



        "capacity": 100,



        "distance_km": 5.2,



        "status": "AVAILABLE",



    },



    {



        "id": "SHELTER-01",



        "name": "Community Shelter #1",



        "type": "SHELTER",



        "capacity": 50,



        "distance_km": 6.0,



        "status": "AVAILABLE",



    },



]







initialize_resources(DEFAULT_RESOURCES)







# ============================================================



# SESSION STATE



# ============================================================







if "resources" not in st.session_state:



    st.session_state.resources = get_resources()







if "emergencies" not in st.session_state:



    st.session_state.emergencies = []







if "assignments" not in st.session_state:



    st.session_state.assignments = []







if "last_trace" not in st.session_state:



    st.session_state.last_trace = []











# ============================================================



# HELPERS



# ============================================================







def now():



    return datetime.now().strftime("%H:%M:%S")











def add_trace(stage, component, message, kind="INFO"):



    event = {



        "time": now(),



        "stage": stage,



        "component": component,



        "message": message,



        "kind": kind,



    }







    st.session_state.last_trace.append(event)











def get_client():



    key = os.getenv("GROQ_API_KEY")







    if not key:



        return None







    return Groq(api_key=key)











# ============================================================



# AI REQUEST AGENT



# ============================================================

def analyze_emergency_fallback(message: str) -> EmergencyAnalysis:
    """Conservative deterministic backup used only when AI extraction fails."""

    text = message.lower()

    def has(*terms):
        return any(term in text for term in terms)

    # Try to identify the number of people.
    number_match = re.search(r"\b(\d+)\b", text)
    people = int(number_match.group(1)) if number_match else 1

    # Try to identify children.
    child_match = re.search(
        r"\b(\d+)\s+(?:children|kids|child)\b",
        text,
    )

    if child_match:
        children = int(child_match.group(1))
    elif has("child", "children", "kid", "kids"):
        children = 1
    else:
        children = 0

    # Basic emergency indicators.
    injured = 1 if has(
        "injured",
        "injury",
        "hurt",
        "wounded",
        "medical help",
        "medical assistance",
    ) else 0

    elderly = 1 if has(
        "elderly",
        "senior citizen",
        "old man",
        "old woman",
    ) else 0

    trapped = has(
        "trapped",
        "stuck",
        "stranded",
        "roof",
    )

    rising = has(
        "water is rising",
        "rising water",
        "water rising",
    )

    danger = (
        trapped
        or rising
        or has(
            "immediate danger",
            "urgent",
            "serious",
            "critical",
        )
    )

    flood = has(
        "flood",
        "flooded",
        "water",
        "roof",
        "boat",
    )

    supplies = has(
        "food",
        "drinking water",
        "supplies",
        "supply",
    )

    shelter = has(
        "shelter",
        "homeless",
        "evacuated",
        "evacuation",
    )

    # Determine required resources.
    required = []

    if flood and (trapped or has("boat", "rescue")):
        required.append("RESCUE_BOAT")

    if injured:
        required.extend([
            "AMBULANCE",
            "MEDICAL_TEAM",
        ])

    if supplies:
        required.append("SUPPLY_TEAM")

    if shelter:
        required.append("SHELTER")

    # Remove duplicates while preserving order.
    required = list(dict.fromkeys(required))

    # Determine emergency category.
    if flood:
        emergency_type = "FLOOD_RESCUE"
    elif injured:
        emergency_type = "MEDICAL"
    elif supplies:
        emergency_type = "SUPPLIES"
    elif shelter:
        emergency_type = "SHELTER"
    else:
        emergency_type = "OTHER"

    # Basic location extraction.
    location = "Unknown"

    location_match = re.search(
        r"\bnear\s+([^.!?]+)",
        message,
        flags=re.IGNORECASE,
    )

    if location_match:
        location = location_match.group(1).strip()

    return EmergencyAnalysis(
        emergency_type=emergency_type,
        people_affected=people,
        children=children,
        injured_people=injured,
        elderly_people=elderly,
        location=location,
        immediate_danger=danger,
        rising_water=rising,
        people_trapped=trapped,
        required_resources=required,
        summary=(
            "Emergency details extracted using "
            "deterministic fallback rules."
        ),
        ai_reason=(
            "AI extraction was unavailable, so basic "
            "keyword and rule-based extraction was used."
        ),
    )

def analyze_emergency_with_ai(message: str) -> EmergencyAnalysis:







    client = get_client()







    if client is None:



        raise RuntimeError(



            "GROQ_API_KEY is missing. Add it to your .env file."



        )







    system_prompt = """



You are an emergency request extraction component for a DEMO disaster



relief coordination application.







Your job is ONLY to convert the user's natural-language report into



structured operational information.







Do not make final dispatch decisions.







Return ONLY valid JSON with exactly these fields:







{



  "emergency_type": "FLOOD_RESCUE | MEDICAL | SUPPLIES | SHELTER | OTHER",



  "people_affected": integer,



  "children": integer,



  "injured_people": integer,



  "elderly_people": integer,



  "location": "string",



  "immediate_danger": boolean,



  "rising_water": boolean,



  "people_trapped": boolean,



  "required_resources": ["RESCUE_BOAT", "AMBULANCE", "MEDICAL_TEAM", "SUPPLY_TEAM", "SHELTER"],



  "summary": "short factual summary",



  "ai_reason": "brief explanation of what information in the report led to the extraction"



}







Rules:



*\\-* Do not invent specific people counts if absent. Use 1 as people_affected when unknown.



*\\-* Use 0 for child/injured/elderly counts when not mentioned.



*\\-* Only include resources that appear reasonably necessary from the report.



*\\-* If someone is trapped by flood water, RESCUE_BOAT may be required.



*\\-* If injury or urgent medical need exists, include MEDICAL_TEAM and/or AMBULANCE.



*\\-* Keep ai_reason short.



"""







    response = client.chat.completions.create(



        model=MODEL,



        temperature=0,



        response_format={"type": "json_object"},



        messages=[



            {



                "role": "system",



                "content": system_prompt,



            },



            {



                "role": "user",



                "content": message,



            },



        ],



    )







    raw = response.choices[0].message.content







    data = json.loads(raw)







    analysis = EmergencyAnalysis(**data)







    add_trace(



        "1",



        "AI Request Agent",



        f"Classified request as {analysis.emergency_type}.",



        "SUCCESS",



    )







    add_trace(



        "1",



        "AI Request Agent",



        f"Extracted location: {analysis.location}.",



        "SUCCESS",



    )







    add_trace(



        "1",



        "AI Request Agent",



        f"Required resources identified: {', '.join(analysis.required_resources) or 'None'}.",



        "SUCCESS",



    )







    return analysis











# ============================================================



# DETERMINISTIC PRIORITY ENGINE



# ============================================================







def calculate_priority(analysis):



    score, priority, reasons = calculate_priority_score(analysis)







    for reason, points in reasons:



        add_trace(



            "2",



            "Priority",



            f"{reason}  →  +{points}",



        )







    add_trace(



        "2",



        "Priority",



        f"Priority Score: {score}/100  →  {priority}",



        "SUCCESS",



    )







    return score, priority, reasons











# ============================================================



# RESOURCE DATABASE QUERY



# ============================================================











# ============================================================



# MATCHING ALGORITHM



# ============================================================







def choose_best_resource(required_type, people):



    add_trace(



        "3",



        "Resource Search",



        f"Searching for available {required_type} resources.",



    )







    resource = select_best_resource(



        st.session_state.resources,



        required_type,



        people,



    )







    if resource is None:



        add_trace(



            "3",



            "Resource Search",



            f"No suitable {required_type} currently available.",



            "WARNING",



        )



        return None







    add_trace(



        "3",



        "Resource Search",



        (



            f"Selected {resource['name']} — "



            f"capacity {resource['capacity']}, "



            f"{resource['distance_km']} km away."



        ),



        "SUCCESS",



    )







    return resource







# ============================================================



# ASSIGNMENT / STATE UPDATE



# ============================================================







def reserve_resource(resource, emergency_id):







    success = reserve_resource_db(



        resource["id"],



        emergency_id,



    )







    if not success:



        add_trace(



            "4",



            "Assignment",



            f"{resource['name']} is no longer available.",



            "WARNING",



        )



        return False







    st.session_state.resources = get_resources()







    add_trace(



        "4",



        "Assignment",



        f"{resource['name']} assigned to {emergency_id}.",



        "SUCCESS",



    )







    return True







# ============================================================



# FULL PIPELINE



# ============================================================


def process_emergency(message):
    st.session_state.last_trace = []

    emergency_id = f"EM-{uuid.uuid4().hex[:6].upper()}"

    add_trace(
        "0",
        "API/Input Layer",
        f"Created emergency request {emergency_id}.",
        "SUCCESS",
    )

    # STEP 1: AI extraction with deterministic fallback
    try:
        analysis = analyze_emergency_with_ai(message)

    except Exception as exc:
        add_trace(
            "1",
            "AI Request Agent",
            (
                f"AI extraction unavailable "
                f"({type(exc).__name__}). "
                "Switching to deterministic fallback."
            ),
            "WARNING",
        )

        analysis = analyze_emergency_fallback(message)

        add_trace(
            "1",
            "Fallback Parser",
            f"Classified request as {analysis.emergency_type}.",
            "SUCCESS",
        )

        add_trace(
            "1",
            "Fallback Parser",
            (
                "Required resources identified: "
                f"{', '.join(analysis.required_resources) or 'None'}."
            ),
            "SUCCESS",
        )

    # STEP 2: deterministic priority
    score, priority, priority_reasons = calculate_priority(analysis)

    # STEP 3 + 4: resource lookup and matching
    selected_resources = []

    for required_type in analysis.required_resources:
        selected = choose_best_resource(
            required_type,
            analysis.people_affected,
        )

        if selected:
            selected_resources.append(selected)

    # STEP 5: reserve resources
    successful_assignments = []

    for resource in selected_resources:
        success = reserve_resource(
            resource,
            emergency_id,
        )

        if success:
            successful_assignments.append(
                dict(resource)
            )

    # Determine whether all, some or none of the
    # required resource types were successfully assigned.
    assigned_types = {
        resource["type"]
        for resource in successful_assignments
    }

    required_types = set(
        analysis.required_resources
    )

    if (
        required_types
        and assigned_types >= required_types
    ):
        status = "ASSIGNED"

    elif successful_assignments:
        status = "PARTIALLY_ASSIGNED"

    else:
        status = "WAITING_FOR_RESOURCE"

    emergency = {
        "id": emergency_id,
        "created_at": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "original_message": message,
        "analysis": analysis.model_dump(),
        "priority_score": score,
        "priority": priority,
        "priority_reasons": priority_reasons,
        "resources": successful_assignments,
        "status": status,
    }

    # Store emergency in session and database.
    st.session_state.emergencies.append(
        emergency
    )

    save_emergency(emergency)

    # Store successful assignments.
    for resource in successful_assignments:
        st.session_state.assignments.append(
            {
                "emergency_id": emergency_id,
                "resource_id": resource["id"],
                "resource_name": resource["name"],
                "status": "IN_PROGRESS",
            }
        )

        save_assignment(
            emergency_id,
            resource,
        )

    add_trace(
        "6",
        "Workflow",
        (
            "Emergency workflow completed "
            f"with status {status}."
        ),
        "SUCCESS",
    )

    return emergency


def reassign_waiting_emergencies():



    waiting_emergencies = get_waiting_emergencies()



    if not waiting_emergencies:

        return



    for waiting in waiting_emergencies:



        emergency_id = waiting["id"]

        people = waiting["people_affected"]



        emergency_data = next(

            (

                emergency

                for emergency in st.session_state.emergencies

                if emergency["id"] == emergency_id

            ),

            None,

        )



        if emergency_data is None:

            continue



        required_resources = emergency_data["analysis"]["required_resources"]

        st.session_state.resources = get_resources()



        already_assigned_types = set()



        for assignment in st.session_state.assignments:

            if (

                assignment["emergency_id"] == emergency_id

                and assignment["status"] == "IN_PROGRESS"

            ):

                resource = next(

                    (

                        r

                        for r in st.session_state.resources

                        if r["id"] == assignment["resource_id"]

                    ),

                    None,

                )



                if resource is not None:

                    already_assigned_types.add(resource["type"])



        newly_assigned = []



        for required_type in required_resources:



            if required_type in already_assigned_types:

                continue



            st.session_state.resources = get_resources()



            resource = select_best_resource(

                st.session_state.resources,

                required_type,

                people,

            )



            if resource is None:

                continue



            success = reserve_resource_db(

                resource["id"],

                emergency_id,

            )



            if not success:

                continue



            save_assignment(

                emergency_id,

                resource,

            )



            st.session_state.assignments.append(

                {

                    "emergency_id": emergency_id,

                    "resource_id": resource["id"],

                    "resource_name": resource["name"],

                    "status": "IN_PROGRESS",

                }

            )



            newly_assigned.append(dict(resource))

            already_assigned_types.add(required_type)



        if newly_assigned:

            emergency_data["resources"].extend(newly_assigned)



        required_types = set(required_resources)



        if required_types and already_assigned_types >= required_types:

            new_status = "ASSIGNED"

        elif already_assigned_types:

            new_status = "PARTIALLY_ASSIGNED"

        else:

            new_status = "WAITING_FOR_RESOURCE"



        emergency_data["status"] = new_status



        update_emergency_status(

            emergency_id,

            new_status,

        )



    st.session_state.resources = get_resources()





# ============================================================



# RESOLUTION



# ============================================================







def resolve_emergency(emergency_id):







    # Mark emergency resolved



    for emergency in st.session_state.emergencies:







        if emergency["id"] == emergency_id:







            emergency["status"] = "RESOLVED"







            update_emergency_status(



                emergency_id,



                "RESOLVED",



            )







    # Release resources



    for resource in st.session_state.resources:







        if resource.get("assigned_to") == emergency_id:







            release_resource_db(



                resource["id"]



            )







    # Complete assignments



    for assignment in st.session_state.assignments:







        if assignment["emergency_id"] == emergency_id:



            assignment["status"] = "COMPLETED"







    update_assignment_status(



        emergency_id,



        "COMPLETED",



    )







    # Reload available resources



    st.session_state.resources = get_resources()







    # NEW:



    # Automatically reconsider waiting emergencies



    reassign_waiting_emergencies()







    # Reload final state



    st.session_state.resources = get_resources()



# ============================================================



# UI HELPERS



# ============================================================







def priority_icon(priority):







    return {



        "CRITICAL": "🚨",



        "HIGH": "⚠️",



        "MEDIUM": "🟡",



        "NORMAL": "🟢",



    }.get(priority, "⚪")











def render_trace():







    if not st.session_state.last_trace:



        st.info(



            "Submit an emergency request to see the AI and backend "



            "processing steps here."



        )



        return







    stage_names = {



        "0": "Request Received",



        "1": "AI Understanding",



        "2": "Priority Calculation",



        "3": "Resource Search",



        "4": "Resource Matching",



        "5": "Assignment",



        "6": "Workflow Complete",



    }







    current_stage = None







    for event in st.session_state.last_trace:







        if event["stage"] != current_stage:







            current_stage = event["stage"]







            st.markdown("---")







            st.subheader(



                f"Step {current_stage} — "



                f"{stage_names.get(current_stage, current_stage)}"



            )







        icon = {



            "SUCCESS": "✅",



            "WARNING": "⚠️",



            "ERROR": "❌",



            "INFO": "⚙️",



        }.get(event["kind"], "•")







        st.markdown(



            f"{icon} **{event['component']}** — {event['message']}"



        )











# ============================================================



# HEADER



# ============================================================







st.title("🚨 Disaster Relief Coordination System")







st.caption(



    "AI-assisted emergency request understanding, deterministic "



    "priority calculation and limited-resource matching."



)







st.warning(



    "Portfolio demonstration only. This system uses simulated resources "



    "and simplified prioritization rules and must not be used for real "



    "emergency dispatch or medical triage."



)











# ============================================================



# SIDEBAR



# ============================================================







with st.sidebar:







    st.header("System Status")







    available = len(



        [



            r



            for r in st.session_state.resources



            if r["status"] == "AVAILABLE"



        ]



    )



    busy = len(



        [



            r



            for r in st.session_state.resources



            if r["status"] == "BUSY"



        ]



    )







    unresolved = len(



        [



            e



            for e in st.session_state.emergencies



                if e["status"] != "RESOLVED"

        ]

    )



    st.metric("Available Resources", available)

    st.metric("Busy Resources", busy)

    st.metric("Active Emergencies", unresolved)



    st.divider()



    if st.button("Reset Demo Data"):



        reset_demo_database(DEFAULT_RESOURCES)



        st.session_state.resources = get_resources()

        st.session_state.emergencies = []

        st.session_state.assignments = []

        st.session_state.last_trace = []



        st.rerun()





# ============================================================



# TABS



# ============================================================







tab1, tab2, tab3, tab4 = st.tabs(



    [



        "🚨 Report Emergency",



        "⚙️ Live Processing",



        "🗺️ Operations",



        "🏗️ How It Works",



    ]



)











# ============================================================



# TAB 1 — REPORT



# ============================================================







with tab1:







    st.header("Report an Emergency")







    st.write(



        "Describe the situation naturally. The AI will extract the "



        "important operational information."



    )







    example = (



        "We are a family of 5 stuck on the roof near ABC School. "



        "Two children are with us. Water is rising quickly and "



        "my father is injured."



    )







    emergency_text = st.text_area(



        "Emergency description",



        value=example,



        height=150,



    )







    if st.button(



        "Process Emergency",



        type="primary",



        use_container_width=True,



    ):







        if not emergency_text.strip():







            st.error("Enter an emergency description.")







        else:







            try:







                with st.spinner(



                    "Processing emergency through AI and backend pipeline..."



                ):







                    emergency = process_emergency(



                        emergency_text.strip()



                    )







                    time.sleep(0.5)







                st.success(



                    f"{emergency['id']} processed successfully."



                )







                analysis = emergency["analysis"]







                st.subheader("AI Understanding")







                c1, c2, c3, c4 = st.columns(4)







                c1.metric(



                    "Emergency",



                    analysis["emergency_type"],



                )







                c2.metric(



                    "People",



                    analysis["people_affected"],



                )







                c3.metric(



                    "Priority",



                    emergency["priority"],



                )







                c4.metric(



                    "Score",



                    f"{emergency['priority_score']}/100",



                )







                st.write(



                    "**AI Summary:**",



                    analysis["summary"],



                )







                st.write(



                    "**AI Explanation:**",



                    analysis["ai_reason"],



                )







                st.write(



                    "**Required Resources:**",



                    ", ".join(



                        analysis["required_resources"]



                    )



                    or "None",



                )







                st.info(



                    "Open the **Live Processing** tab to see exactly "



                    "what the AI, priority engine, resource database "



                    "and matching algorithm did."



                )







            except Exception as exc:







                st.exception(exc)











# ============================================================



# TAB 2 — LIVE PROCESSING



# ============================================================







with tab2:







    st.header("Live Processing Trace")







    st.write(



        "This view exposes the application's operational processing "



        "steps. It shows extracted information, deterministic rules, "



        "resource queries and state changes rather than hidden model "



        "chain-of-thought."



    )







    render_trace()











# ============================================================



# TAB 3 — OPERATIONS



# ============================================================







with tab3:







    st.header("Emergency Operations Dashboard")







    # ----------------------------



    # ACTIVE EMERGENCIES



    # ----------------------------







    st.subheader("Emergency Queue")







    if not st.session_state.emergencies:







        st.info("No emergency requests have been submitted.")







    else:







        sorted_emergencies = sorted(



            st.session_state.emergencies,



            key=lambda x: (



                x["status"] == "RESOLVED",



                -x["priority_score"],



            ),



        )







        for emergency in sorted_emergencies:







            icon = priority_icon(



                emergency["priority"]



            )







            title = (



                f"{icon} {emergency['id']} — "



                f"{emergency['priority']} — "



                f"{emergency['status']}"



            )







            with st.expander(title):







                analysis = emergency["analysis"]







                st.write(



                    "**Request:**",



                    emergency["original_message"],



                )







                st.write(



                    "**Location:**",



                    analysis["location"],



                )







                st.write(



                    "**AI Summary:**",



                    analysis["summary"],



                )







                st.write(



                    "**Priority Score:**",



                    emergency["priority_score"],



                )







                if emergency["priority_reasons"]:







                    st.write("**Priority calculation:**")







                    for reason, points in emergency[



                        "priority_reasons"



                    ]:







                        st.write(



                            f"- {reason}: +{points}"



                        )







                if emergency["resources"]:







                    st.write("**Assigned Resources:**")







                    for resource in emergency["resources"]:







                        st.write(



                            f"- {resource['name']} "



                            f"({resource['distance_km']} km)"



                        )







                else:







                    st.warning(



                        "No suitable resource currently available."



                    )







                if emergency["status"] != "RESOLVED":







                    if st.button(



                        "Mark Resolved",



                        key=f"resolve_{emergency['id']}",



                    ):







                        resolve_emergency(



                            emergency["id"]



                        )







                        st.rerun()







    # ----------------------------



    # RESOURCES



    # ----------------------------







    st.divider()







    st.subheader("Resource Pool")







    resource_df = pd.DataFrame(



        st.session_state.resources



    )







    display_columns = [



        "id",



        "name",



        "type",



        "capacity",



        "distance_km",



        "status",



    ]







    st.dataframe(



        resource_df[display_columns],



        use_container_width=True,



        hide_index=True,



    )







    # ----------------------------



    # ASSIGNMENTS



    # ----------------------------







    st.divider()







    st.subheader("Assignments")







    if st.session_state.assignments:







        st.dataframe(



            pd.DataFrame(



                st.session_state.assignments



            ),



            use_container_width=True,



            hide_index=True,



        )







    else:







        st.info("No assignments yet.")











# ============================================================



# TAB 4 — HOW IT WORKS



# ============================================================







with tab4:







    st.header("How the System Works")







    st.markdown(



        """



database would require atomic reservation/locking so that two workers



cannot assign the same rescue resource.



"""



    )