from app.accounts.models import User
from app.extensions import db
from app.learning.models import Infographic, Poster

POSTER_SEED = (
    {
        "tone": "p1",
        "icon": "\U0001F511",
        "title_en": "The Same Key Opens Every Lock",
        "tips_en": (
            "A password reused across apps is one leak away from opening all of them.\n"
            "Give every important account its own password.\n"
            "Use a password manager so unique passwords stay easy."
        ),
        "title_hi": "एक ही चाबी हर ताला नहीं खोलनी चाहिए",
        "tips_hi": (
            "एक पासवर्ड कई जगह इस्तेमाल करना मतलब एक सेंध से सब कुछ खुल जाना।\n"
            "हर ज़रूरी अकाउंट का पासवर्ड अलग रखें।\n"
            "पासवर्ड मैनेजर का इस्तेमाल करें ताकि अलग पासवर्ड रखना आसान हो।"
        ),
    },
    {
        "tone": "p2",
        "icon": "⏳",
        "title_en": "Urgency Is the Oldest Trick in the Book",
        "tips_en": (
            "Scammers manufacture a deadline so you act before you think.\n"
            "A real deadline survives a five-minute pause to verify it.\n"
            "Call back on a number you already trust, not one in the message."
        ),
        "title_hi": "जल्दबाज़ी, ठगी की सबसे पुरानी चाल है",
        "tips_hi": (
            "ठग एक नकली डेडलाइन बनाते हैं ताकि आप सोचने से पहले काम कर बैठें।\n"
            "असली डेडलाइन पांच मिनट रुककर जांचने से नहीं बदलती।\n"
            "संदेश में दिए नंबर पर नहीं, अपने भरोसेमंद नंबर पर कॉल करें।"
        ),
    },
    {
        "tone": "p3",
        "icon": "\U0001F4F2",
        "title_en": "One Tap Doesn't Need Your Whole Life",
        "tips_en": (
            "An app asking for contacts, camera, or location should explain why.\n"
            "Review permissions you've already granted, not just new ones.\n"
            "Remove access from apps you no longer open."
        ),
        "title_hi": "एक टैप को आपकी पूरी ज़िंदगी नहीं चाहिए",
        "tips_hi": (
            "कॉन्टैक्ट्स, कैमरा या लोकेशन मांगने वाले ऐप को कारण बताना चाहिए।\n"
            "पुरानी दी हुई परमिशन भी समय-समय पर जांचें।\n"
            "जो ऐप अब इस्तेमाल नहीं करते, उनकी परमिशन हटा दें।"
        ),
    },
    {
        "tone": "p4",
        "icon": "\U0001F3AD",
        "title_en": "A Stranger's Voice Can Wear a Familiar Mask",
        "tips_en": (
            "Cloned voices copy tone, not context — they slip up on details.\n"
            "Hang up and call the person back on a known number.\n"
            "Agree on a family 'safe word' for urgent money requests."
        ),
        "title_hi": "अनजान आवाज़, जानी-पहचानी शक्ल में भी आ सकती है",
        "tips_hi": (
            "नकली आवाज़ लहज़ा कॉपी करती है, पर बारीकियां नहीं।\n"
            "फोन रखें और जाने-पहचाने नंबर पर वापस कॉल करें।\n"
            "परिवार में पैसों के लिए एक 'सीक्रेट कोड वर्ड' तय करें।"
        ),
    },
    {
        "tone": "p5",
        "icon": "\U0001F522",
        "title_en": "Your OTP Has One Job: Stay With You",
        "tips_en": (
            "No bank or delivery agent ever needs your OTP to help you.\n"
            "An OTP you didn't request means someone else is trying to log in.\n"
            "Never read an OTP aloud over a call, even to 'support'."
        ),
        "title_hi": "आपका OTP सिर्फ़ आपके पास रहने के लिए है",
        "tips_hi": (
            "कोई भी बैंक या डिलीवरी एजेंट मदद के लिए OTP नहीं मांगता।\n"
            "बिना मांगे आया OTP मतलब कोई और आपके अकाउंट में घुसने की कोशिश कर रहा है।\n"
            "OTP कभी भी किसी को, 'सपोर्ट' को भी, फोन पर न बताएं।"
        ),
    },
    {
        "tone": "p6",
        "icon": "\U0001F517",
        "title_en": "A Link Is Not an Invitation",
        "tips_en": (
            "Hover or long-press a link to see where it really goes.\n"
            "Type known addresses yourself instead of tapping a forwarded one.\n"
            "When in doubt, open the official app instead of the link."
        ),
        "title_hi": "हर लिंक एक न्योता नहीं होता",
        "tips_hi": (
            "लिंक पर टैप करने से पहले देखें वह असल में कहां ले जाता है।\n"
            "जाना-पहचाना पता खुद टाइप करें, फॉरवर्ड किया लिंक न दबाएं।\n"
            "शक हो तो लिंक की जगह असली ऐप खोलें।"
        ),
    },
)

INFOGRAPHIC_SEED = (
    {
        "icon": "\U0001F4E6",
        "title": "Fake App (APK) Frauds, Decoded",
        "body": "A link promises a delivery update or a cashback app, but installs an APK outside the official store that quietly reads messages and screens.",
    },
    {
        "icon": "\U0001F4B8",
        "title": "UPI & Payment Request Frauds, Decoded",
        "body": "A 'collect' request is disguised as a refund. Approving it sends money out, it never brings money in — refunds never need your PIN.",
    },
    {
        "icon": "\U0001F5E3️",
        "title": "Deepfake Voice Call Frauds, Decoded",
        "body": "A cloned voice of someone you trust asks for urgent funds. The panic is real; the voice on the call may not be.",
    },
    {
        "icon": "\U0001F4C8",
        "title": "Job & Investment Scam Frauds, Decoded",
        "body": "Guaranteed returns and 'easy task' jobs ask for an upfront fee first. Legitimate pay never requires you to pay to get paid.",
    },
)


def seed_initial_content():
    """Publish the site's original poster and infographic copy, attributed to an admin.

    Idempotent: skips any title that already exists. Requires at least one
    administrator account to exist, since all content here is admin-authored.
    """
    admin = User.query.filter_by(role="admin", status="active").order_by(User.user_id).first()
    if admin is None:
        raise RuntimeError("Create an active administrator first with the create-admin command.")

    created = {"posters": 0, "infographics": 0}

    existing_poster_titles = {title for (title,) in db.session.query(Poster.title_en).all()}
    for data in POSTER_SEED:
        if data["title_en"] in existing_poster_titles:
            continue
        db.session.add(Poster(status="published", uploaded_by=admin.user_id, **data))
        created["posters"] += 1

    existing_infographic_titles = {title for (title,) in db.session.query(Infographic.title).all()}
    for data in INFOGRAPHIC_SEED:
        if data["title"] in existing_infographic_titles:
            continue
        db.session.add(Infographic(status="published", uploaded_by=admin.user_id, **data))
        created["infographics"] += 1

    db.session.commit()
    return created
