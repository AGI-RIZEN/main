import click
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import func, select

from app.accounts.models import User
from app.extensions import db
from app.learning.models import AwarenessFilm, Category, CyberNews
from app.phishing.models import PhishingHotspot, PhishingScenario
from app.quizzes.models import Question, QuestionOption, Quiz
from app.uploads import store_image


CATEGORY_NAMES = (
    "Phishing Awareness",
    "Password Security",
    "Social Engineering",
    "Online Banking Safety",
    "Malware Awareness",
    "Data Privacy",
    "Cybercrime Prevention",
)

QUIZ_DATA = (
    {
        "title": "DEMO · Password Basics",
        "category": "Password Security",
        "difficulty": "easy",
        "questions": (
            ("What is the safest way to reuse a password?", ("Reuse it only on trusted sites", "Use a unique password for each account", "Add a number to the same password", "Share it with a family member"), 1, "Unique passwords limit the impact of a single account breach."),
            ("Where should you store a long, unique password?", ("A password manager", "A public notes app", "An email draft", "A desk note"), 0, "A reputable password manager can store strong, unique passwords securely."),
            ("What should you do after a service reports a password breach?", ("Wait for another warning", "Change that password and any reused copies", "Delete the account email", "Post the password for advice"), 1, "Change the exposed password promptly and replace any reused passwords."),
            ("Which password is strongest?", ("Summer2026", "Password!1", "A unique, long passphrase", "Your first name and birthday"), 2, "Length and uniqueness make a passphrase harder to guess."),
            ("Should a one-time verification code be shared with a caller?", ("Yes, if they know your name", "Only with a bank caller", "No; enter it only in the service you contacted", "Yes, if the caller sounds urgent"), 2, "One-time codes are credentials. Do not disclose them to callers or messages."),
        ),
    },
    {
        "title": "DEMO · Spotting Phishing",
        "category": "Phishing Awareness",
        "difficulty": "easy",
        "questions": (
            ("A delivery text asks for an unexpected fee through a shortened link. What is safest?", ("Open the link quickly", "Visit the carrier using its official app or typed address", "Reply with your card number", "Forward it to friends"), 1, "Check delivery status through a known, official channel."),
            ("Which sender detail deserves closer inspection?", ("A familiar display name only", "A sender domain that differs subtly from the real domain", "A message with a greeting", "A company logo"), 1, "Display names and logos can be copied; inspect the full sender address."),
            ("An email says your account closes in ten minutes unless you sign in. What is the clue?", ("A company signature", "Artificial urgency and an unexpected sign-in link", "A date in the footer", "A plain-text format"), 1, "Urgency is often used to discourage careful verification."),
            ("How should you verify an unexpected account alert?", ("Use the link in the alert", "Contact support through a known official channel", "Reply to the sender", "Send a screenshot with your password"), 1, "Use a known address, phone number, or official app rather than the message link."),
            ("What is a safe response to a suspicious attachment?", ("Open it in a private window", "Enable macros if requested", "Do not open it; report or verify with the sender", "Rename it first"), 2, "Unexpected attachments can deliver malware; verify them before opening."),
        ),
    },
    {
        "title": "DEMO · Safer Web Browsing",
        "category": "Cybercrime Prevention",
        "difficulty": "easy",
        "questions": (
            ("What does HTTPS tell you?", ("The site is guaranteed legitimate", "The connection is encrypted, not that the site is trustworthy", "The page has no tracking", "The site is government-owned"), 1, "HTTPS protects the connection but does not prove a site is authentic."),
            ("A pop-up says your computer is infected and provides a phone number. What should you do?", ("Call immediately", "Install its recommended tool", "Close the page and use trusted security software", "Give remote access"), 2, "Scare pop-ups can be tech-support scams; do not call or install from them."),
            ("How should you install a browser update?", ("Use the browser's built-in updater", "Use an advertisement link", "Download an attachment", "Ask a pop-up to install it"), 0, "Use the software's own update mechanism or its official source."),
            ("What is safest when using public Wi-Fi?", ("Disable device updates", "Avoid sensitive activity on untrusted networks or use a trusted connection", "Share files with everyone", "Ignore certificate warnings"), 1, "Untrusted networks increase risk; use trusted connections and avoid ignoring warnings."),
            ("A website asks for unrelated personal information. What should you do?", ("Provide it to continue", "Pause and verify why it is needed before sharing", "Use a coworker's details", "Post it in a review"), 1, "Only provide information necessary for a legitimate, verified purpose."),
        ),
    },
    {
        "title": "DEMO · Social Engineering Defenses",
        "category": "Social Engineering",
        "difficulty": "medium",
        "questions": (
            ("A caller claiming to be IT asks for your MFA code to fix an account. What is safest?", ("Read the code to them", "Decline and contact IT through the official help desk", "Approve every prompt", "Share a screenshot"), 1, "A legitimate support team should not need your one-time authentication code."),
            ("A colleague emails an unusual request to buy gift cards urgently. What should you do?", ("Follow the request", "Verify it using a separate known communication channel", "Reply with the card codes", "Ask the email thread to confirm itself"), 1, "A separate channel helps verify the sender when an account may be compromised."),
            ("What is pretexting?", ("A scheduled software update", "A fabricated identity or story used to obtain information or access", "A type of backup", "A password manager feature"), 1, "Pretexting uses a plausible but false scenario to manipulate a target."),
            ("Why should you avoid tailgating into a secure office?", ("It slows the elevator", "Access controls must apply to each person", "Visitors cannot use doors", "It disables Wi-Fi"), 1, "Letting an unverified person follow you bypasses physical access controls."),
            ("A caller knows your public job title and asks for internal details. What is the best response?", ("Treat the caller as verified", "Share only public information", "Verify their identity and authorization independently", "Transfer them your credentials"), 2, "Public facts do not authenticate a caller or authorize access."),
        ),
    },
    {
        "title": "DEMO · Online Banking Safety",
        "category": "Online Banking Safety",
        "difficulty": "medium",
        "questions": (
            ("A message asks you to move money to a 'safe account'. What should you do?", ("Transfer immediately", "Call the bank using the number on your card or official site", "Reply with account details", "Trust the displayed caller ID"), 1, "Banks do not make safe-account transfers by unsolicited request; verify independently."),
            ("What is safest when paying a new online seller?", ("Use an irreversible payment method", "Use a protected payment method and verify the seller", "Send banking credentials", "Pay through a link in an unexpected message"), 1, "Protected payment options and seller checks reduce fraud risk."),
            ("You notice a transaction you do not recognize. What is the best first step?", ("Wait a month", "Contact your bank through its official channel promptly", "Post card details online", "Reply to the transaction alert"), 1, "Promptly report suspicious transactions using a known bank contact route."),
            ("Why should you avoid banking on a shared public computer?", ("It has a small screen", "It may retain credentials or session data", "It uses a keyboard", "It cannot display HTTPS"), 1, "Shared devices may capture or retain sensitive account information."),
            ("A caller asks you to install remote-access software to reverse a transfer. What is safest?", ("Install it and share the session code", "End the call and contact the bank independently", "Disable antivirus", "Send a one-time code"), 1, "Unsolicited remote-access requests can give a scammer control of your device."),
        ),
    },
    {
        "title": "DEMO · Malware and Device Hygiene",
        "category": "Malware Awareness",
        "difficulty": "medium",
        "questions": (
            ("What is the safest way to install an application?", ("Use its official store or publisher site", "Use a file-sharing link", "Open an email attachment", "Disable security checks"), 0, "Official sources reduce the risk of tampered software."),
            ("A document asks you to enable macros to view an invoice. What should you do?", ("Enable them immediately", "Verify the document and sender before enabling anything", "Forward it to everyone", "Rename the file"), 1, "Unexpected macro prompts can run malicious code."),
            ("Why install operating-system security updates?", ("They make passwords unnecessary", "They fix known vulnerabilities", "They guarantee no malware", "They remove the need for backups"), 1, "Updates often patch flaws attackers could otherwise exploit."),
            ("What should you do if a device shows a ransomware note?", ("Pay immediately using the note's link", "Disconnect it from networks and contact the authorized response team", "Delete every backup", "Enter more passwords"), 1, "Isolating the device can reduce spread; follow incident-response guidance."),
            ("Which backup strategy is safer against ransomware?", ("One always-connected writable drive", "A tested backup with an offline or protected copy", "A folder on the same device only", "No backups"), 1, "An offline or protected backup is less exposed to malware on the primary device."),
        ),
    },
    {
        "title": "DEMO · Data Privacy Decisions",
        "category": "Data Privacy",
        "difficulty": "hard",
        "questions": (
            ("A service requests contact access unrelated to its purpose. What is best?", ("Grant it automatically", "Decline and assess whether the permission is necessary", "Share another person's contacts", "Disable the screen lock"), 1, "Apply data minimization: grant only permissions needed for a clear purpose."),
            ("You find customer data sent to the wrong recipient. What should you do?", ("Delete the sent folder and say nothing", "Follow incident policy and report it promptly", "Forward it to your personal account", "Wait for a complaint"), 1, "Prompt reporting lets the organization contain exposure and meet its obligations."),
            ("Which is a safer way to share a sensitive file?", ("Public link with no expiry", "Approved access-controlled sharing with only intended recipients", "Personal email attachment", "Post it in a public chat"), 1, "Restrict access to authorized recipients and use approved secure tools."),
            ("Why remove location metadata before publicly sharing a photo?", ("It changes image colors", "Metadata can reveal private location details", "It blocks image viewing", "It encrypts the photo"), 1, "Image metadata can expose where or when a photo was taken."),
            ("A data request arrives from an unverified person claiming legal authority. What should you do?", ("Send the records immediately", "Use the formal verification and disclosure process", "Ask them to send a password", "Post the request publicly"), 1, "Verify authority and follow established procedures before disclosing personal data."),
        ),
    },
    {
        "title": "DEMO · Incident Response Essentials",
        "category": "Cybercrime Prevention",
        "difficulty": "hard",
        "questions": (
            ("You suspect an account is compromised. What is an appropriate first action?", ("Ignore new alerts", "Use a trusted device to secure the account and report the incident", "Reuse the suspected password", "Delete evidence"), 1, "Secure access from a trusted device and report the incident through official channels."),
            ("Why preserve suspicious messages and timestamps?", ("They make the mailbox larger", "They may help responders understand and investigate the incident", "They prove the sender is genuine", "They stop all malware"), 1, "Evidence can support incident investigation and containment."),
            ("A malware alert appears on a work device. What should an employee do?", ("Disable endpoint protection", "Follow the organization's incident process and contact IT", "Install an unknown cleaner", "Forward files to a personal device"), 1, "Use the approved response process rather than experimenting on a potentially compromised device."),
            ("What is the main purpose of incident containment?", ("Assign blame", "Limit further harm while investigation and recovery proceed", "Publish user data", "Avoid notifying responders"), 1, "Containment reduces ongoing impact while preserving a path to recovery."),
            ("Why should an organization test its backups?", ("Testing is unnecessary if a backup exists", "A restore test checks that data can actually be recovered", "It replaces access controls", "It makes every incident harmless"), 1, "A successful restore test verifies that the backup is usable."),
        ),
    },
)

