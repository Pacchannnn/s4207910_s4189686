"""Idempotently add supplied personas/team and SQL views to the project copy only."""
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
PERSONAS = [
    (1, "Dr Amara Okonkwo",
     "Regional public health analyst, aged 35 to 45, based in Sub-Saharan Africa.",
     "She wants to identify countries falling behind in controlling preventable infectious diseases.",
     "Raw case counts are difficult to compare because populations differ."),
    (2, "Liem Tran",
     "Second-year public health student, aged 18 to 24, living in Melbourne.",
     "He needs figures concerning disease burden and economic conditions.",
     "Missing years, sources and population denominators frustrate him."),
    (3, "Sofia Mascherano", "Health journalist, aged 40, based in Rome.",
     "She wants to verify measles-resurgence claims and distinguish large raw totals from unusually high infection rates.",
     "Distinguishing large raw totals from unusually high infection rates."),
    (4, "Grace Lil'", "Parent and community volunteer, aged 40, living in regional Victoria.",
     "She wants understandable comparisons.",
     "She finds terms such as antigen and vaccination coverage difficult.")
]

def main():
    path = ROOT / "database/immunisation.db"
    if not path.is_file():
        raise SystemExit("The project copy database/immunisation.db is missing.")
    connection = sqlite3.connect(path)
    try:
        connection.executescript((ROOT / "database/extensions.sql").read_text(encoding="utf-8"))
        connection.executemany(
            "INSERT OR IGNORE INTO Persona(persona_id,name,profile,goal,difficulty) VALUES (?,?,?,?,?)",
            PERSONAS)
        connection.executemany(
            "INSERT OR IGNORE INTO TeamMember(student_id,name) VALUES (?,?)",
            [("s4207910","Le Chi Bach"),("s4189686","Nguyen Tran Ba Trong")])
        connection.commit()
        print("Project database prepared. Original tables and records preserved.")
    finally:
        connection.close()

if __name__ == "__main__":
    main()

