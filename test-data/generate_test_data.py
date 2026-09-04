"""
Comprehensive Synthetic Data Generator for Clinevo Smart Inbox Assistant
Generates 22 realistic test cases covering all criteria in Section 6 of problem statement:
- 16 ICSR reaction cases (varying detail, forms, tables, scanned notes, articles, non-English)
- 5 Digital PDF forms with tables
- 2 Scanned/handwritten-style PDFs with simulated image scan
- 5 Multi-column journal articles with abstract, case presentation, discussion, references
- 3 Non-English PDFs (French, German, Spanish)
- 2 Pure Product Quality Complaints (PQC) with defect diagrams
- 2 Pure Medical Information Inquiries (MI)
- 2 Irrelevant/marketing emails
- 1 Dual-category ICSR + PQC case
"""

import os
import io
import fitz  # PyMuPDF
from PIL import Image, ImageDraw
from email.message import EmailMessage

def create_table_pdf(doc, page, x, y, width, headers, rows, title=None):
    """Draw a professional structured table on a PyMuPDF page."""
    if title:
        page.insert_text((x, y - 6), title, fontsize=10, fontname="helv", color=(0.1, 0.2, 0.4))
        y += 14

    col_count = len(headers)
    col_w = width / col_count
    row_h = 18

    # Header row background
    header_rect = fitz.Rect(x, y, x + width, y + row_h)
    page.draw_rect(header_rect, color=(0.2, 0.35, 0.6), fill=(0.88, 0.92, 0.98))

    # Header text
    for i, h in enumerate(headers):
        page.insert_text((x + i * col_w + 4, y + 13), str(h), fontsize=8, fontname="helv", color=(0.1, 0.2, 0.4))

    y += row_h

    # Data rows
    for r_idx, row in enumerate(rows):
        bg = (0.97, 0.98, 1.0) if r_idx % 2 == 1 else (1.0, 1.0, 1.0)
        row_rect = fitz.Rect(x, y, x + width, y + row_h)
        page.draw_rect(row_rect, color=(0.75, 0.8, 0.88), fill=bg)

        for i, val in enumerate(row):
            page.insert_text((x + i * col_w + 4, y + 13), str(val), fontsize=8, fontname="helv", color=(0.15, 0.15, 0.15))
        y += row_h

    return y + 10

def create_defect_image():
    """Create a simulated product defect diagram image (PNG bytes)."""
    img = Image.new('RGB', (320, 180), color=(245, 248, 252))
    d = ImageDraw.Draw(img)
    # Draw vial outline
    d.rectangle([100, 30, 220, 150], outline=(70, 90, 120), width=3, fill=(230, 240, 255))
    d.rectangle([130, 15, 190, 30], outline=(70, 90, 120), width=2, fill=(180, 200, 220))
    # Draw crack / defect line
    d.line([140, 60, 175, 90, 160, 110, 190, 135], fill=(220, 40, 40), width=3)
    # Defect label
    d.text((15, 15), "DEFECT INSPECTION: LOT C4401 / B9912", fill=(40, 40, 60))
    d.text((15, 160), "Visual Finding: Physical defect / fracture line detected", fill=(180, 30, 30))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()

def create_scanned_page_image(title, fields, notes, doc_id):
    """Create a simulated scanned paper note image with handwriting style."""
    img = Image.new('RGB', (600, 800), color=(252, 250, 242)) # slight off-white paper tint
    d = ImageDraw.Draw(img)

    # Header border & stamp
    d.rectangle([30, 30, 570, 770], outline=(160, 160, 160), width=2)
    d.rectangle([420, 45, 555, 95], outline=(180, 80, 80), width=2)
    d.text((430, 55), "SCANNED INTAKE", fill=(180, 80, 80))
    d.text((430, 75), f"ID: {doc_id}", fill=(120, 60, 60))

    d.text((50, 50), title.upper(), fill=(40, 50, 70))
    d.text((50, 70), "CLINICAL ENCOUNTER & ADVERSE EVENT RECORD", fill=(80, 90, 110))
    d.line([50, 105, 550, 105], fill=(180, 180, 180), width=1)

    y = 125
    for k, v in fields:
        d.text((50, y), f"{k}:", fill=(60, 60, 70))
        d.text((220, y), str(v), fill=(20, 30, 90)) # darker ink color
        d.line([215, y + 16, 540, y + 16], fill=(210, 210, 220), width=1)
        y += 35

    y += 10
    d.text((50, y), "PHYSICIAN / CLINICIAN ENCOUNTER NOTES:", fill=(60, 60, 70))
    y += 25
    d.rectangle([50, y, 550, y + 140], outline=(200, 200, 210), fill=(248, 246, 238))
    d.text((60, y + 10), notes, fill=(20, 30, 90))

    y += 160
    d.text((50, y), "Clinician Signature: Dr. J. Wilson, MD", fill=(20, 30, 90))
    d.text((380, y), "Date: 01-Sep-2026", fill=(40, 40, 50))

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()