PHISHING_DATA = (
    {
        "title": "DEMO · Fake banking security alert",
        "category": "Online Banking Safety",
        "difficulty": "easy",
        "site": "Northstar Bank",
        "legitimate_host": "secure.northstar.example",
        "phishing_host": "northstar-security.example",
        "message": "Unusual sign-in detected. Verify through the official app.",
        "phishing_message": "URGENT: Verify now or access will be suspended.",
        "hotspots": (
            ("Look-alike web address", 8, 7, 84, 11, "The address uses an unexpected security-themed domain. Open the bank app or type its known address instead.", 10),
            ("Urgent account threat", 8, 41, 84, 15, "The simulated page pressures the reader to act immediately. Verify alerts through a known bank channel.", 10),
        ),
    },
    {
        "title": "DEMO · Parcel delivery fee notice",
        "category": "Phishing Awareness",
        "difficulty": "easy",
        "site": "ParcelPost",
        "legitimate_host": "tracking.parcelpost.example",
        "phishing_host": "parcelpost-fee.example",
        "message": "Track a parcel using the carrier's official reference.",
        "phishing_message": "Delivery paused. Pay a small fee within 2 hours.",
        "hotspots": (
            ("Unexpected payment request", 8, 7, 84, 11, "The sender asks for an unanticipated fee. Check delivery status using the carrier's official site or app.", 10),
            ("Artificial deadline", 8, 41, 84, 15, "The short deadline creates pressure. Do not follow payment links in unexpected delivery messages.", 10),
        ),
    },
    {
        "title": "DEMO · Social account warning",
        "category": "Social Engineering",
        "difficulty": "medium",
        "site": "CircleSquare",
        "legitimate_host": "accounts.circlesquare.example",
        "phishing_host": "circlesquare-help.example",
        "message": "Review account notices in the official application.",
        "phishing_message": "A complaint will close your profile unless you appeal now.",
        "hotspots": (
            ("Unfamiliar sign-in address", 8, 7, 84, 11, "The host is not the known service domain. Navigate using the official app rather than this page.", 10),
            ("Threatening account message", 8, 41, 84, 15, "A threat of immediate closure is intended to rush the reader into disclosing credentials.", 10),
        ),
    },
    {
        "title": "DEMO · Unverified job offer",
        "category": "Cybercrime Prevention",
        "difficulty": "medium",
        "site": "BrightPath Careers",
        "legitimate_host": "careers.brightpath.example",
        "phishing_host": "brightpath-fastoffer.example",
        "message": "Confirm an interview through the employer's verified careers page.",
        "phishing_message": "Pay a processing fee to secure this remote position.",
        "hotspots": (
            ("Look-alike recruiting host", 8, 7, 84, 11, "The host is not the fictional employer's expected careers address. Verify the vacancy independently.", 10),
            ("Up-front payment demand", 8, 41, 84, 15, "A request to pay a fee to secure a job is a warning sign. Do not send money or identity documents without verification.", 10),
        ),
    },
    {
        "title": "DEMO · Password reset notification",
        "category": "Password Security",
        "difficulty": "hard",
        "site": "CloudNotes",
        "legitimate_host": "account.cloudnotes.example",
        "phishing_host": "cloudnotes-reset.example",
        "message": "If you did not request a reset, open the service directly.",
        "phishing_message": "Your password expires today. Confirm old password to keep access.",
        "hotspots": (
            ("Unexpected reset domain", 8, 7, 84, 11, "The page uses a different host. Go directly to the real service rather than following an email link.", 10),
            ("Requests current password", 8, 41, 84, 15, "An unexpected page asking for an old password is suspicious. Never enter credentials on an unverified page.", 10),
        ),
    },
)

