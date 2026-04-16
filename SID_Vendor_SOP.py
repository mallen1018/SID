#!/usr/bin/env python3
"""Generate SID Vendor SOP PDF using reportlab."""

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether, ListFlowable, ListItem
)

OUTPUT = "/sessions/friendly-inspiring-brahmagupta/mnt/SID_Extension_v55_upload/SID_Vendor_SOP.pdf"

# Colors
NAVY = HexColor("#1a3a5c")
BLUE = HexColor("#2a6496")
LIGHT_BLUE = HexColor("#e8f0fa")
ACCENT = HexColor("#3b82f6")
DARK = HexColor("#222222")
GRAY = HexColor("#555555")
LIGHT_GRAY = HexColor("#f5f5f5")
WHITE = HexColor("#ffffff")
GREEN = HexColor("#16a34a")
RED = HexColor("#dc2626")
AMBER = HexColor("#d97706")

styles = getSampleStyleSheet()

# Custom styles
styles.add(ParagraphStyle(
    'DocTitle', parent=styles['Title'],
    fontSize=26, leading=32, textColor=NAVY,
    spaceAfter=6, alignment=TA_CENTER, fontName='Helvetica-Bold'
))
styles.add(ParagraphStyle(
    'DocSubtitle', parent=styles['Normal'],
    fontSize=12, leading=16, textColor=GRAY,
    spaceAfter=20, alignment=TA_CENTER
))
styles.add(ParagraphStyle(
    'SectionHead', parent=styles['Heading1'],
    fontSize=16, leading=20, textColor=NAVY,
    spaceBefore=20, spaceAfter=10, fontName='Helvetica-Bold',
    borderPadding=(0, 0, 4, 0)
))
styles.add(ParagraphStyle(
    'SubHead', parent=styles['Heading2'],
    fontSize=13, leading=17, textColor=BLUE,
    spaceBefore=14, spaceAfter=6, fontName='Helvetica-Bold'
))
styles.add(ParagraphStyle(
    'Body', parent=styles['Normal'],
    fontSize=10.5, leading=15, textColor=DARK,
    spaceAfter=6
))
styles.add(ParagraphStyle(
    'BodyBold', parent=styles['Normal'],
    fontSize=10.5, leading=15, textColor=DARK,
    spaceAfter=6, fontName='Helvetica-Bold'
))
styles.add(ParagraphStyle(
    'StepNum', parent=styles['Normal'],
    fontSize=11, leading=15, textColor=WHITE,
    fontName='Helvetica-Bold', alignment=TA_CENTER
))
styles.add(ParagraphStyle(
    'StepText', parent=styles['Normal'],
    fontSize=10.5, leading=15, textColor=DARK,
    spaceAfter=4
))
styles.add(ParagraphStyle(
    'Note', parent=styles['Normal'],
    fontSize=9.5, leading=13, textColor=GRAY,
    leftIndent=12, spaceAfter=4
))
styles.add(ParagraphStyle(
    'Footer', parent=styles['Normal'],
    fontSize=8, leading=10, textColor=GRAY,
    alignment=TA_CENTER
))
styles.add(ParagraphStyle(
    'TOCEntry', parent=styles['Normal'],
    fontSize=11, leading=18, textColor=BLUE,
    leftIndent=20, spaceAfter=2
))
styles.add(ParagraphStyle(
    'ImportantBox', parent=styles['Normal'],
    fontSize=10.5, leading=15, textColor=HexColor("#92400e"),
    backColor=HexColor("#fef3c7"), borderPadding=10,
    spaceAfter=10, spaceBefore=6
))


def hr():
    return HRFlowable(width="100%", thickness=1, color=HexColor("#dddddd"), spaceAfter=8, spaceBefore=8)

def section_hr():
    return HRFlowable(width="100%", thickness=2, color=ACCENT, spaceAfter=4, spaceBefore=2)

