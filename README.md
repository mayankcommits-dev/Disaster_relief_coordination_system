# Disaster Relief Coordination System

An AI-assisted disaster relief coordination application that converts natural-language emergency reports into structured requests, calculates emergency priority using deterministic rules, and allocates limited rescue resources based on availability, capacity, and distance.

## Live Demo

**Application:**  
https://disasterreliefcoordinationsystem-2zmkjzocnkrdxvmcma7ehe.streamlit.app/

> This is a portfolio demonstration using simulated emergencies and resources. It is not intended for real emergency dispatch or medical triage.

---

## Problem Statement

During disasters such as floods, emergency teams may receive many unstructured requests while having limited rescue resources.

A coordination system needs to answer questions such as:

- What is happening?
- Where is the emergency?
- How many people are affected?
- Are people trapped or injured?
- How urgent is the situation?
- What resources are required?
- Which available resource is the best match?
- What happens when some or all required resources are unavailable?

This project demonstrates one possible software architecture for that coordination problem.

---

## How It Works

```text
Emergency Report
      |
      v
AI Request Extraction
      |
      v
Structured Emergency Data
      |
      v
Deterministic Priority Engine
      |
      v
Resource Search
      |
      v
Matching Algorithm
      |
      v
Atomic Resource Reservation
      |
      v
ASSIGNED / PARTIALLY_ASSIGNED / WAITING
      |
      v
Emergency Resolution
      |
      v
Release Resources
      |
      v
Re-evaluate Waiting Emergencies
```

---

## AI + Deterministic Design

The project deliberately does not let the LLM control the entire workflow.

### AI is used for

Converting a natural-language emergency report into structured information such as:

- emergency type
- location
- number of people
- children
- injured people
- elderly people
- trapped people
- rising water
- immediate danger
- required resources

### Deterministic code is used for

- priority calculation
- resource availability checks
- capacity validation
- distance-based resource selection
- resource reservation
- emergency status
- resource release
- waiting-emergency reassignment

This keeps operational decisions predictable while using the LLM where natural-language understanding is useful.

---

## Priority Engine

Priority is calculated using explicit rules rather than an LLM.

| Condition | Score |
|---|---:|
| People trapped | +30 |
| Immediate danger | +20 |
| Rising water | +20 |
| Injured people | +20 |
| Children involved | +10 |
| Elderly people | +10 |
| 10+ people affected | +10 |

Maximum score: **100**

Priority classification:

```text
75–100  -> CRITICAL
45–74   -> HIGH
20–44   -> MEDIUM
0–19    -> NORMAL
```

---

## Resource Matching

The simulated resource pool contains:

- rescue boats
- ambulances
- medical teams
- supply teams
- shelters

The matching algorithm checks:

```text
Required resource type
        +
Availability
        +
Capacity (where applicable)
        +
Distance
        ↓
Best suitable resource
```

Among suitable resources, the closest available resource is selected.

---

## Multi-Resource Allocation

One emergency can require multiple resources.

For example:

```text
Flood + trapped people + injury
              ↓
RESCUE_BOAT
AMBULANCE
MEDICAL_TEAM
```

The resulting emergency can become:

- **ASSIGNED** — all required resource types were allocated
- **PARTIALLY_ASSIGNED** — some required resources were allocated
- **WAITING_FOR_RESOURCE** — no required resource could currently be allocated

---

## Automatic Reassignment

When an emergency is resolved:

1. its resources are released;
2. resources become available again;
3. waiting and partially assigned emergencies are reconsidered;
4. higher-priority waiting emergencies are processed first;
5. newly available resources can be assigned automatically.

This models changing resource availability rather than treating each request independently.

---

## Atomic Resource Reservation

Resource reservation is performed conditionally in SQLite.

Conceptually:

```sql
UPDATE resources
SET status = 'BUSY',
    assigned_to = ?
WHERE id = ?
  AND status = 'AVAILABLE';
```

The update succeeds only if the resource is still available.

This prevents two assignment attempts from successfully reserving the same resource through the same database state transition.