DEMO_NEWS = (
    {
        "slug": "fictional-parcel-message",
        "title": "DEMO ONLY: Fictional parcel-message awareness example",
        "category": "Phishing Awareness",
        "summary": "This fictional demonstration describes a made-up parcel message asking for an unexpected fee. It is not a report of a real campaign or current event.",
        "tips": "- Check delivery status through the carrier's official app.\n- Avoid payment links in unexpected messages.",
    },
    {
        "slug": "fictional-account-alert",
        "title": "DEMO ONLY: Fictional account-alert awareness example",
        "category": "Cybercrime Prevention",
        "summary": "This fictional demonstration describes a made-up account warning designed to create urgency. It does not describe a real breach or real organization.",
        "tips": "- Verify account alerts by signing in through a known official route.\n- Do not share one-time codes with callers or messages.",
    },
    {
        "slug": "fictional-password-notice",
        "title": "DEMO ONLY: Fictional password-notice awareness example",
        "category": "Password Security",
        "summary": "This fictional demonstration shows why an unexpected password-expiry link should be checked independently. It is not current real-world news.",
        "tips": "- Open the service directly instead of using an unexpected link.\n- Use unique passwords and a trusted password manager.",
    },
)


def _category_by_name(name):
    category = db.session.scalar(
        select(Category).where(func.lower(Category.category_name) == name.lower())
    )
    if category is None:
        category = Category(category_name=name, description="Cyber awareness learning category.")
        db.session.add(category)
        db.session.flush()
    return category


