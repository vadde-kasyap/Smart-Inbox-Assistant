import os
import hashlib
from email.message import EmailMessage

def create_minimal_pdf(text: str) -> bytes:
    # A standard valid minimal PDF-1.4 containing text
    clean_text = text.replace("(", "\\(").replace(")", "\\)")
    stream_content = f"BT /F1 12 Tf 72 712 Td ({clean_text}) Tj ET"
    stream_bytes = stream_content.encode('latin1', errors='replace')
    length = len(stream_bytes)
    
    obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    obj3 = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> >>\nendobj\n"
    obj4 = f"4 0 obj\n<< /Length {length} >>\nstream\n".encode('latin1') + stream_bytes + b"\nendstream\nendobj\n"
    
    header = b"%PDF-1.4\n"
    offsets = [0]
    curr = len(header)
    
    offsets.append(curr)
    curr += len(obj1)
    
    offsets.append(curr)
    curr += len(obj2)
    
    offsets.append(curr)
    curr += len(obj3)
    
    offsets.append(curr)
    curr += len(obj4)
    
    xref = b"xref\n0 5\n0000000000 65535 f \n"
    for off in offsets[1:]:
        xref += f"{off:010d} 00000 n \n".encode('latin1')
    
    trailer = f"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n{curr}\n%%EOF\n".encode('latin1')
    
    return header + obj1 + obj2 + obj3 + obj4 + xref + trailer

