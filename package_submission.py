"""
Automated Submission Packaging Utility for Project JARVIS.
Packages the mandated /src directory, assistant_execution.log, and Prelim_Project_Report.pdf
into the official ZIP archive required by Prof. Rob Malitao.
"""

import os
import sys
import zipfile
import shutil

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


def create_submission_zip(last_name1: str = "Carvajal", last_name2: str = "Sarsalijo"):
    zip_name = f"AI_PrelimExam_Group_{last_name1}_{last_name2}.zip"
    zip_path = os.path.join(PROJECT_ROOT, zip_name)

    print(f"[PACKAGING]: Building submission archive '{zip_name}'...")

    required_items = [
        ("src", True),
        ("assistant_execution.log", False),
        ("Prelim_Project_Report.pdf", False),
        ("requirements.txt", False),
        ("README.md", False)
    ]

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for item, is_dir in required_items:
            item_path = os.path.join(PROJECT_ROOT, item)
            if not os.path.exists(item_path):
                print(f"  [!] Warning: Missing item '{item}'. Make sure it is generated first!")
                continue

            if is_dir:
                for root, dirs, files in os.walk(item_path):
                    # Skip __pycache__
                    if "__pycache__" in root:
                        continue
                    for file in files:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, PROJECT_ROOT)
                        zf.write(file_path, rel_path)
                        print(f"  + Added: {rel_path}")
            if item == "Prelim_Project_Report.pdf":
                pdf_candidates = [
                    "Prelim_Project_Report_Final.pdf",
                    "Prelim_Project_Report_v2.pdf",
                    "Prelim_Project_Report.pdf",
                    "test_report.pdf"
                ]
                chosen = next((c for c in pdf_candidates if os.path.exists(os.path.join(PROJECT_ROOT, c))), None)
                if chosen:
                    item_path = os.path.join(PROJECT_ROOT, chosen)
                    zf.write(item_path, "Prelim_Project_Report.pdf")
                    print(f"  + Added: Prelim_Project_Report.pdf (from {chosen})")
            else:
                zf.write(item_path, item)
                print(f"  + Added: {item}")

    print(f"\n[SUCCESS]: Submission archive created at: {zip_path}")
    print(f"File size: {os.path.getsize(zip_path) / 1024:.2f} KB\n")


if __name__ == "__main__":
    name1 = sys.argv[1] if len(sys.argv) > 1 else "Carvajal"
    name2 = sys.argv[2] if len(sys.argv) > 2 else "Sarsalijo"
    create_submission_zip(name1, name2)