def _font(size):
    return ImageFont.load_default(size=size)


def _screenshot(site, host, message, suspicious=False):
    image = Image.new("RGB", (1200, 700), "#f4f7fb")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 1200, 70), fill="#e1e7ef")
    draw.ellipse((18, 24, 34, 40), fill="#bd5555" if suspicious else "#54a36f")
    draw.ellipse((43, 24, 59, 40), fill="#d2a24d")
    draw.ellipse((68, 24, 84, 40), fill="#54a36f")
    draw.rounded_rectangle((160, 14, 1080, 54), radius=12, fill="#ffffff", outline="#bbc6d5", width=2)
    draw.text((184, 23), f"https://{host}/account", fill="#842929" if suspicious else "#34445b", font=_font(24))
    draw.rectangle((0, 70, 1200, 145), fill="#17375e")
    draw.text((60, 92), site, fill="#ffffff", font=_font(32))
    draw.rounded_rectangle((100, 190, 1100, 610), radius=18, fill="#ffffff", outline="#d5deea", width=2)
    draw.text((150, 225), f"{site} account notice", fill="#172b4d", font=_font(34))
    banner_color = "#9c3434" if suspicious else "#e8f4ec"
    text_color = "#ffffff" if suspicious else "#245b3e"
    draw.rounded_rectangle((150, 290, 1050, 390), radius=12, fill=banner_color)
    draw.text((185, 322), message, fill=text_color, font=_font(24))
    draw.text((150, 425), "Review account information only through a verified service.", fill="#52627a", font=_font(22))
    draw.rounded_rectangle((150, 495, 420, 555), radius=10, fill="#2058a4")
    draw.text((195, 514), "Continue safely", fill="#ffffff", font=_font(22))
    draw.text((150, 640), "FICTIONAL DEMO SCREENSHOT - no real service or credentials", fill="#62718a", font=_font(18))
    return image