---

## AI Failure Fallback

The LLM is not a required single point of failure.

```text
Emergency Report
       |
       v
Try AI Extraction
       |
   +---+---+
   |       |
Success   Failure
   |       |
   |       v
   |   Deterministic
   |   Fallback Parser
   |       |
   +---+---+
       |
       v
Priority + Matching + Assignment
```

If AI extraction fails, a conservative rule-based parser uses keywords and regular expressions to extract basic emergency information and allows the workflow to continue.

The fallback was manually verified by intentionally using an invalid model during testing.

---

## Live Processing Trace

The Streamlit interface exposes major processing steps so the application is not simply an input box followed by a final answer.

The UI shows:

- request creation
- AI extraction
- fallback activation when required
- priority rules triggered
- calculated score
- resource searches
- selected resources
- assignment state
- final workflow status

The application displays operational decisions and summaries rather than hidden model chain-of-thought.

---

## Persistence

SQLite is used for persistent backend state including:

- emergencies
- resources
- assignments

Resource state is persisted so resources can transition between:

```text
AVAILABLE -> BUSY -> AVAILABLE
```

The current portfolio implementation still uses Streamlit session state for parts of the UI representation, so it should not be interpreted as a fully distributed or restart-safe production architecture.

---

## FastAPI

The project also exposes a lightweight FastAPI interface for backend access.

Example endpoints include:

```text
GET   /
GET   /health
GET   /emergencies
PATCH /emergencies/{emergency_id}/status
```

This demonstrates separation between the interactive Streamlit interface and an API surface that could be consumed by other clients.

---

## Testing

The project includes automated tests for major backend behavior.

**13/13 tests passing**

Coverage includes:

- FastAPI health/root endpoints
- emergency API access
- emergency status updates
- deterministic priority calculation
- resource matching
- capacity filtering
- unavailable-resource handling
- full multi-resource matching
- partial allocation scenarios
- waiting/no-resource scenarios
- resource release and reassignment behavior

Run the tests with:

```bash
py -m pytest -q
```

---

## Tech Stack

- **Python**
- **Streamlit**
- **Groq API / LLM**
- **Pydantic**
- **SQLite**
- **FastAPI**
- **Pytest**
- **Pandas**
- **Git / GitHub**
- **Streamlit Community Cloud**

---

## Project Structure

```text
Disaster_relief_coordination_system/
|
|-- app.py
|-- requirements.txt
|-- README.md
|-- .env.example
|-- .gitignore
|
|-- backend/
|   |-- __init__.py
|   |-- api.py
|   |-- database.py
|   |
|   `-- services/
|       |-- __init__.py
|       |-- priority.py
|       `-- matching.py
|
`-- tests/
    |-- test_system.py
    |-- test_priority.py
    |-- test_matching.py
    `-- test_workflows.py
```

---

## Running Locally

### 1. Install dependencies

```bash
py -m pip install -r requirements.txt
```

### 2. Configure the API key

Create a `.env` file:

```text
GROQ_API_KEY=your_groq_api_key
```

Do not commit `.env` to GitHub.

### 3. Run the application

```bash
py -m streamlit run app.py
```

### 4. Run tests

```bash
py -m pytest -q
```

---

## Current Limitations

This is a portfolio system, not a production disaster-response platform.

Current limitations include:

- simulated emergency resources
- simplified deterministic priority rules
- basic keyword/regex AI fallback
- local SQLite persistence
- some UI state maintained in Streamlit session state
- no real emergency-service integrations
- no distributed worker/queue architecture
- no real geospatial routing
- no authentication or authorization layer

A larger production architecture could introduce API servers, queues, background workers, geospatial services, distributed databases, notifications, authentication, and stronger concurrency controls.

---

## Key Engineering Idea

The core design principle of the project is:

> Use AI where natural-language understanding provides value, and use deterministic software where predictable operational behavior matters.

The project therefore combines LLM-based request understanding with conventional Python services, explicit algorithms, database state management, failure handling, APIs, and automated testing.