def generate():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    emails_dir = os.path.join(base_dir, "emails")
    pdfs_dir = os.path.join(base_dir, "pdfs")
    os.makedirs(emails_dir, exist_ok=True)
    os.makedirs(pdfs_dir, exist_ok=True)

    cases = [
        {
            "id": "synthetic-01-icsr",
            "from": "safety-officer@synthetic-hospital.org",
            "subject": "URGENT: Adverse Event Report - SynthoStatin (Male, 54)",
            "date": "Mon, 01 Sep 2026 10:15:30 +0000",
            "body": "Dear Safety Team,\n\nSpontaneous adverse reaction report for patient ID SYN-5401.\nPatient age 54 Male experienced severe cutaneous rash following 20mg SynthoStatin.\nReporter: Dr. Synthetic Jones, General Practitioner.",
            "pdf_name": "case_report_syntho.pdf",
            "pdf_text": "Synthetic ICSR Case Report: Patient 54M SynthoStatin Rash 20mg"
        },
        {
            "id": "synthetic-02-icsr-pqc",
            "from": "clinic-rep@synthetic-health.org",
            "subject": "Defective Packaging and Mild Itching Report",
            "date": "Mon, 01 Sep 2026 11:30:00 +0000",
            "body": "Dear Quality & Safety,\n\nPatient reported mild itching after taking SynthoVial from Lot B9912. The vial packaging was torn and defective.",
            "pdf_name": "pqc_investigation.pdf",
            "pdf_text": "Quality Complaint & AE: Cracked vial Lot B9912 SynthoVial itching observed"
        },
        {
            "id": "synthetic-03-pqc",
            "from": "qa-manager@synthopharm-distributor.com",
            "subject": "Product Complaint: Batch B9912 - Particulate Matter",
            "date": "Mon, 01 Sep 2026 12:45:15 +0000",
            "body": "Quality Alert:\nLot B9912 SynthoVial observed with visible particulate matter during routine incoming inspection.\nNo patient exposure reported.",
            "pdf_name": "particulate_inspection.pdf",
            "pdf_text": "PQC Laboratory Inspection: Batch B9912 Particulate matter SynthoVial defect"
        },
        {
            "id": "synthetic-04-pqc-cracked",
            "from": "hospital-pharmacy@regional-care.org",
            "subject": "Product Quality Complaint: Cracked Vial Lot C4401",
            "date": "Mon, 01 Sep 2026 13:00:00 +0000",
            "body": "Reporting cracked vial upon opening box. Batch Lot C4401 SynthoVial.\nPlease dispatch replacement stock.",
            "pdf_name": "vial_defect_c4401.pdf",
            "pdf_text": "Product Defect Report: SynthoVial Lot C4401 cracked glass wall"
        },
        {
            "id": "synthetic-05-mi-dosage",
            "from": "pharmacist@community-rx.com",
            "subject": "Medical Information Inquiry: Pediatric Dosage for SynthoStatin",
            "date": "Mon, 01 Sep 2026 14:10:00 +0000",
            "body": "Dear Medical Info Team,\n\nCould you please provide the recommended pediatric dosage schedule for SynthoStatin in patients aged 12-16?\nThank you.",
            "pdf_name": "mi_inquiry_dosage.pdf",
            "pdf_text": "Medical Information Request: Questions regarding pediatric dosing for SynthoStatin"
        },
        {
            "id": "synthetic-06-mi-stability",
            "from": "nurse-station@city-hospital.org",
            "subject": "Medical Inquiry: Reconstitution Stability of SynthoVial",
            "date": "Mon, 01 Sep 2026 14:40:00 +0000",
            "body": "Medical Information Request:\nWhat is the allowable room temperature stability time for SynthoVial after reconstitution with saline?",
            "pdf_name": "mi_stability_query.pdf",
            "pdf_text": "Medical Information Query: Product SynthoVial room temperature stability questions"
        },
        {
            "id": "synthetic-07-icsr-hepatic",
            "from": "hepatology@university-clinic.org",
            "subject": "Safety Report: Elevated Transaminases with SynthoStatin 40mg",
            "date": "Mon, 01 Sep 2026 15:20:00 +0000",
            "body": "Adverse Drug Reaction Report:\nPatient age 62 Female developed marked ALT/AST elevation 2 weeks after SynthoStatin 40mg daily.\nReporter: Dr. Adams, Hepatologist.",
            "pdf_name": "hepatic_syntho_report.pdf",
            "pdf_text": "Clinical Safety Report: Patient 62F SynthoStatin 40mg elevated liver enzymes"
        },
        {
            "id": "synthetic-08-icsr-french",
            "from": "vigilance@hopital-paris.fr",
            "subject": "Signalement d'Effets Indésirables - SynthoStatin (Femme, 48 ans)",
            "date": "Mon, 01 Sep 2026 16:05:00 +0000",
            "body": "Cher département de pharmacovigilance,\n\nVeuillez trouver le signalement pour une patiente de 48 ans ayant développé une éruption cutanée et prurit suite à SynthoStatin 20mg.",
            "pdf_name": "signalement_syntho_fr.pdf",
            "pdf_text": "Fiche de Pharmacovigilance: Patiente 48F SynthoStatin 20mg éruption cutanée prurit"
        },
        {
            "id": "synthetic-09-article",
            "from": "journal-watch@medical-press.org",
            "subject": "Literature Case Presentation: Cutaneous Drug Eruption with SynthoStatin",
            "date": "Mon, 01 Sep 2026 16:45:00 +0000",
            "body": "Please review literature case publication regarding SynthoStatin induced rash in a 71 year old male patient.",
            "pdf_name": "literature_case_article.pdf",
            "pdf_text": "Journal of Clinical Case Reports: Abstract: A 71yo male developed rash after SynthoStatin. References: 1. Smith et al."
        },
        {
            "id": "synthetic-10-scanned",
            "from": "clinic-records@outpatient-center.org",
            "subject": "Scanned Adverse Event Note: Patient SynthoStatin",
            "date": "Mon, 01 Sep 2026 17:15:00 +0000",
            "body": "Attached is the scanned clinical encounter note for adverse reaction SynthoStatin headache and rash.",
            "pdf_name": "scanned_clinic_note.pdf",
            "pdf_text": "Scanned Encounter Record: Patient 38 Female SynthoStatin rash headache"
        },
        {
            "id": "synthetic-11-icsr-cardiac",
            "from": "cardio-safety@heart-institute.org",
            "subject": "Adverse Event Notification: Palpitations post SynthoCardio",
            "date": "Mon, 01 Sep 2026 17:50:00 +0000",
            "body": "Spontaneous Adverse Event Report:\nPatient age 58 Male experienced palpitations and dizziness 1 hour after taking SynthoCardio 10mg.\nReporter: Dr. Evans, Cardiologist.",
            "pdf_name": "cardiac_event_synthocardio.pdf",
            "pdf_text": "Safety Case Report: Patient 58M SynthoCardio palpitations reaction"
        },
        {
            "id": "synthetic-12-irrelevant",
            "from": "facilities-booking@synthocorp.com",
            "subject": "Notice: Quarterly Maintenance and Room Reservations",
            "date": "Mon, 01 Sep 2026 18:30:00 +0000",
            "body": "All Staff,\n\nPlease be advised that conference room 4B will be closed next Wednesday for HVAC maintenance.\nNo action required regarding clinical products.",
            "pdf_name": "maintenance_schedule.pdf",
            "pdf_text": "Facilities Bulletin: HVAC maintenance schedule for headquarters building"
        }
    ]

    for c in cases:
        pdf_bytes = create_minimal_pdf(c["pdf_text"])
        with open(os.path.join(pdfs_dir, c["pdf_name"]), "wb") as f:
            f.write(pdf_bytes)

        msg = EmailMessage()
        msg['Message-ID'] = f"<{c['id']}@pharma-safety.org>"
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

    print(f"Generated {len(cases)} comprehensive benchmark synthetic cases.")

if __name__ == "__main__":
    generate()