def generate():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    emails_dir = os.path.join(base_dir, "emails")
    pdfs_dir = os.path.join(base_dir, "pdfs")
    os.makedirs(emails_dir, exist_ok=True)
    os.makedirs(pdfs_dir, exist_ok=True)

    # Clear old files
    for f in os.listdir(emails_dir):
        p = os.path.join(emails_dir, f)
        if os.path.isfile(p):
            os.remove(p)
    for f in os.listdir(pdfs_dir):
        p = os.path.join(pdfs_dir, f)
        if os.path.isfile(p):
            os.remove(p)

    cases = [
        # ── 1. DIGITAL FORM ICSR (High Detail with Structured Lab Table) ──────
        {
            "id": "synthetic-01-icsr-cioms-digital",
            "from": "safety.officer@metro-general-hospital.org",
            "subject": "URGENT CIOMS-I: Severe Cutaneous Rash with SynthoStatin 20mg (Patient SYN-5401)",
            "date": "Mon, 01 Sep 2026 09:15:00 +0000",
            "body": "Dear Pharmacovigilance Team,\n\nPlease find attached the completed CIOMS-I adverse drug reaction report for Patient ID SYN-5401.\nPatient is a 54 year old Male (Weight: 78 kg, Height: 178 cm, History: Type 2 Diabetes) who developed a severe cutaneous rash following oral administration of SynthoStatin 20mg daily.\nReporter: Dr. Synthetic Jones, General Practitioner, United States.\nReaction onset: 18 Aug 2026. Outcome: Recovering.\nDetailed laboratory test panel included in attachment.",
            "pdf_name": "cioms_syntho_report.pdf",
            "type": "form_icsr",
            "title": "CIOMS-I ADVERSE DRUG REACTION REPORT",
            "sections": [
                ("I. REACTION INFORMATION", [
                    ("Patient Identifier", "SYN-5401"),
                    ("Age / Sex", "54 Years / Male"),
                    ("Weight / Height", "78 kg / 178 cm"),
                    ("Relevant Medical History", "Type 2 Diabetes Mellitus, Hyperlipidemia"),
                    ("Adverse Reaction Description", "Severe cutaneous rash and erythematous lesions"),
                    ("Onset Date", "18 Aug 2026"),
                    ("Outcome", "Recovering"),
                    ("Seriousness Assessment", "Serious (Hospitalization required)")
                ]),
                ("II. SUSPECT DRUG INFORMATION", [
                    ("Suspect Product Name", "SynthoStatin"),
                    ("Dose / Formulation", "20mg Tablet"),
                    ("Route of Administration", "Oral"),
                    ("Therapy Start Date", "01 Aug 2026"),
                    ("Therapy Stop Date", "19 Aug 2026"),
                    ("Batch / Lot Number", "Lot S7702")
                ]),
                ("III. REPORTER DETAILS", [
                    ("Reporter Identity", "Dr. Synthetic Jones"),
                    ("Professional Role", "General Practitioner"),
                    ("Institution / Clinic", "Metro General Hospital"),
                    ("Country", "United States")
                ])
            ],
            "table": {
                "title": "Laboratory Test Panel (Liver & Inflammatory Biomarkers):",
                "headers": ["Test Parameter", "Baseline Value", "Onset (18 Aug)", "Follow-up (25 Aug)", "Reference Range"],
                "rows": [
                    ["ALT (Alanine Transaminase)", "24 U/L", "145 U/L", "62 U/L", "7 - 56 U/L"],
                    ["AST (Aspartate Transaminase)", "22 U/L", "118 U/L", "48 U/L", "10 - 40 U/L"],
                    ["Total Bilirubin", "0.8 mg/dL", "1.9 mg/dL", "1.1 mg/dL", "0.2 - 1.2 mg/dL"],
                    ["C-Reactive Protein (CRP)", "2.1 mg/L", "48.5 mg/L", "12.0 mg/L", "< 5.0 mg/L"]
                ]
            }
        },

        # ── 2. CLINICAL HOSPITAL REPORT ICSR (with Dosing Schedule Table) ─────
        {
            "id": "synthetic-02-icsr-hospital-digital",
            "from": "pharmacovigilance@university-medcenter.org",
            "subject": "Clinical Safety Report: Marked ALT/AST Transaminase Elevation post SynthoStatin 40mg",
            "date": "Mon, 01 Sep 2026 10:30:00 +0000",
            "body": "Adverse Drug Reaction Notification:\nPatient age 62 Female (Weight: 65 kg, Height: 162 cm, History: Dyslipidemia) experienced marked ALT/AST transaminase elevation and hepatic injury 2 weeks following SynthoStatin 40mg oral daily.\nReporter: Dr. Adams, Hepatologist, United Kingdom.\nReaction started: 15 Aug 2026. Drug discontinued on 20 Aug 2026. Outcome: Recovering.",
            "pdf_name": "hospital_hepatic_report.pdf",
            "type": "form_icsr",
            "title": "HOSPITAL PHARMACOVIGILANCE CASE REPORT",
            "sections": [
                ("PATIENT & EVENT DETAILS", [
                    ("Patient", "Female, 62 years old"),
                    ("Demographics", "Weight: 65 kg, Height: 162 cm"),
                    ("Past History", "Dyslipidemia, Hypertension"),
                    ("Suspected Adverse Reaction", "Marked ALT/AST transaminase elevation and hepatic injury"),
                    ("Reaction Onset", "15 Aug 2026"),
                    ("Outcome of Reaction", "Recovering"),
                    ("Seriousness", "Serious")
                ]),
                ("DRUG & DOSING", [
                    ("Medicinal Product", "SynthoStatin"),
                    ("Dose / Route", "40mg daily / Oral"),
                    ("Start Date", "01 Aug 2026"),
                    ("Discontinuation Date", "20 Aug 2026"),
                    ("Reporter", "Dr. Adams, Hepatologist, United Kingdom")
                ])
            ],
            "table": {
                "title": "Dosing & Hepatic Transaminase Trend Table:",
                "headers": ["Date", "SynthoStatin Dose", "ALT (U/L)", "AST (U/L)", "Total Bilirubin (mg/dL)"],
                "rows": [
                    ["01 Aug 2026", "40mg Oral", "28", "25", "0.7"],
                    ["15 Aug 2026", "40mg Oral", "320", "285", "2.4"],
                    ["20 Aug 2026", "Discontinued", "210", "180", "1.8"],
                    ["28 Aug 2026", "0mg (Washout)", "75", "55", "1.0"]
                ]
            }
        },

        # ── 3. SPECIALIST CARDIOLOGY REPORT ICSR ──────────────────────────────
        {
            "id": "synthetic-03-icsr-cardiac-digital",
            "from": "cardio-safety@heart-institute.org",
            "subject": "Spontaneous Adverse Event: Acute Palpitations & Dizziness post SynthoCardio 10mg",
            "date": "Mon, 01 Sep 2026 11:15:00 +0000",
            "body": "Spontaneous Safety Report:\nPatient age 58 Male (Weight: 82 kg, Height: 180 cm) experienced sudden palpitations and dizziness 1 hour after taking oral SynthoCardio 10mg.\nReporter: Dr. Evans, Cardiologist, Heart Institute, United States.\nReaction started on 22 Aug 2026. Outcome: Resolved.",
            "pdf_name": "cardiac_event_synthocardio.pdf",
            "type": "form_icsr",
            "title": "CARDIOLOGY SPECIALIST SAFETY ASSESSMENT",
            "sections": [
                ("CLINICAL SAFETY RECORD", [
                    ("Patient Identifier", "Patient Male aged 58 years"),
                    ("Weight / Height", "82 kg / 180 cm"),
                    ("Relevant Medical History", "Mild baseline sinus bradycardia"),
                    ("Product Name", "SynthoCardio"),
                    ("Dose & Route", "10mg / Oral"),
                    ("Adverse Reaction Description", "Acute palpitations and dizziness"),
                    ("Onset Date", "22 Aug 2026"),
                    ("Outcome", "Resolved"),
                    ("Seriousness", "Non-serious"),
                    ("Reporter", "Dr. Evans, Cardiologist, United States")
                ])
            ],
            "table": {
                "title": "Vital Signs & ECG Monitor Readings:",
                "headers": ["Timepoint", "Heart Rate (bpm)", "Blood Pressure (mmHg)", "Rhythm Finding"],
                "rows": [
                    ["Baseline (Pre-dose)", "68", "125/80", "Normal Sinus Rhythm"],
                    ["+1 hr Post-dose", "134", "105/65", "Sinus Tachycardia / Palpitations"],
                    ["+4 hrs Post-dose", "82", "120/78", "Resolved to Normal Rhythm"]
                ]
            }
        },

        # ── 4. MEDWATCH FORM ICSR (Digital Form) ──────────────────────────────
        {
            "id": "synthetic-04-icsr-medwatch-digital",
            "from": "drugsafety@regional-clinic.org",
            "subject": "MedWatch 3500A Form: SynthoStatin Induced Urticaria and Angioedema",
            "date": "Mon, 01 Sep 2026 12:00:00 +0000",
            "body": "Attached is the completed MedWatch 3500A form for adverse drug reaction: Urticaria and mild facial angioedema in a 42 year old female patient taking oral SynthoStatin 20mg daily.\nReporter: Dr. Taylor, Physician, Canada.\nTherapy start: 10 Aug 2026, Onset: 14 Aug 2026. Outcome: Recovered.",
            "pdf_name": "medwatch_synthostatin_form.pdf",
            "type": "form_icsr",
            "title": "MEDWATCH FORM 3500A - MANDATORY SAFETY REPORT",
            "sections": [
                ("SECTION A: PATIENT INFORMATION", [
                    ("Patient", "Female, 42 years old"),
                    ("Weight / Height", "60 kg / 165 cm"),
                    ("Relevant History", "Allergic rhinitis")
                ]),
                ("SECTION B: ADVERSE EVENT", [
                    ("Adverse Event", "Urticaria and facial angioedema"),
                    ("Onset Date", "14 Aug 2026"),
                    ("Outcome", "Recovered"),
                    ("Seriousness", "Serious")
                ]),
                ("SECTION C: SUSPECT PRODUCT", [
                    ("Product Name", "SynthoStatin"),
                    ("Dose / Route", "20mg / Oral"),
                    ("Start / Stop Date", "10 Aug 2026 / 15 Aug 2026"),
                    ("Lot Number", "Lot K8831")
                ]),
                ("SECTION E: REPORTER", [
                    ("Reporter", "Dr. Taylor, Physician, Regional Clinic, Canada")
                ])
            ],
            "table": None
        },

        # ── 5. POST-MARKETING SURVEILLANCE FORM ICSR ──────────────────────────
        {
            "id": "synthetic-05-icsr-surveillance-digital",
            "from": "surveillance@global-pharma-watch.org",
            "subject": "Post-Marketing Safety Intake: Severe Cutaneous Adverse Reaction to SynthoStatin",
            "date": "Mon, 01 Sep 2026 12:30:00 +0000",
            "body": "Post-Marketing Pharmacovigilance Intake Form:\nPatient age 67 Male (Weight: 85 kg, Height: 172 cm) developed a severe cutaneous rash with fever after taking SynthoStatin 20mg.\nReporter: Dr. Miller, Oncologist, Australia.\nOnset: 05 Aug 2026. Outcome: Recovering.",
            "pdf_name": "postmarketing_surveillance_intake.pdf",
            "type": "form_icsr",
            "title": "POST-MARKETING SURVEILLANCE SAFETY INTAKE",
            "sections": [
                ("CASE DETAILS", [
                    ("Patient", "Male, 67 years old, 85 kg, 172 cm"),
                    ("Medical History", "Prostate carcinoma (in remission)"),
                    ("Suspected Product", "SynthoStatin 20mg Oral"),
                    ("Adverse Reaction", "Severe cutaneous rash with fever"),
                    ("Reaction Onset Date", "05 Aug 2026"),
                    ("Event Outcome", "Recovering"),
                    ("Seriousness", "Serious (Life-threatening / Hospitalization)"),
                    ("Reporter Information", "Dr. Miller, Oncologist, Australia")
                ])
            ],
            "table": None
        },

        # ── 6. SCANNED / HANDWRITTEN CLINICAL NOTE ICSR ───────────────────────
        {
            "id": "synthetic-06-icsr-scanned-note",
            "from": "records@outpatient-care.org",
            "subject": "Scanned Doctor Clinical Encounter Note: Patient SYN-3802 SynthoStatin Reaction",
            "date": "Mon, 01 Sep 2026 13:10:00 +0000",
            "body": "Attached is the scanned encounter note from Dr. Wilson regarding patient SYN-3802 (Female, age 38) who presented with severe erythematous rash and headache following SynthoStatin 20mg oral therapy.\nReporter: Dr. Wilson, Physician, United States.",
            "pdf_name": "scanned_doctor_note.pdf",
            "type": "scanned_image",
            "title": "Outpatient Clinical Encounter Note",
            "doc_id": "SYN-3802",
            "fields": [
                ("Patient ID & Age / Sex", "SYN-3802 | 38 yo Female"),
                ("Suspect Drug / Dose", "SynthoStatin 20mg Oral Tablet"),
                ("Reported Reaction", "Severe erythematous rash and headache"),
                ("Date of Reaction Onset", "12 Aug 2026"),
                ("Reaction Outcome", "Recovering"),
                ("Reporting Physician", "Dr. Wilson, Physician, United States")
            ],
            "notes": "Patient reports widespread pruritic macular rash on trunk and arms.\nStarted SynthoStatin 10 days ago. Drug held today.\nRx: Oral antihistamine and topical hydrocortisone."
        },

        # ── 7. SCANNED PAPER INTAKE SHEET ICSR ────────────────────────────────
        {
            "id": "synthetic-07-icsr-scanned-form",
            "from": "intake@urgentcare-center.org",
            "subject": "Scanned Paper Intake Sheet: SynthoCardio Dizziness & Nausea Report",
            "date": "Mon, 01 Sep 2026 13:45:00 +0000",
            "body": "Attached scanned triage questionnaire for patient Male age 51 who experienced acute dizziness, nausea, and palpitations after SynthoCardio 10mg.\nReporter: Nurse Jenkins, Nurse, United States.",
            "pdf_name": "scanned_intake_sheet.pdf",
            "type": "scanned_image",
            "title": "Urgent Care Triage Intake Form",
            "doc_id": "UC-9914",
            "fields": [
                ("Patient Name & Age / Sex", "Patient 51M (Male, 51 years old)"),
                ("Suspected Medication", "SynthoCardio 10mg Oral"),
                ("Adverse Event Experienced", "Acute dizziness, nausea, and palpitations"),
                ("Onset Date", "24 Aug 2026"),
                ("Event Outcome", "Resolved"),
                ("Triage Nurse / Reporter", "Nurse Jenkins, Nurse, Urgent Care, United States")
            ],
            "notes": "Walk-in patient complaint of sudden dizziness 45 mins after first morning dose of SynthoCardio.\nBP 100/60 mmHg, HR 110 bpm. Symptoms subsided after rest and fluids."
        },

        # ── 8. MULTI-COLUMN ARTICLE 1: DERMATOLOGY CASE REPORT ────────────────
        {
            "id": "synthetic-08-article-dermatology",
            "from": "editor@journal-dermatology-cases.org",
            "subject": "Literature Case Report: SynthoStatin Induced Erythematous Maculopapular Rash in a 71-Year-Old Male",
            "date": "Mon, 01 Sep 2026 14:15:00 +0000",
            "body": "Please review literature case publication regarding SynthoStatin induced rash in a 71 year old male patient.\nArticle describes clinical presentation, drug withdrawal, and recovery.",
            "pdf_name": "article_cutaneous_reaction.pdf",
            "type": "article",
            "journal": "Journal of Clinical Dermatology Case Reports (2026) 14:112-116",
            "doi": "doi:10.1016/j.jcdcr.2026.08.014",
            "title": "Cutaneous Adverse Drug Eruption Associated with SynthoStatin Therapy: A Detailed Clinical Case",
            "authors": "Robert Martinez, MD; Sarah Jenkins, MD; Department of Dermatology, United States",
            "abstract": "We describe a case of severe erythematous maculopapular rash in a 71-year-old male patient following initiation of SynthoStatin 20mg oral daily for hypercholesterolemia. Symptoms commenced 10 days into therapy. Dechallenge resulted in complete resolution.",
            "case_presentation": "A 71-year-old male patient (Weight: 75 kg, past history of hypertension) presented to our outpatient clinic with an extensive erythematous maculopapular rash covering his torso and upper extremities. Ten days prior to presentation, the patient had been prescribed oral SynthoStatin 20mg once daily. Physical examination revealed confluent erythematous macules without mucosal involvement. SynthoStatin was promptly discontinued on 14 Aug 2026. Within 7 days of cessation, the rash resolved completely without scarring (Outcome: Recovered). The reporting physician was Dr. Martinez, Dermatologist.",
            "discussion": "Statin-induced cutaneous adverse reactions are well-documented yet underreported pharmacovigilance signals. In this patient, prompt dechallenge confirmed causality without rechallenge.",
            "references": [
                "1. Smith AB, et al. Cutaneous reactions to lipid-lowering agents. J Dermatol Sci. 2023;45:101-108.",
                "2. Dupont H, et al. Adverse drug reactions in pharmacovigilance databases. Lancet Pharm. 2024;12:45-52.",
                "3. Williams R. Clinical dermatology handbook, 5th ed. London: MedPress; 2022."
            ]
        },

        # ── 9. MULTI-COLUMN ARTICLE 2: CARDIOLOGY CASE PRESENTATION ───────────
        {
            "id": "synthetic-09-article-cardiology",
            "from": "reprints@cardiovascular-case-reports.org",
            "subject": "Journal Publication: SynthoCardio Associated Tachycardia & Palpitations: A Case Presentation",
            "date": "Mon, 01 Sep 2026 14:45:00 +0000",
            "body": "Attached journal publication describing SynthoCardio associated palpitations in a 55 year old female patient.\nReporter: Dr. Clark, Cardiologist, United Kingdom.",
            "pdf_name": "article_cardiac_palpitations.pdf",
            "type": "article",
            "journal": "Cardiovascular Case Reports Journal (2026) Vol 8, Issue 3",
            "doi": "doi:10.1093/ccrj/cvaa088",
            "title": "SynthoCardio Induced Palpitations and Supraventricular Tachycardia in a Middle-Aged Female",
            "authors": "Eleanor Clark, MD; Thomas Wright, MD; Heart & Vascular Division, United Kingdom",
            "abstract": "A 55-year-old female patient developed palpitations and dizziness 2 hours after receiving oral SynthoCardio 10mg. Clinical monitoring and subsequent dechallenge resulted in full recovery.",
            "case_presentation": "A 55-year-old female (Weight: 68 kg, no prior cardiac arrhythmias) was initiated on oral SynthoCardio 10mg daily for mild hypertension. Two hours following the initial dose on 16 Aug 2026, she experienced acute palpitations, lightheadedness, and dizziness. ECG confirmed transient sinus tachycardia at 130 bpm. SynthoCardio was withdrawn immediately. Heart rate normalized within 4 hours. Outcome: Resolved. Case documented by Dr. Clark, Cardiologist.",
            "discussion": "Cardiovascular adverse reactions require close surveillance during initial titration. Causality assessment was categorized as probable based on immediate onset post-dose.",
            "references": [
                "1. Taylor PK, et al. Pharmacovigilance monitoring in cardiovascular pharmacotherapy. Heart J. 2024;88:210-218.",
                "2. Gomez L. Anti-hypertensive drug safety profiles. Eur Cardiol Rev. 2023;19:77-84."
            ]
        },

        # ── 10. MULTI-COLUMN ARTICLE 3: HEPATOLOGY CASE SERIES ────────────────
        {
            "id": "synthetic-10-article-hepatology",
            "from": "med-reviews@clinical-hepatology-press.org",
            "subject": "Literature Case Series: Drug-Induced Liver Injury (DILI) Secondary to SynthoStatin 40mg",
            "date": "Mon, 01 Sep 2026 15:10:00 +0000",
            "body": "Review of literature publication on drug-induced liver injury following SynthoStatin in a 64 year old female patient.\nReporter: Dr. Richardson, Hepatologist, United States.",
            "pdf_name": "article_hepatic_injury.pdf",
            "type": "article",
            "journal": "Clinical Hepatology & Drug Safety (2026) 31:401-407",
            "doi": "doi:10.1053/j.chds.2026.04.011",
            "title": "Drug-Induced Liver Injury (DILI) with Severe Transaminase Elevation Associated with High-Dose SynthoStatin",
            "authors": "Marcus Richardson, MD; Patricia Kelly, MD; Liver Center, United States",
            "abstract": "Drug-induced liver injury is a critical adverse event in pharmacovigilance. We present a 64-year-old female who developed acute hepatotoxicity with marked ALT/AST elevation following SynthoStatin 40mg daily.",
            "case_presentation": "A 64-year-old female patient (Weight: 70 kg, Height: 165 cm) presented with jaundice, dark urine, and fatigue. She had been prescribed oral SynthoStatin 40mg daily starting on 01 Aug 2026. On 20 Aug 2026, routine blood tests demonstrated ALT 420 U/L and AST 360 U/L (elevated transaminases). SynthoStatin was discontinued immediately (Outcome: Recovering). Seriousness was graded as Serious due to hospitalization. Documented by Dr. Richardson, Hepatologist.",
            "discussion": "Idiosyncratic hepatotoxicity remains a key safety signal. Early biomarker monitoring is essential for patient protection.",
            "references": [
                "1. Zimmerman HJ. Hepatotoxicity: adverse effects of drugs on liver. 2nd ed. Philadelphia; 2020.",
                "2. Chalasani N, et al. ACG clinical guideline: diagnosis and management of DILI. Am J Gastroenterol. 2023;116:878-898."
            ]
        },

        # ── 11. MULTI-COLUMN ARTICLE 4: RENAL SAFETY REPORT ───────────────────
        {
            "id": "synthetic-11-article-nephrology",
            "from": "cases@renal-pharmacotherapy.org",
            "subject": "Published Case Report: Acute Interstitial Nephritis Associated with High-Dose SynthoStatin",
            "date": "Mon, 01 Sep 2026 15:35:00 +0000",
            "body": "Published case presentation: A 69 year old male patient developed acute adverse reaction following SynthoStatin 40mg daily therapy.\nReporter: Dr. Foster, Nephrologist, United States.",
            "pdf_name": "article_renal_safety.pdf",
            "type": "article",
            "journal": "Renal Pharmacotherapy Case Reports (2026) 19:88-93",
            "doi": "doi:10.1016/j.rpcr.2026.07.009",
            "title": "Acute Interstitial Reaction and Fatigue Secondary to SynthoStatin Pharmacotherapy",
            "authors": "James Foster, MD; Renal Medicine Division, United States",
            "abstract": "A 69-year-old male developed severe fatigue, nausea, and fever following SynthoStatin 40mg administration. Dechallenge resulted in favorable clinical recovery.",
            "case_presentation": "A 69-year-old male patient (Weight: 80 kg) initiated oral SynthoStatin 40mg on 10 Jul 2026. Three weeks later (onset 02 Aug 2026), he developed acute fatigue, nausea, and mild fever. Blood tests revealed serum creatinine rise. Following cessation of SynthoStatin, renal function stabilized and symptoms resolved (Outcome: Recovered). Reported by Dr. Foster, Nephrologist.",
            "discussion": "Immune-mediated adverse reactions to statins warrant comprehensive differential diagnosis in elderly patients.",
            "references": [
                "1. Perazella MA. Drug-induced nephrotoxicity. Clin J Am Soc Nephrol. 2022;17:123-134.",
                "2. Bennett WM. Guide to drug dosage in impaired renal function. 4th ed. 2021."
            ]
        },

        # ── 12. MULTI-COLUMN ARTICLE 5: CLINICAL PHARMACOLOGY ─────────────────
        {
            "id": "synthetic-12-article-pharmacology",
            "from": "editorial@pharmacology-case-reports.com",
            "subject": "Case Report: SynthoCardio Induced Hypotension and Severe Dizziness in a 61-Year-Old Female",
            "date": "Mon, 01 Sep 2026 16:00:00 +0000",
            "body": "Clinical case presentation: SynthoCardio induced dizziness and hypotension in a 61 year old female patient.\nReporter: Dr. Bell, Clinical Pharmacologist, United States.",
            "pdf_name": "article_clinical_pharmacology.pdf",
            "type": "article",
            "journal": "Journal of Clinical Pharmacology Studies (2026) 22:54-59",
            "doi": "doi:10.1177/009127002611029",
            "title": "Post-Marketing Adverse Event: Severe Dizziness and Palpitations Following First-Dose SynthoCardio",
            "authors": "Catherine Bell, PharmD; Arthur Pendelton, MD; Clinical Pharmacology Dept, United States",
            "abstract": "We present a case of severe dizziness and palpitations in a 61-year-old female after taking oral SynthoCardio 10mg. Clinical monitoring documented rapid symptom onset and subsequent resolution.",
            "case_presentation": "A 61-year-old female patient (Weight: 63 kg) received oral SynthoCardio 10mg for mild hypertension on 18 Aug 2026. Within 90 minutes, she experienced sudden severe dizziness and palpitations. Blood pressure decreased to 92/58 mmHg. SynthoCardio was discontinued. Outcome: Resolved within 6 hours. Reporter: Dr. Bell, Clinical Pharmacologist.",
            "discussion": "First-dose hemodynamic responses require proactive patient counseling and pharmacovigilance surveillance.",
            "references": [
                "1. Johnson KL. Pharmacokinetic variability in cardiovascular therapeutics. Clin Pharmacokinet. 2023;62:415-428.",
                "2. World Health Organization. Safety monitoring of medicinal products. Geneva; 2022."
            ]
        },

        # ── 13. NON-ENGLISH FRENCH ICSR FORM ──────────────────────────────────
        {
            "id": "synthetic-13-icsr-french",
            "from": "vigilance@hopital-paris.fr",
            "subject": "Signalement d'Effets Indésirables - SynthoStatin (Femme, 48 ans)",
            "date": "Mon, 01 Sep 2026 16:30:00 +0000",
            "body": "Cher département de pharmacovigilance,\n\nVeuillez trouver ci-joint le signalement pour une patiente de 48 ans ayant développé une éruption cutanée et prurit suite à la prise de SynthoStatin 20mg.\nRapporteur: Dr. Dubois, Médecin Généraliste, Hôpital de Paris, France.\nDébut: 14 Août 2026. Évolution: Rétablissement (Recovered).",
            "pdf_name": "signalement_syntho_fr.pdf",
            "type": "non_english",
            "lang": "French",
            "title": "CENTRE RÉGIONAL DE PHARMACOVIGILANCE - FICHE DE SIGNALEMENT",
            "sections": [
                ("I. INFORMATION SUR LE PATIENT", [
                    ("Identifiant / Sexe / Âge", "Patiente 48 ans, Femme"),
                    ("Poids / Taille", "62 kg / 168 cm"),
                    ("Antécédents médicaux", "Hypercholestérolémie familiale")
                ]),
                ("II. EFFET INDÉSIRABLE SUSPECTÉ", [
                    ("Description de la réaction", "Éruption cutanée érythémateuse avec prurit sévère"),
                    ("Date de début", "14 Août 2026"),
                    ("Évolution / Issue", "Rétablissement complet suite à l'arrêt du médicament"),
                    ("Gravité", "Non grave")
                ]),
                ("III. MÉDICAMENT SUSPECT", [
                    ("Nom du médicament", "SynthoStatin"),
                    ("Posologie / Voie", "20mg par jour / Voie orale"),
                    ("Date de début du traitement", "01 Août 2026"),
                    ("Numéro de lot", "Lot FR-8812")
                ]),
                ("IV. NOTIFICATEUR", [
                    ("Nom du déclarant", "Dr. Dubois"),
                    ("Qualité / Rôle", "Médecin Généraliste"),
                    ("Établissement / Pays", "Hôpital de Paris, France")
                ])
            ]
        },

        # ── 14. NON-ENGLISH GERMAN ICSR FORM ──────────────────────────────────
        {
            "id": "synthetic-14-icsr-german",
            "from": "arzneimittelsicherheit@klinikum-berlin.de",
            "subject": "Meldung über unerwünschte Arzneimittelwirkungen - SynthoCardio (Mann, 59 Jahre)",
            "date": "Mon, 01 Sep 2026 17:00:00 +0000",
            "body": "Sehr geehrte Damen und Herren,\n\nHiermit übermitteln wir den Bericht über eine unerwünschte Arzneimittelwirkung bei einem 59-jährigen Patienten nach Einnahme von SynthoCardio 10mg (Herzklopfen und Schwindel).\nMelder: Dr. Becker, Arzt, Klinikum Berlin, Deutschland.\nBeginn: 20. August 2026. Ausgang: Wiederhergestellt (Recovered).",
            "pdf_name": "meldung_synthocardio_de.pdf",
            "type": "non_english",
            "lang": "German",
            "title": "MELDUNG EINER UNERWÜNSCHTEN ARZNEIMITTELWIRKUNG (UAW)",
            "sections": [
                ("1. PATIENTENANGABEN", [
                    ("Patient", "Mann, 59 Jahre alt"),
                    ("Gewicht / Größe", "81 kg / 176 cm"),
                    ("Anamnese", "Arterielle Hypertonie")
                ]),
                ("2. UNERWÜNSCHTE WIRKUNG", [
                    ("Symptome / Reaktion", "Herzklopfen (Palpitationen), Schwindel und Übelkeit"),
                    ("Beginn der Reaktion", "20. August 2026"),
                    ("Ausgang der UAW", "Wiederhergestellt (Resolved)"),
                    ("Schweregrad", "Nicht schwerwiegend")
                ]),
                ("3. VERDÄCHTIGES ARZNEIMITTEL", [
                    ("Arzneimittel", "SynthoCardio"),
                    ("Dosis / Verabreichungsweg", "10mg / Oral"),
                    ("Behandlungsbeginn", "15. August 2026"),
                    ("Chargennummer", "Lot DE-4491")
                ]),
                ("4. ANGABEN ZUM MELDER", [
                    ("Melder", "Dr. Becker, Arzt, Klinikum Berlin, Deutschland")
                ])
            ]
        },

        # ── 15. NON-ENGLISH SPANISH ICSR FORM ─────────────────────────────────
        {
            "id": "synthetic-15-icsr-spanish",
            "from": "farmacovigilancia@hospital-madrid.es",
            "subject": "Notificación de Sospecha de Reacción Adversa a Medicamentos - SynthoStatin (Mujer, 53 años)",
            "date": "Mon, 01 Sep 2026 17:25:00 +0000",
            "body": "Estimado equipo de farmacovigilancia,\n\nNotificación de sospecha de reacción adversa a medicamentos: Paciente mujer de 53 años presentó erupción cutánea y prurito intenso tras administración de SynthoStatin 20mg oral.\nNotificador: Dr. Gomez, Médico, Hospital Madrid, España.\nInicio: 19 Agosto 2026. Desenlace: Recuperado.",
            "pdf_name": "notificacion_reaccion_es.pdf",
            "type": "non_english",
            "lang": "Spanish",
            "title": "SISTEMA DE FARMACOVIGILANCIA - NOTIFICACIÓN DE REACCIÓN ADVERSA",
            "sections": [
                ("DATOS DEL PACIENTE", [
                    ("Paciente", "Mujer, 53 años de edad"),
                    ("Peso / Talla", "66 kg / 164 cm"),
                    ("Historia clínica", "Hipercolesterolemia")
                ]),
                ("REACCIÓN ADVERSA SOSPECHADA", [
                    ("Descripción", "Erupción cutánea eritematosa y prurito intenso"),
                    ("Fecha de inicio", "19 Agosto 2026"),
                    ("Desenlace", "Recuperado (Recovered)"),
                    ("Gravedad", "No grave")
                ]),
                ("MEDICAMENTO SOSPECHOSO", [
                    ("Medicamento", "SynthoStatin"),
                    ("Dosis / Vía", "20mg / Vía oral"),
                    ("Fecha inicio tratamiento", "05 Agosto 2026"),
                    ("Lote", "Lot ES-7731")
                ]),
                ("DATOS DEL NOTIFICADOR", [
                    ("Notificador", "Dr. Gomez, Médico, Hospital Madrid, España")
                ])
            ]
        },

        # ── 16. DUAL CATEGORY: ICSR + PQC (Cracked Vial + Rash Reaction) ──────
        {
            "id": "synthetic-16-icsr-pqc-dual",
            "from": "clinic-rep@synthetic-health.org",
            "subject": "Defective Packaging & Severe Localized Itching Report: SynthoVial Lot B9912",
            "date": "Mon, 01 Sep 2026 17:50:00 +0000",
            "body": "Dear Quality & Safety Department,\n\nDual Incident Report:\n1. Product Defect: SynthoVial from Lot B9912 had cracked glass packaging and liquid leakage upon opening carton.\n2. Adverse Reaction: Patient (Male, age 49, 74 kg) experienced severe localized itching and erythema after accidental skin contact with leaked liquid.\nReporter: Dr. Henderson, General Practitioner, United States.\nDefect photo and clinical case details attached.",
            "pdf_name": "cracked_vial_reaction.pdf",
            "type": "defect_and_ae",
            "title": "DUAL PRODUCT QUALITY COMPLAINT & SAFETY INCIDENT REPORT",
            "sections": [
                ("PART A: PRODUCT QUALITY COMPLAINT (PQC)", [
                    ("Product Name", "SynthoVial"),
                    ("Batch / Lot Number", "Lot B9912"),
                    ("Defect Description", "Cracked glass vial neck with product leakage upon carton opening"),
                    ("Packaging Condition", "Damaged packaging / cracked vial"),
                    ("Photograph Mentioned", "Yes (Defect diagram embedded below)")
                ]),
                ("PART B: ADVERSE EVENT REPORT (ICSR)", [
                    ("Patient", "Male, 49 years old, 74 kg"),
                    ("Adverse Reaction", "Severe localized itching, erythema, and rash on hands"),
                    ("Reaction Onset", "26 Aug 2026"),
                    ("Outcome", "Recovering"),
                    ("Reporter", "Dr. Henderson, General Practitioner, United States")
                ])
            ]
        },

        # ── 17. PURE PRODUCT QUALITY COMPLAINT 1 (Cracked Vial) ───────────────
        {
            "id": "synthetic-17-pqc-cracked-vial",
            "from": "hospital-pharmacy@regional-care.org",
            "subject": "Product Quality Complaint: Cracked Vial Glass Wall Lot C4401",
            "date": "Mon, 01 Sep 2026 18:15:00 +0000",
            "body": "Quality Alert & Complaint:\nReporting cracked vial glass wall upon opening shipment carton for SynthoVial Batch Lot C4401.\nNo patient administration occurred; no adverse event. Product quarantined.\nPhotographic evidence and defect report attached. Please dispatch replacement stock.",
            "pdf_name": "vial_defect_c4401.pdf",
            "type": "pqc_only",
            "title": "PRODUCT QUALITY COMPLAINT REPORT",
            "sections": [
                ("COMPLAINT INVESTIGATION DETAILS", [
                    ("Suspect Product", "SynthoVial"),
                    ("Batch / Lot Number", "Lot C4401"),
                    ("Defect Type", "Cracked vial glass wall and compromised sterile barrier"),
                    ("Quantity Affected", "3 vials in Carton #04"),
                    ("Patient Exposure", "None — quarantined prior to dispensing"),
                    ("Photo Mentioned / Attached", "Yes (Inspection diagram attached)"),
                    ("Complainant", "Pharmacist Collins, Hospital Pharmacy, United States")
                ])
            ]
        },

        # ── 18. PURE PRODUCT QUALITY COMPLAINT 2 (Particulate Matter) ─────────
        {
            "id": "synthetic-18-pqc-particulate",
            "from": "qa-manager@synthopharm-distributor.com",
            "subject": "Product Complaint: Batch B9912 - Visible Particulate Matter",
            "date": "Mon, 01 Sep 2026 18:40:00 +0000",
            "body": "Quality Control Notification:\nIncoming quality control inspection detected visible particulate matter in parenteral solution SynthoVial, Batch Lot B9912.\nNo patient exposure reported. Lot quarantined pending vendor investigation.\nAttached: QA Laboratory Inspection Certificate.",
            "pdf_name": "particulate_inspection_b9912.pdf",
            "type": "pqc_only",
            "title": "QA LABORATORY DEFECT INSPECTION CERTIFICATE",
            "sections": [
                ("INCOMING QUALITY INSPECTION", [
                    ("Product Name", "SynthoVial Solution for Injection"),
                    ("Batch / Lot Number", "Batch B9912"),
                    ("Observed Defect", "Visible particulate matter and foreign precipitate in solution"),
                    ("Action Taken", "Quarantine of entire lot B9912"),
                    ("Patient Exposure", "No patient exposure"),
                    ("Inspector", "QA Manager Vance, Quality Assurance Division, United States")
                ])
            ]
        },

        # ── 19. PURE MEDICAL INFORMATION 1 (Pediatric Dosage) ─────────────────
        {
            "id": "synthetic-19-mi-pediatric-dosage",
            "from": "pharmacist@community-rx.com",
            "subject": "Medical Information Inquiry: Pediatric Dosage and Titration Schedule for SynthoStatin",
            "date": "Mon, 01 Sep 2026 19:00:00 +0000",
            "body": "Dear Medical Information Team,\n\nCould you please provide the recommended pediatric dosage schedule for SynthoStatin in patients aged 12-16 years with heterozygous familial hypercholesterolemia?\nWhat is the recommended starting dose and titration interval?\nNo patient reaction or defect to report. Thank you.",
            "pdf_name": "mi_pediatric_dosing_inquiry.pdf",
            "type": "mi_only",
            "title": "MEDICAL INFORMATION INQUIRY FORM",
            "sections": [
                ("INQUIRY DETAILS", [
                    ("Inquiry Topic", "Pediatric Dosage and Administration Schedule"),
                    ("Product of Interest", "SynthoStatin"),
                    ("Inquirer Information", "Pharmacist Laura Chen, Community Pharmacy, United States"),
                    ("Inquiry Question 1", "What is the recommended starting pediatric dosage for SynthoStatin in patients aged 12-16?"),
                    ("Inquiry Question 2", "What is the allowable titration interval and maximum daily dosage in adolescents?"),
                    ("Clinical Purpose", "Formulary dosing guideline review")
                ])
            ]
        },

        # ── 20. PURE MEDICAL INFORMATION 2 (Stability Query) ──────────────────
        {
            "id": "synthetic-20-mi-stability",
            "from": "nurse-station@city-hospital.org",
            "subject": "Medical Inquiry: Reconstitution Stability & Storage Duration of SynthoVial",
            "date": "Mon, 01 Sep 2026 19:25:00 +0000",
            "body": "Medical Information Request:\nWhat is the allowable room temperature stability time for SynthoVial after reconstitution with 0.9% sodium chloride?\nCan reconstituted vials be refrigerated for up to 48 hours without potency loss?\nNo adverse reaction or defect observed.",
            "pdf_name": "mi_reconstitution_stability.pdf",
            "type": "mi_only",
            "title": "MEDICAL INFORMATION PRODUCT STABILITY INQUIRY",
            "sections": [
                ("STABILITY & STORAGE INQUIRY", [
                    ("Product Inquired", "SynthoVial"),
                    ("Inquiry Topic", "Reconstitution Stability and Storage Conditions"),
                    ("Inquiry Question 1", "What is the maximum allowable room temperature stability time for SynthoVial following reconstitution with saline?"),
                    ("Inquiry Question 2", "Is refrigeration allowable for reconstituted vials up to 48 hours?"),
                    ("Inquirer", "Nurse Sarah Miller, Nurse Station, City Hospital, United States")
                ])
            ]
        },

        # ── 21. NOT RELEVANT 1 (Facilities Maintenance) ───────────────────────
        {
            "id": "synthetic-21-irrelevant-maintenance",
            "from": "facilities-booking@synthocorp.com",
            "subject": "Notice: Quarterly HVAC Maintenance & Conference Room Reservations",
            "date": "Mon, 01 Sep 2026 19:50:00 +0000",
            "body": "All Staff,\n\nPlease be advised that Conference Room 4B and Executive Boardroom will be closed next Wednesday from 8:00 AM to 4:00 PM for scheduled quarterly HVAC maintenance and filter replacements.\nPlease rebook meeting rooms via the intranet portal.\nNo action required regarding clinical or safety products.",
            "pdf_name": "facility_hvac_bulletin.pdf",
            "type": "irrelevant",
            "title": "FACILITIES & OPERATIONS MAINTENANCE BULLETIN",
            "sections": [
                ("FACILITY SCHEDULE NOTICE", [
                    ("Subject", "Quarterly HVAC Maintenance and Office Room Closures"),
                    ("Affected Areas", "Conference Room 4B, Executive Boardroom, East Wing"),
                    ("Maintenance Date", "Wednesday, 10 September 2026"),
                    ("Instructions", "Please utilize West Wing meeting rooms or virtual meeting links.")
                ])
            ]
        },

        # ── 22. NOT RELEVANT 2 (Wellness Seminar Invitation) ──────────────────
        {
            "id": "synthetic-22-irrelevant-wellness",
            "from": "hr-benefits@synthocorp.com",
            "subject": "Invitation: Annual Employee Health & Wellness Seminar Series",
            "date": "Mon, 01 Sep 2026 20:10:00 +0000",
            "body": "Dear Team,\n\nYou are invited to attend our Annual Employee Health & Wellness Seminar Series next month. Sessions include ergonomics in remote work, mindfulness techniques, and healthy nutrition.\nRegistration link is available on the internal HR portal.\nBest regards,\nHR Benefits Team",
            "pdf_name": "wellness_seminar_newsletter.pdf",
            "type": "irrelevant",
            "title": "CORPORATE HR HEALTH & WELLNESS NEWSLETTER",
            "sections": [
                ("ANNUAL WELLNESS SEMINAR SCHEDULE", [
                    ("Event Series", "Fall Employee Wellness & Ergonomics Workshop"),
                    ("Target Audience", "All Corporate and Administrative Staff"),
                    ("Topics", "Workplace Ergonomics, Stress Management, Nutrition Basics"),
                    ("Registration", "Sign up via HR portal by Friday")
                ])
            ]
        }
    ]

    defect_img_bytes = create_defect_image()

    for c in cases:
        pdf_path = os.path.join(pdfs_dir, c["pdf_name"])
        doc = fitz.open()

        if c["type"] in ["form_icsr", "pqc_only", "mi_only", "irrelevant", "defect_and_ae", "non_english"]:
            page = doc.new_page(width=595, height=842) # A4
            # Header bar
            page.draw_rect(fitz.Rect(0, 0, 595, 45), fill=(0.15, 0.28, 0.48))
            page.insert_text((30, 28), c["title"], fontsize=13, fontname="helv", color=(1.0, 1.0, 1.0))

            y = 70
            for sec_title, fields in c.get("sections", []):
                page.draw_rect(fitz.Rect(30, y, 565, y + 18), fill=(0.92, 0.94, 0.97))
                page.insert_text((35, y + 13), sec_title, fontsize=9, fontname="helv", color=(0.15, 0.25, 0.45))
                y += 26

                for label, val in fields:
                    page.insert_text((40, y), f"{label}:", fontsize=8.5, fontname="helv", color=(0.3, 0.3, 0.35))
                    page.insert_text((220, y), str(val), fontsize=8.5, fontname="helv", color=(0.1, 0.1, 0.1))
                    y += 16
                y += 10

            # Embed table if present
            if c.get("table"):
                tbl = c["table"]
                y = create_table_pdf(doc, page, 30, y + 5, 535, tbl["headers"], tbl["rows"], title=tbl.get("title"))

            # Embed defect diagram if PQC
            if c["type"] in ["pqc_only", "defect_and_ae"]:
                page.insert_text((30, y + 10), "ATTACHED DEFECT PHOTOGRAPH / SCHEMATIC:", fontsize=9, fontname="helv", color=(0.6, 0.15, 0.15))
                page.insert_image(fitz.Rect(30, y + 18, 350, y + 170), stream=defect_img_bytes)

        elif c["type"] == "scanned_image":
            # Render simulated scanned document image and place on page
            scanned_png = create_scanned_page_image(c["title"], c["fields"], c["notes"], c["doc_id"])
            page = doc.new_page(width=595, height=842)
            page.insert_image(fitz.Rect(0, 0, 595, 842), stream=scanned_png)

        elif c["type"] == "article":
            # 2-column article layout
            page = doc.new_page(width=595, height=842)
            # Header
            page.insert_text((40, 35), c["journal"], fontsize=8, fontname="helv", color=(0.4, 0.4, 0.4))
            page.insert_text((430, 35), c["doi"], fontsize=8, fontname="helv", color=(0.4, 0.4, 0.4))
            page.draw_line(fitz.Point(40, 42), fitz.Point(555, 42), color=(0.7, 0.7, 0.7), width=1)

            # Title & Authors
            page.insert_text((40, 65), c["title"][:70], fontsize=12, fontname="helv", color=(0.1, 0.15, 0.35))
            if len(c["title"]) > 70:
                page.insert_text((40, 80), c["title"][70:], fontsize=12, fontname="helv", color=(0.1, 0.15, 0.35))
            page.insert_text((40, 98), c["authors"], fontsize=8.5, fontname="helv", color=(0.3, 0.3, 0.3))
            page.draw_line(fitz.Point(40, 108), fitz.Point(555, 108), color=(0.8, 0.8, 0.8), width=1)

            # Abstract box
            page.draw_rect(fitz.Rect(40, 115, 555, 175), fill=(0.96, 0.97, 0.99), color=(0.85, 0.88, 0.92))
            page.insert_text((48, 128), "ABSTRACT", fontsize=8.5, fontname="helv", color=(0.15, 0.25, 0.45))
            # Wrap abstract text
            abs_words = c["abstract"].split()
            line1 = " ".join(abs_words[:18])
            line2 = " ".join(abs_words[18:36])
            line3 = " ".join(abs_words[36:])
            page.insert_text((48, 142), line1, fontsize=8, fontname="helv", color=(0.2, 0.2, 0.2))
            page.insert_text((48, 154), line2, fontsize=8, fontname="helv", color=(0.2, 0.2, 0.2))
            if line3:
                page.insert_text((48, 166), line3, fontsize=8, fontname="helv", color=(0.2, 0.2, 0.2))

            # Column 1: Case Presentation
            col1_x = 40
            col2_x = 300
            y_body = 195

            page.insert_text((col1_x, y_body), "CASE PRESENTATION", fontsize=9, fontname="helv", color=(0.15, 0.25, 0.45))
            page.draw_line(fitz.Point(col1_x, y_body + 3), fitz.Point(col1_x + 240, y_body + 3), color=(0.7, 0.75, 0.85), width=1)

            words = c["case_presentation"].split()
            y_curr = y_body + 16
            for idx in range(0, len(words), 7):
                line = " ".join(words[idx:idx + 7])
                page.insert_text((col1_x, y_curr), line, fontsize=8, fontname="helv", color=(0.15, 0.15, 0.15))
                y_curr += 12

            # Column 2: Discussion & References
            y_curr2 = y_body
            page.insert_text((col2_x, y_curr2), "DISCUSSION", fontsize=9, fontname="helv", color=(0.15, 0.25, 0.45))
            page.draw_line(fitz.Point(col2_x, y_curr2 + 3), fitz.Point(col2_x + 240, y_curr2 + 3), color=(0.7, 0.75, 0.85), width=1)
            y_curr2 += 16
            disc_words = c["discussion"].split()
            for idx in range(0, len(disc_words), 7):
                line = " ".join(disc_words[idx:idx + 7])
                page.insert_text((col2_x, y_curr2), line, fontsize=8, fontname="helv", color=(0.15, 0.15, 0.15))
                y_curr2 += 12

            y_curr2 += 15
            page.insert_text((col2_x, y_curr2), "REFERENCES", fontsize=9, fontname="helv", color=(0.15, 0.25, 0.45))
            page.draw_line(fitz.Point(col2_x, y_curr2 + 3), fitz.Point(col2_x + 240, y_curr2 + 3), color=(0.7, 0.75, 0.85), width=1)
            y_curr2 += 16
            for ref in c["references"]:
                page.insert_text((col2_x, y_curr2), ref[:50], fontsize=7.5, fontname="helv", color=(0.35, 0.35, 0.35))
                y_curr2 += 11
                if len(ref) > 50:
                    page.insert_text((col2_x + 8, y_curr2), ref[50:], fontsize=7.5, fontname="helv", color=(0.35, 0.35, 0.35))
                    y_curr2 += 11

        doc.save(pdf_path)
        doc.close()

        # Generate corresponding .eml file
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        msg = EmailMessage()
        msg['Message-ID'] = f"<{c['id']}@clinevo-pharma.local>"
        msg['From'] = c['from']
        msg['To'] = 'inbox@clinevo-assistant.local'
        msg['Subject'] = c['subject']
        msg['Date'] = c['date']
        msg.set_content(c['body'])

        msg.add_attachment(
            pdf_bytes,
            maintype='application',
            subtype='pdf',
            filename=c['pdf_name']
        )

        eml_path = os.path.join(emails_dir, f"{c['id']}.eml")
        with open(eml_path, "wb") as f:
            f.write(msg.as_bytes())

    print(f"Successfully generated {len(cases)} comprehensive synthetic test cases and PDF documents.")

if __name__ == "__main__":
    generate()
