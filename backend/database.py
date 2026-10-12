import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "disaster_relief.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emergencies (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            original_message TEXT NOT NULL,
            emergency_type TEXT,
            location TEXT,
            people_affected INTEGER,
            priority_score INTEGER,
            priority TEXT,
            status TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emergency_id TEXT NOT NULL,
            resource_id TEXT NOT NULL,
            resource_name TEXT NOT NULL,
            status TEXT NOT NULL
        )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS resources (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        capacity INTEGER NOT NULL,
        distance_km REAL NOT NULL,
        status TEXT NOT NULL,
        assigned_to TEXT
        )
    """)

    conn.commit()
    conn.close()


def save_emergency(emergency):
    conn = get_connection()
    cursor = conn.cursor()

    analysis = emergency["analysis"]

    cursor.execute("""
        INSERT OR REPLACE INTO emergencies (
            id,
            created_at,
            original_message,
            emergency_type,
            location,
            people_affected,
            priority_score,
            priority,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        emergency["id"],
        emergency["created_at"],
        emergency["original_message"],
        analysis["emergency_type"],
        analysis["location"],
        analysis["people_affected"],
        emergency["priority_score"],
        emergency["priority"],
        emergency["status"],
    ))

    conn.commit()
    conn.close()


def save_assignment(emergency_id, resource):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO assignments (
            emergency_id,
            resource_id,
            resource_name,
            status
        )
        VALUES (?, ?, ?, ?)
    """, (
        emergency_id,
        resource["id"],
        resource["name"],
        "IN_PROGRESS",
    ))

    conn.commit()
    conn.close()


def get_emergencies():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM emergencies
        ORDER BY created_at DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def update_emergency_status(emergency_id, status):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE emergencies
        SET status = ?
        WHERE id = ?
    """, (status, emergency_id))

    conn.commit()
    conn.close()


def initialize_resources(default_resources):
    conn = get_connection()
    cursor = conn.cursor()

    for resource in default_resources:
        cursor.execute("""
            INSERT OR IGNORE INTO resources (
                id,
                name,
                type,
                capacity,
                distance_km,
                status,
                assigned_to
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            resource["id"],
            resource["name"],
            resource["type"],
            resource["capacity"],
            resource["distance_km"],
            resource["status"],
            resource.get("assigned_to"),
        ))

    conn.commit()
    conn.close()


def get_resources():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM resources
        ORDER BY id
    """)

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def reserve_resource_db(resource_id, emergency_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE resources
        SET status = 'BUSY',
        assigned_to = ?
        WHERE id = ?
        AND status = 'AVAILABLE'
    """, (
        emergency_id,
        resource_id,
    ))

    success = cursor.rowcount == 1

    conn.commit()
    conn.close()

    return success


def release_resource_db(resource_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE resources
        SET status = 'AVAILABLE',
        assigned_to = NULL
        WHERE id = ?
    """, (resource_id,))

    conn.commit()
    conn.close()

def update_assignment_status(emergency_id, status):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE assignments
        SET status = ?
        WHERE emergency_id = ?
    """, (
        status,
        emergency_id,
    ))

    conn.commit()
    conn.close()


def get_waiting_emergencies():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM emergencies
        WHERE status IN (
        'WAITING_FOR_RESOURCE',
        'PARTIALLY_ASSIGNED')
        ORDER BY priority_score DESC, created_at ASC
    """)

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]

def reset_demo_database(default_resources):
    conn = get_connection()
    cursor = conn.cursor()

    # Remove old demo data
    cursor.execute("DELETE FROM assignments")
    cursor.execute("DELETE FROM emergencies")
    cursor.execute("DELETE FROM resources")

    # Restore default resources
    for resource in default_resources:
        cursor.execute(
            """
            INSERT INTO resources (
                id,
                name,
                type,
                capacity,
                distance_km,
                status,
                assigned_to
            )
            VALUES (?, ?, ?, ?, ?, ?, NULL)
            """,
            (
                resource["id"],
                resource["name"],
                resource["type"],
                resource["capacity"],
                resource["distance_km"],
                resource["status"],
            ),
        )

    conn.commit()
    conn.close()
    
initialize_database()