def numbered_step(num, text):
    """Create a styled numbered step with a circle badge."""
    circle_style = ParagraphStyle(
        f'circle{num}', parent=styles['Normal'],
        fontSize=10, leading=14, textColor=WHITE,
        fontName='Helvetica-Bold', alignment=TA_CENTER
    )
    text_style = styles['StepText']
    data = [[Paragraph(str(num), circle_style), Paragraph(text, text_style)]]
    t = Table(data, colWidths=[0.35*inch, 6.3*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), ACCENT),
        ('ROUNDEDCORNERS', [8, 8, 8, 8]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (0, 0), 0),
        ('RIGHTPADDING', (0, 0), (0, 0), 8),
        ('TOPPADDING', (0, 0), (0, 0), 2),
        ('BOTTOMPADDING', (0, 0), (0, 0), 2),
        ('LEFTPADDING', (1, 0), (1, 0), 8),
        ('TOPPADDING', (1, 0), (1, 0), 1),
    ]))
    return t

def important_box(text):
    """Create a highlighted important/warning box."""
    data = [[Paragraph(f"<b>IMPORTANT:</b> {text}", styles['ImportantBox'])]]
    t = Table(data, colWidths=[6.5*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), HexColor("#fef3c7")),
        ('BOX', (0, 0), (0, 0), 1, AMBER),
        ('LEFTPADDING', (0, 0), (0, 0), 12),
        ('RIGHTPADDING', (0, 0), (0, 0), 12),
        ('TOPPADDING', (0, 0), (0, 0), 8),
        ('BOTTOMPADDING', (0, 0), (0, 0), 8),
    ]))
    return t

def tip_box(text):
    """Create a tip box."""
    tip_style = ParagraphStyle(
        'TipText', parent=styles['Normal'],
        fontSize=10, leading=14, textColor=HexColor("#065f46"),
    )
    data = [[Paragraph(f"<b>TIP:</b> {text}", tip_style)]]
    t = Table(data, colWidths=[6.5*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), HexColor("#ecfdf5")),
        ('BOX', (0, 0), (0, 0), 1, GREEN),
        ('LEFTPADDING', (0, 0), (0, 0), 12),
        ('RIGHTPADDING', (0, 0), (0, 0), 12),
        ('TOPPADDING', (0, 0), (0, 0), 8),
        ('BOTTOMPADDING', (0, 0), (0, 0), 8),
    ]))
    return t

def bullet_list(items):
    """Create a bullet list from a list of strings."""
    return ListFlowable(
        [ListItem(Paragraph(item, styles['Body']), bulletColor=ACCENT) for item in items],
        bulletType='bullet',
        bulletFontSize=8,
        leftIndent=20,
        spaceBefore=4,
        spaceAfter=8
    )


def add_page_number(canvas, doc):
    """Add page number footer."""
    canvas.saveState()
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(GRAY)
    canvas.drawCentredString(letter[0] / 2, 0.5 * inch,
        f"SID - Smart Indeed Downloader  |  Vendor SOP  |  Page {doc.page}")
    canvas.restoreState()