def _make_film_thumbnail(title):
    image = Image.new("RGB", (800, 450), "#17375e")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((35, 35, 765, 415), radius=24, outline="#8fb9ed", width=4)
    draw.text((70, 75), "DEMO PLACEHOLDER", fill="#b9d6f7", font=_font(28))
    draw.text((70, 160), title[:44], fill="#ffffff", font=_font(36))
    draw.text((70, 330), "Replace with a verified educational video before publishing.", fill="#dce8f7", font=_font(22))
    return image


def seed_demo_data():
    admin = db.session.scalar(
        select(User)
        .where(User.role == "admin", User.status == "active")
        .order_by(User.user_id)
    )
    if admin is None:
        raise click.ClickException(
            "Create an active administrator first with the create-admin command."
        )

    categories = {name: _category_by_name(name) for name in CATEGORY_NAMES}
    for quiz_data in QUIZ_DATA:
        existing = db.session.scalar(
            select(Quiz).where(Quiz.quiz_title == quiz_data["title"])
        )
        if existing:
            continue
        quiz = Quiz(
            category=categories[quiz_data["category"]],
            quiz_title=quiz_data["title"],
            description="Clearly labeled seed content for local project demonstration.",
            difficulty=quiz_data["difficulty"],
            total_questions=len(quiz_data["questions"]),
            passing_percentage=60,
            duration_minutes=10,
            status="published",
            is_demo=True,
            created_by=admin.user_id,
        )
        for prompt, options, correct_index, explanation in quiz_data["questions"]:
            question = Question(question_text=prompt, explanation=explanation, marks=1)
            question.options = [
                QuestionOption(option_text=option, is_correct=index == correct_index)
                for index, option in enumerate(options)
            ]
            quiz.questions.append(question)
        db.session.add(quiz)

    for scenario_data in PHISHING_DATA:
        existing = db.session.scalar(
            select(PhishingScenario).where(
                PhishingScenario.scenario_title == scenario_data["title"]
            )
        )
        if existing:
            continue
        original = _screenshot(
            scenario_data["site"],
            scenario_data["legitimate_host"],
            scenario_data["message"],
        )
        simulated = _screenshot(
            scenario_data["site"],
            scenario_data["phishing_host"],
            scenario_data["phishing_message"],
            suspicious=True,
        )
        scenario = PhishingScenario(
            category=categories[scenario_data["category"]],
            scenario_title=scenario_data["title"],
            description="Fictional screenshot-only awareness simulation. Never enter real credentials.",
            original_image=store_image(original, "phishing"),
            phishing_image=store_image(simulated, "phishing"),
            difficulty=scenario_data["difficulty"],
            total_hotspots=len(scenario_data["hotspots"]),
            status="active",
            created_by=admin.user_id,
        )
        for title, x, y, width, height, explanation, points in scenario_data["hotspots"]:
            scenario.hotspots.append(
                PhishingHotspot(
                    hotspot_title=title,
                    x_position=x,
                    y_position=y,
                    width=width,
                    height=height,
                    explanation=explanation,
                    points=points,
                )
            )
        db.session.add(scenario)

    film_placeholders = (
        (
            "[DEMO PLACEHOLDER] Verify before you click",
            "Inactive placeholder. Add a verified public educational video URL before publishing.",
            "Phishing Awareness",
        ),
        (
            "[DEMO PLACEHOLDER] Protecting account access",
            "Inactive placeholder. Add a verified public educational video URL before publishing.",
            "Password Security",
        ),
    )
    for title, description, category_name in film_placeholders:
        existing = db.session.scalar(
            select(AwarenessFilm).where(AwarenessFilm.film_title == title)
        )
        if existing:
            continue
        thumbnail = store_image(_make_film_thumbnail(title), "films")
        db.session.add(
            AwarenessFilm(
                category=categories[category_name],
                film_title=title,
                description=description,
                video_url="https://video.example.invalid/review-required",
                thumbnail=thumbnail,
                duration=None,
                status="inactive",
                uploaded_by=admin.user_id,
            )
        )

    for news_data in DEMO_NEWS:
        article_url = f"https://example.invalid/demo-news/{news_data['slug']}"
        existing = db.session.scalar(
            select(CyberNews).where(CyberNews.article_url == article_url)
        )
        if existing:
            continue
        db.session.add(
            CyberNews(
                category=categories[news_data["category"]],
                title=news_data["title"],
                source="DEMO DATA — Fictional Example",
                article_url=article_url,
                description="Fictional training content. It is not a real news article.",
                published_at=None,
                summary=news_data["summary"],
                safety_tips=news_data["tips"],
                status="published",
                is_demo=True,
            )
        )

    db.session.commit()
    return {
        "categories": len(CATEGORY_NAMES),
        "quizzes": len(QUIZ_DATA),
        "scenarios": len(PHISHING_DATA),
        "films": len(film_placeholders),
        "news": len(DEMO_NEWS),
    }