def build():
    doc = SimpleDocTemplate(
        OUTPUT, pagesize=letter,
        topMargin=0.75*inch, bottomMargin=0.75*inch,
        leftMargin=0.85*inch, rightMargin=0.85*inch
    )
    story = []

    # ===== COVER / TITLE =====
    story.append(Spacer(1, 1.2*inch))
    story.append(Paragraph("SID - Smart Indeed Downloader", styles['DocTitle']))
    story.append(Paragraph("Vendor Standard Operating Procedure (SOP)", styles['DocSubtitle']))
    story.append(hr())
    story.append(Spacer(1, 0.3*inch))

    # Info table
    info_data = [
        ["Document Type:", "Standard Operating Procedure"],
        ["Version:", "1.0"],
        ["Effective Date:", "March 2026"],
        ["Prepared By:", "Melissa Allen"],
        ["Contact:", "mallen10185@gmail.com"],
        ["Confidentiality:", "For authorized vendors only"],
    ]
    info_style = ParagraphStyle('InfoVal', parent=styles['Body'], fontSize=10.5, textColor=DARK)
    info_label = ParagraphStyle('InfoLabel', parent=styles['Body'], fontSize=10.5, textColor=GRAY, fontName='Helvetica-Bold')
    info_table_data = [[Paragraph(r[0], info_label), Paragraph(r[1], info_style)] for r in info_data]
    info_t = Table(info_table_data, colWidths=[1.8*inch, 4.5*inch])
    info_t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, HexColor("#eeeeee")),
    ]))
    story.append(info_t)

    story.append(Spacer(1, 0.5*inch))

    # Table of Contents
    story.append(Paragraph("Table of Contents", styles['SectionHead']))
    story.append(section_hr())
    toc_items = [
        "1. Purpose and Scope",
        "2. Installing the SID Extension",
        "3. Using SID to Download Resumes",
        "4. Daily File Submission Process",
        "5. File Naming and Organization",
        "6. Troubleshooting",
        "7. Expectations and Deadlines",
        "8. Contact and Support",
    ]
    for item in toc_items:
        story.append(Paragraph(item, styles['TOCEntry']))
    story.append(PageBreak())

    # ===== SECTION 1: PURPOSE =====
    story.append(Paragraph("1. Purpose and Scope", styles['SectionHead']))
    story.append(section_hr())
    story.append(Paragraph(
        "This Standard Operating Procedure provides step-by-step instructions for vendors who use the "
        "<b>SID - Smart Indeed Downloader</b> Chrome extension. SID automates the process of downloading "
        "candidate resumes and data from the Indeed employer dashboard.",
        styles['Body']
    ))
    story.append(Paragraph(
        "This document covers how to install the extension, how to use it on a daily basis, and how to "
        "submit the downloaded resume files to Melissa Allen each day.",
        styles['Body']
    ))
    story.append(Spacer(1, 6))
    story.append(Paragraph("<b>Who this is for:</b> All vendors who have been given access to the SID extension and are responsible for downloading resumes from Indeed.", styles['Body']))
    story.append(Spacer(1, 12))

    # ===== SECTION 2: INSTALLATION =====
    story.append(Paragraph("2. Installing the SID Extension", styles['SectionHead']))
    story.append(section_hr())
    story.append(Paragraph("SID is available as a Chrome extension. It also works on Microsoft Edge since Edge supports Chrome extensions.", styles['Body']))
    story.append(Spacer(1, 6))

    story.append(Paragraph("2.1  Requirements", styles['SubHead']))
    story.append(bullet_list([
        "Google Chrome (recommended) or Microsoft Edge browser",
        "An active Indeed employer account with candidate access",
        "The SID extension install link (provided by Melissa)"
    ]))

    story.append(Paragraph("2.2  Installation Steps", styles['SubHead']))
    story.append(numbered_step(1, "Open the <b>SID install link</b> that Melissa provided to you in Chrome or Edge."))
    story.append(Spacer(1, 4))
    story.append(numbered_step(2, 'Click the <b>"Add to Chrome"</b> button on the Chrome Web Store page.'))
    story.append(Spacer(1, 4))
    story.append(numbered_step(3, 'A popup will appear asking for permissions. Click <b>"Add extension"</b> to confirm.'))
    story.append(Spacer(1, 4))
    story.append(numbered_step(4, "You will see a confirmation message that SID has been added to your browser. That's it \u2014 no further setup needed."))
    story.append(Spacer(1, 4))
    story.append(numbered_step(5, 'Navigate to <b>employers.indeed.com</b> and log in. The SID panel will appear automatically on any Indeed employer page.'))
    story.append(Spacer(1, 10))
    story.append(tip_box("Edge users: you can install Chrome extensions directly. Just open the same link in Edge and click \"Add to Chrome\" \u2014 it works the same way."))
    story.append(Spacer(1, 12))

    # ===== SECTION 3: USING SID =====
    story.append(Paragraph("3. Using SID to Download Resumes", styles['SectionHead']))
    story.append(section_hr())
    story.append(Paragraph(
        "Once installed, SID adds a floating panel to the Indeed employer dashboard. This panel is your "
        "control center for downloading resumes.",
        styles['Body']
    ))
    story.append(Spacer(1, 6))

    story.append(Paragraph("3.1  Starting a Download", styles['SubHead']))
    story.append(numbered_step(1, 'Log into <b>employers.indeed.com</b> and navigate to the <b>Candidates</b> page for the job you want to process.'))
    story.append(Spacer(1, 4))
    story.append(numbered_step(2, 'You will see the <b>SID panel</b> floating in the corner of the page. It will show "Ready" status.'))
    story.append(Spacer(1, 4))
    story.append(numbered_step(3, 'Click the green <b>"Start"</b> button. SID will begin scanning candidates and downloading their resumes automatically.'))
    story.append(Spacer(1, 4))
    story.append(numbered_step(4, 'The panel shows real-time progress: how many candidates have been processed, how many were skipped (no resume available), and an estimated time remaining.'))
    story.append(Spacer(1, 4))
    story.append(numbered_step(5, 'When processing is complete, the status will update to show the final count. A <b>"Download Zip"</b> button will appear.'))
    story.append(Spacer(1, 10))

    story.append(Paragraph("3.2  Downloading Your Files", styles['SubHead']))
    story.append(Paragraph("After SID finishes processing candidates, you have two download options:", styles['Body']))
    story.append(Spacer(1, 4))

    dl_data = [
        [Paragraph("<b>Button</b>", styles['BodyBold']), Paragraph("<b>What It Does</b>", styles['BodyBold'])],
        [Paragraph("Download Zip", styles['Body']), Paragraph("Downloads a ZIP file containing all resumes for the <b>current job</b>, plus a CSV spreadsheet with candidate details (name, email, phone, location, etc.).", styles['Body'])],
        [Paragraph("Download All Today", styles['Body']), Paragraph("Downloads a single ZIP containing resumes and CSVs for <b>all jobs you processed today</b>. Includes a master CSV with every candidate across all jobs, with duplicates removed.", styles['Body'])],
    ]
    dl_table = Table(dl_data, colWidths=[1.5*inch, 5.0*inch])
    dl_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), LIGHT_BLUE),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(dl_table)
    story.append(Spacer(1, 10))

    story.append(Paragraph("3.3  Pausing and Resuming", styles['SubHead']))
    story.append(bullet_list([
        'Click <b>"Stop"</b> at any time to pause SID. It will finish the current candidate and then stop.',
        'Click <b>"Resume"</b> to continue where you left off. SID remembers which candidates have already been processed.',
        'If you navigate to a different job, SID automatically resets for the new job while keeping your previous job\'s data accessible via the <b>"Job History"</b> button.',
    ]))

    story.append(Paragraph("3.4  Job History", styles['SubHead']))
    story.append(Paragraph(
        'Click the <b>"Job History"</b> button at the bottom of the SID panel to see all jobs you\'ve processed. '
        'Click any job in the list to re-download its ZIP file.',
        styles['Body']
    ))
    story.append(Spacer(1, 6))
    story.append(important_box(
        "SID stores resume data in your browser's local storage. If you clear your browser data or switch computers, "
        "your history will be lost. Always download your ZIP files before clearing browser data."
    ))
    story.append(Spacer(1, 6))

    story.append(Paragraph("3.5  Repeat for Each Job Posting", styles['SubHead']))
    story.append(Paragraph(
        "If you manage multiple job postings, navigate to each job's Candidates page and repeat the process. "
        'SID tracks each job separately. At the end of the day, use <b>"Download All Today"</b> to get everything in one ZIP.',
        styles['Body']
    ))

    story.append(PageBreak())

    # ===== SECTION 4: DAILY FILE UPLOAD =====
    story.append(Paragraph("4. Daily File Upload", styles['SectionHead']))
    story.append(section_hr())
    story.append(Paragraph(
        "After running SID and downloading your ZIP file, you need to upload it to the <b>vendor portal</b> the same day. "
        "Melissa gets notified automatically when you upload.",
        styles['Body']
    ))
    story.append(Spacer(1, 6))

    story.append(Paragraph("<b>How to Upload:</b>", styles['BodyBold']))
    story.append(numbered_step(1, "Go to the <b>vendor portal</b> and scroll down to the <b>Upload Your ZIP Files</b> section."))
    story.append(Spacer(1, 4))
    story.append(numbered_step(2, "Enter your <b>name</b> and <b>email</b> in the form fields."))
    story.append(Spacer(1, 4))
    story.append(numbered_step(3, "<b>Drag & drop</b> your ZIP file into the upload area, or click it to browse for the file."))
    story.append(Spacer(1, 4))
    story.append(numbered_step(4, 'Click <b>"Upload Files"</b> and wait for it to finish. Melissa gets notified automatically.'))
    story.append(Spacer(1, 10))

    story.append(important_box(
        "Do <b>not</b> unzip the file before uploading. Upload the .zip file as-is. "
        "Also, do <b>not</b> rename it \u2014 the file already includes the date."
    ))
    story.append(Spacer(1, 10))

    story.append(tip_box(
        "Upload once at the end of your shift after all jobs are done. "
        'Use <b>"Download All Today"</b> to get one ZIP with everything, then upload that single file.'
    ))

    story.append(PageBreak())

    # ===== SECTION 5: FILE NAMING =====
    story.append(Paragraph("5. File Naming and Organization", styles['SectionHead']))
    story.append(section_hr())
    story.append(Paragraph(
        "SID automatically names files in a structured format. <b>Do not rename the ZIP files or their contents.</b> "
        "The naming convention helps Melissa track and organize resumes efficiently.",
        styles['Body']
    ))
    story.append(Spacer(1, 6))

    story.append(Paragraph("5.1  ZIP File Structure", styles['SubHead']))
    story.append(Paragraph("When you click <b>\"Download All Today\"</b>, the ZIP file contains:", styles['Body']))
    story.append(Spacer(1, 4))

    struct_data = [
        [Paragraph("<b>Folder / File</b>", styles['BodyBold']), Paragraph("<b>Contents</b>", styles['BodyBold'])],
        [Paragraph("<b>Resumes/</b>", styles['Body']), Paragraph("All candidate resume PDFs, named with candidate name and metadata (city, state, email, phone).", styles['Body'])],
        [Paragraph("<b>CSV/</b>", styles['Body']), Paragraph("One CSV per job posting with detailed candidate information (name, email, phone, location, job title, company, date applied, source, resume filename).", styles['Body'])],
        [Paragraph("Master CSV", styles['Body']), Paragraph("A combined CSV at the root level with all unique candidates across every job, with duplicates removed.", styles['Body'])],
    ]
    struct_table = Table(struct_data, colWidths=[1.5*inch, 5.0*inch])
    struct_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), LIGHT_BLUE),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(struct_table)
    story.append(Spacer(1, 10))

    story.append(Paragraph("5.2  Resume Filename Format", styles['SubHead']))
    story.append(Paragraph(
        "Each resume PDF is automatically named using this pattern:",
        styles['Body']
    ))
    story.append(Spacer(1, 4))
    fmt_data = [[Paragraph(
        '<font face="Courier" size="10"><b>Firstname_Lastname{City,ST,Zip,email,,phone}.pdf</b></font>',
        styles['Body']
    )]]
    fmt_table = Table(fmt_data, colWidths=[6.5*inch])
    fmt_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), LIGHT_GRAY),
        ('BOX', (0, 0), (0, 0), 0.5, HexColor("#cccccc")),
        ('LEFTPADDING', (0, 0), (0, 0), 12),
        ('TOPPADDING', (0, 0), (0, 0), 8),
        ('BOTTOMPADDING', (0, 0), (0, 0), 8),
    ]))
    story.append(fmt_table)
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "This metadata in the filename makes it easy to identify candidates without opening each file. "
        "<b>Do not rename these files.</b>",
        styles['Body']
    ))
    story.append(Spacer(1, 12))

    # ===== SECTION 6: TROUBLESHOOTING =====
    story.append(Paragraph("6. Troubleshooting", styles['SectionHead']))
    story.append(section_hr())

    issues = [
        ["SID panel doesn't appear", "Make sure you are on <b>employers.indeed.com</b> (not indeed.com). The panel only loads on the employer dashboard. Try refreshing the page. If it still doesn't appear, check that the extension is enabled by going to <b>chrome://extensions</b>."],
        ["\"Start\" button does nothing", "Make sure you are on a Candidates page for a specific job. SID needs to detect candidates on the page to begin processing."],
        ["Progress stuck or very slow", 'SID processes one candidate at a time with brief pauses to avoid overloading Indeed. If it\'s stuck for more than 2 minutes, click <b>"Stop"</b> and then <b>"Resume"</b>.'],
        ["Many candidates \"skipped\"", "Skipped candidates typically don't have a resume on file with Indeed. This is normal. SID shows skipped candidates in the panel so you can review them."],
        ["ZIP file won't download", "Check your browser's download settings. Make sure Chrome isn't blocking the download. Try disabling any ad-blocker extensions temporarily."],
        ["Extension disabled after Chrome update", "Chrome occasionally disables extensions after major updates. Go to <b>chrome://extensions</b>, find SID, and toggle it back on."],
        ["\"Download All Today\" shows 0 jobs", "This means no jobs were processed today. The button only bundles jobs processed in the current day (Eastern time). Make sure you ran SID before trying to download."],
    ]

    for issue in issues:
        story.append(Paragraph(f'<b>Problem:</b> {issue[0]}', styles['Body']))
        story.append(Paragraph(f'<b>Solution:</b> {issue[1]}', styles['Note']))
        story.append(Spacer(1, 6))

    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "If none of the above solutions work, contact Melissa with a screenshot of the issue and a description of what happened.",
        styles['Body']
    ))

    story.append(PageBreak())

    # ===== SECTION 7: EXPECTATIONS =====
    story.append(Paragraph("7. Expectations and Deadlines", styles['SectionHead']))
    story.append(section_hr())

    story.append(Paragraph("7.1  Daily Requirements", styles['SubHead']))
    story.append(bullet_list([
        "Run SID for <b>every active job posting</b> assigned to you, every business day.",
        'Use <b>"Download All Today"</b> at the end of each day to create one combined ZIP.',
        "Upload the ZIP to the vendor portal <b>by end of day</b>.",
    ]))

    story.append(Paragraph("7.2  Quality Checks", styles['SubHead']))
    story.append(Paragraph("Before uploading, do a quick sanity check:", styles['Body']))
    story.append(bullet_list([
        "Open the ZIP and verify it contains the <b>Resumes</b> folder and <b>CSV</b> folder.",
        "Spot-check that resume PDFs open correctly (open 2-3 random files).",
        "Check that the CSV files contain data (not empty).",
    ]))

    story.append(Paragraph("7.3  What to Do If You Can't Complete Your Daily Download", styles['SubHead']))
    story.append(bullet_list([
        "If Indeed is down or SID encounters a major error, notify Melissa immediately.",
        "If you will be unavailable, notify Melissa <b>at least 24 hours in advance</b> so coverage can be arranged.",
        "If you miss a day, run SID the next business day \u2014 it will pick up any new candidates that appeared.",
    ]))

    story.append(Spacer(1, 12))

    # ===== SECTION 8: CONTACT =====
    story.append(Paragraph("8. Contact and Support", styles['SectionHead']))
    story.append(section_hr())

    contact_data = [
        [Paragraph("<b>For</b>", styles['BodyBold']), Paragraph("<b>Contact</b>", styles['BodyBold'])],
        [Paragraph("Technical issues with SID", styles['Body']), Paragraph("Email Melissa at <b>mallen10185@gmail.com</b> with a screenshot and description of the problem.", styles['Body'])],
        [Paragraph("File submission questions", styles['Body']), Paragraph("Email Melissa at <b>mallen10185@gmail.com</b>.", styles['Body'])],
        [Paragraph("Time off / scheduling", styles['Body']), Paragraph("Notify Melissa at least 24 hours in advance via email or text.", styles['Body'])],
        [Paragraph("Extension updates", styles['Body']), Paragraph("SID updates automatically through the Chrome Web Store. No action needed from you.", styles['Body'])],
    ]
    contact_table = Table(contact_data, colWidths=[2.0*inch, 4.5*inch])
    contact_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), LIGHT_BLUE),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(contact_table)

    story.append(Spacer(1, 0.5*inch))
    story.append(hr())
    story.append(Paragraph(
        "By following this SOP, you help ensure that candidate data is collected accurately and delivered "
        "on time every day. Thank you for your diligence and partnership.",
        styles['Body']
    ))
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph(
        "<i>This document is confidential and intended for authorized vendors only. "
        "Do not share this document or the SID extension link with unauthorized parties.</i>",
        styles['Note']
    ))

    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    print(f"PDF created: {OUTPUT}")


if __name__ == "__main__":
    build()
