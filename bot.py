"""
bot.py
Telegram bot that reads property data from a MockAPI URL and returns ratings.

Commands:
  /start                    - welcome message with interactive menu
  /menu                     - show the main menu with options
  /ratings                  - list all properties with Airbnb & Booking ratings
  /top5                     - show top 5 rated properties with chart
  /top20                    - show top 20 rated properties with chart
  /properties               - list all properties (basic info)
  /property <id>            - show single property details
  /complaints <property_id> - show complaints for a specific property

Environment variables:
  TELEGRAM_TOKEN        - required, your Telegram bot token from BotFather
  MOCKAPI_URL           - required, e.g. https://yourproject.mockapi.io/properties
  PROPERTIES_URL        - optional, separate URL for properties list (defaults to MOCKAPI_URL)
  COMPLAINTS_URL        - optional, URL for complaints endpoint (e.g. https://yourproject.mockapi.io/complaints)
  MOCKAPI_KEY           - optional, API key/token to send to MockAPI
  MOCKAPI_KEY_HEADER    - optional, header name to send the key under (default: Authorization)
  MOCKAPI_KEY_PREFIX    - optional, prefix for token (default: Bearer). If you want raw token, set to empty string.
"""

import os
import io
import logging
import requests
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for server use
import matplotlib.pyplot as plt
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
from typing import List, Dict, Tuple
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# ---- Configuration ----
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MOCKAPI_URL = os.getenv("MOCKAPI_URL")  # e.g. https://yourproject.mockapi.io/properties
PROPERTIES_URL = os.getenv("PROPERTIES_URL", MOCKAPI_URL)  # separate URL for properties list
COMPLAINTS_URL = os.getenv("COMPLAINTS_URL")  # e.g. https://yourproject.mockapi.io/complaints
MOCKAPI_KEY = os.getenv("MOCKAPI_KEY")  # optional
MOCKAPI_KEY_HEADER = os.getenv("MOCKAPI_KEY_HEADER", "Authorization")
MOCKAPI_KEY_PREFIX = os.getenv("MOCKAPI_KEY_PREFIX", "Bearer")  # set "" for no prefix

# Telegram message max length (safe limit)
TELEGRAM_MAX_LEN = 4000

# ---- Logging ----
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not TELEGRAM_TOKEN or not MOCKAPI_URL:
    logger.error("Please set TELEGRAM_TOKEN and MOCKAPI_URL environment variables.")
    raise SystemExit("Missing required environment variables.")


def build_headers() -> Dict[str, str]:
    """Return headers to include in MockAPI requests, including optional auth."""
    headers = {
        "Accept": "application/json",
        "User-Agent": "MockAPI-Telegram-Bot/1.0"
    }
    if MOCKAPI_KEY:
        prefix = (MOCKAPI_KEY_PREFIX + " ") if MOCKAPI_KEY_PREFIX else ""
        headers[MOCKAPI_KEY_HEADER] = prefix + MOCKAPI_KEY
    return headers


def fetch_all_properties() -> List[Dict]:
    """Fetch all properties from the base MOCKAPI_URL (expects a list)."""
    try:
        resp = requests.get(MOCKAPI_URL, headers=build_headers(), timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return data
        # some mock APIs wrap result: { "data": [...] }
        if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
            return data["data"]
        logger.warning("Unexpected payload format, returning empty list.")
        return []
    except Exception as e:
        logger.exception("Failed to fetch properties: %s", e)
        return []


def fetch_property_by_id(property_id: str) -> Dict:
    """Try to fetch a single property via {MOCKAPI_URL}/{id}. If not available, fallback to list filter."""
    try:
        # Try fetching /properties/{id} first
        single_url = MOCKAPI_URL.rstrip("/") + "/" + property_id
        resp = requests.get(single_url, headers=build_headers(), timeout=10)
        if resp.status_code == 200:
            return resp.json()
        # If that failed, try searching the list for id
        all_props = fetch_all_properties()
        for p in all_props:
            # MockAPI typically uses "id" as string
            if str(p.get("id")) == str(property_id):
                return p
        return {}
    except Exception as e:
        logger.exception("Failed to fetch property %s: %s", property_id, e)
        return {}


def fetch_properties_list() -> List[Dict]:
    """Fetch properties from PROPERTIES_URL (can be different from ratings endpoint)."""
    url = PROPERTIES_URL or MOCKAPI_URL
    try:
        resp = requests.get(url, headers=build_headers(), timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
            return data["data"]
        return []
    except Exception as e:
        logger.exception("Failed to fetch properties list: %s", e)
        return []


def fetch_complaints_for_property(property_id: str) -> List[Dict]:
    """Fetch complaints for a specific property from COMPLAINTS_URL."""
    if not COMPLAINTS_URL:
        return []
    try:
        # Try query param filter first: /complaints?property_id=X
        url_with_filter = f"{COMPLAINTS_URL.rstrip('/')}?property_id={property_id}"
        resp = requests.get(url_with_filter, headers=build_headers(), timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "data" in data:
            return data["data"]
        return []
    except Exception as e:
        logger.exception("Failed to fetch complaints for property %s: %s", property_id, e)
        return []


def format_property(p: Dict) -> str:
    """Return a nicely formatted string for one property (safe keys)."""
    name = p.get("name", "Unnamed property")
    airbnb = p.get("airbnb_rating", p.get("airbnb", "N/A"))
    booking = p.get("booking_rating", p.get("booking", "N/A"))
    pid = p.get("id", "N/A")
    extra = []
    # Include any other useful fields if present
    if "location" in p:
        extra.append(f"Location: {p['location']}")
    if "url" in p:
        extra.append(f"URL: {p['url']}")
    extras = ("\n    " + "\n    ".join(extra)) if extra else ""
    return f"🏠 {name} (id: {pid})\n   ⭐ Airbnb: {airbnb}\n   ⭐ Booking: {booking}{extras}\n"


def format_property_basic(p: Dict) -> str:
    """Return a basic formatted string for property listing."""
    name = p.get("name", "Unnamed property")
    pid = p.get("id", "N/A")
    location = p.get("location", p.get("address", ""))
    loc_str = f" - {location}" if location else ""
    return f"🏠 [{pid}] {name}{loc_str}"


def format_complaint(c: Dict) -> str:
    """Return a formatted string for a complaint."""
    complaint_id = c.get("id", "N/A")
    title = c.get("title", c.get("subject", "No title"))
    description = c.get("description", c.get("message", c.get("text", "No description")))
    status = c.get("status", "unknown")
    date = c.get("date", c.get("created_at", c.get("createdAt", "")))
    severity = c.get("severity", c.get("priority", ""))

    lines = [f"📋 Complaint #{complaint_id}: {title}"]
    lines.append(f"   Status: {status}")
    if severity:
        lines.append(f"   Severity: {severity}")
    if date:
        lines.append(f"   Date: {date}")
    lines.append(f"   Description: {description[:200]}{'...' if len(description) > 200 else ''}")
    return "\n".join(lines)


def get_property_rating(p: Dict) -> float:
    """Calculate average rating from Airbnb and Booking ratings."""
    airbnb = p.get("airbnb_rating", p.get("airbnb"))
    booking = p.get("booking_rating", p.get("booking"))

    ratings = []
    for r in [airbnb, booking]:
        if r is not None:
            try:
                ratings.append(float(r))
            except (ValueError, TypeError):
                pass

    if not ratings:
        return 0.0
    return sum(ratings) / len(ratings)


def get_top_rated_properties(properties: List[Dict], limit: int) -> List[Tuple[Dict, float]]:
    """Return top N properties sorted by average rating."""
    rated = [(p, get_property_rating(p)) for p in properties]
    rated.sort(key=lambda x: x[1], reverse=True)
    return rated[:limit]


def generate_ratings_chart(properties: List[Tuple[Dict, float]], title: str) -> io.BytesIO:
    """Generate a horizontal bar chart of property ratings and return as bytes buffer."""
    # Prepare data
    names = []
    airbnb_ratings = []
    booking_ratings = []

    for p, _ in properties:
        name = p.get("name", "Unknown")
        # Truncate long names
        if len(name) > 20:
            name = name[:17] + "..."
        names.append(name)

        airbnb = p.get("airbnb_rating", p.get("airbnb"))
        booking = p.get("booking_rating", p.get("booking"))

        try:
            airbnb_ratings.append(float(airbnb) if airbnb else 0)
        except (ValueError, TypeError):
            airbnb_ratings.append(0)

        try:
            booking_ratings.append(float(booking) if booking else 0)
        except (ValueError, TypeError):
            booking_ratings.append(0)

    # Create figure
    fig_height = max(6, len(names) * 0.5)
    fig, ax = plt.subplots(figsize=(10, fig_height))

    y_pos = range(len(names))
    bar_height = 0.35

    # Create horizontal bars
    bars1 = ax.barh([y - bar_height/2 for y in y_pos], airbnb_ratings,
                    bar_height, label='Airbnb', color='#FF5A5F')
    bars2 = ax.barh([y + bar_height/2 for y in y_pos], booking_ratings,
                    bar_height, label='Booking', color='#003580')

    # Add value labels on bars
    for bar in bars1:
        width = bar.get_width()
        if width > 0:
            ax.text(width + 0.05, bar.get_y() + bar.get_height()/2,
                    f'{width:.1f}', va='center', fontsize=9)

    for bar in bars2:
        width = bar.get_width()
        if width > 0:
            ax.text(width + 0.05, bar.get_y() + bar.get_height()/2,
                    f'{width:.1f}', va='center', fontsize=9)

    # Customize chart
    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(names)
    ax.invert_yaxis()  # Top property at the top
    ax.set_xlabel('Rating')
    ax.set_title(title)
    ax.legend(loc='lower right')
    ax.set_xlim(0, 5.5)  # Ratings typically 0-5
    ax.grid(axis='x', alpha=0.3)

    plt.tight_layout()

    # Save to buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)

    return buf


def format_top_property(rank: int, p: Dict, avg_rating: float) -> str:
    """Format a property for top ratings list with rank."""
    name = p.get("name", "Unnamed")
    pid = p.get("id", "N/A")
    airbnb = p.get("airbnb_rating", p.get("airbnb", "N/A"))
    booking = p.get("booking_rating", p.get("booking", "N/A"))
    medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"{rank}.")
    return f"{medal} {name} (id: {pid})\n   ⭐ Avg: {avg_rating:.2f} | Airbnb: {airbnb} | Booking: {booking}"


def split_and_send(chat, text: str):
    """Split long text into chunks and send sequentially (chat is telegram.Bot or update.message.reply_text)."""
    # If chat is update.message, the .reply_text method exists. We'll accept either:
    send_fn = chat.reply_text if hasattr(chat, "reply_text") else chat.send_message
    start = 0
    while start < len(text):
        chunk = text[start:start + TELEGRAM_MAX_LEN]
        send_fn(chunk)
        start += TELEGRAM_MAX_LEN


# ---- Menu keyboard ----
def get_main_menu_keyboard():
    """Return an inline keyboard with main menu options."""
    keyboard = [
        [
            InlineKeyboardButton("🏆 Top 5", callback_data="action_top5"),
            InlineKeyboardButton("📈 Top 20", callback_data="action_top20"),
        ],
        [
            InlineKeyboardButton("📊 All Ratings", callback_data="action_ratings"),
            InlineKeyboardButton("🏠 Properties", callback_data="action_properties"),
        ],
        [
            InlineKeyboardButton("🔍 Property Details", callback_data="action_property_help"),
            InlineKeyboardButton("📋 Complaints", callback_data="action_complaints_help"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


# ---- Telegram handlers ----
def start(update, context):
    welcome_message = (
        "👋 Welcome to the Property Management Bot!\n\n"
        "I can help you with:\n"
        "• View property ratings (Airbnb & Booking)\n"
        "• Browse the list of properties\n"
        "• Check complaints for any property\n\n"
        "Use the menu below or type commands directly:"
    )
    update.message.reply_text(welcome_message, reply_markup=get_main_menu_keyboard())


def menu_handler(update, context):
    """Show the main menu."""
    update.message.reply_text(
        "📌 Main Menu\n\nChoose an option below:",
        reply_markup=get_main_menu_keyboard()
    )


def ratings_handler(update, context):
    update.message.chat.send_action("typing")
    props = fetch_all_properties()
    if not props:
        update.message.reply_text("No property data available (check MOCKAPI_URL or network).")
        return

    lines = ["🏡 Property Ratings (MockAPI) \n"]
    for p in props:
        lines.append(format_property(p))

    message = "\n".join(lines)
    # split & send so we don't exceed Telegram limits
    split_and_send(update.message, message)


def top5_handler(update, context):
    """Show top 5 rated properties with chart."""
    update.message.chat.send_action("typing")
    props = fetch_all_properties()
    if not props:
        update.message.reply_text("No property data available.")
        return

    top_props = get_top_rated_properties(props, 5)
    if not top_props:
        update.message.reply_text("Could not calculate ratings.")
        return

    # Send text summary
    lines = ["🏆 Top 5 Best Rated Properties\n"]
    for rank, (p, avg) in enumerate(top_props, 1):
        lines.append(format_top_property(rank, p, avg))
    update.message.reply_text("\n".join(lines))

    # Generate and send chart
    update.message.chat.send_action("upload_photo")
    chart_buf = generate_ratings_chart(top_props, "Top 5 Properties - Ratings Comparison")
    update.message.reply_photo(photo=chart_buf, caption="📊 Top 5 Properties Rating Chart")


def top20_handler(update, context):
    """Show top 20 rated properties with chart."""
    update.message.chat.send_action("typing")
    props = fetch_all_properties()
    if not props:
        update.message.reply_text("No property data available.")
        return

    # Get top 20 (or all if less than 20)
    limit = min(20, len(props))
    top_props = get_top_rated_properties(props, limit)
    if not top_props:
        update.message.reply_text("Could not calculate ratings.")
        return

    # Send text summary
    lines = [f"🏆 Top {limit} Best Rated Properties\n"]
    for rank, (p, avg) in enumerate(top_props, 1):
        lines.append(format_top_property(rank, p, avg))
    message = "\n".join(lines)
    split_and_send(update.message, message)

    # Generate and send chart
    update.message.chat.send_action("upload_photo")
    chart_buf = generate_ratings_chart(top_props, f"Top {limit} Properties - Ratings Comparison")
    update.message.reply_photo(photo=chart_buf, caption=f"📊 Top {limit} Properties Rating Chart")


def property_handler(update, context):
    args = context.args
    if not args:
        update.message.reply_text("Usage: /property <id>\nExample: /property 1")
        return
    prop_id = args[0]
    update.message.chat.send_action("typing")
    p = fetch_property_by_id(prop_id)
    if not p:
        update.message.reply_text(f"Property with id {prop_id} not found.")
        return
    update.message.reply_text(format_property(p))


def properties_handler(update, context):
    """List all properties (basic info)."""
    update.message.chat.send_action("typing")
    props = fetch_properties_list()
    if not props:
        update.message.reply_text("No properties available.")
        return

    lines = ["🏠 Properties List\n"]
    for p in props:
        lines.append(format_property_basic(p))

    lines.append("\n💡 Use /property <id> for details")
    lines.append("💡 Use /complaints <id> to see complaints")
    message = "\n".join(lines)
    split_and_send(update.message, message)


def complaints_handler(update, context):
    """Show complaints for a specific property."""
    args = context.args
    if not args:
        update.message.reply_text(
            "Usage: /complaints <property_id>\n"
            "Example: /complaints 1\n\n"
            "This will show all complaints for the specified property."
        )
        return

    if not COMPLAINTS_URL:
        update.message.reply_text(
            "Complaints feature is not configured.\n"
            "Please set COMPLAINTS_URL in environment variables."
        )
        return

    prop_id = args[0]
    update.message.chat.send_action("typing")

    # First verify the property exists
    prop = fetch_property_by_id(prop_id)
    if not prop:
        update.message.reply_text(f"Property with id {prop_id} not found.")
        return

    complaints = fetch_complaints_for_property(prop_id)
    prop_name = prop.get("name", f"Property {prop_id}")

    if not complaints:
        update.message.reply_text(f"No complaints found for {prop_name} (id: {prop_id}).")
        return

    lines = [f"📋 Complaints for {prop_name} (id: {prop_id})\n"]
    lines.append(f"Total: {len(complaints)} complaint(s)\n")
    for c in complaints:
        lines.append(format_complaint(c))
        lines.append("")  # blank line between complaints

    message = "\n".join(lines)
    split_and_send(update.message, message)


def button_callback_handler(update, context):
    """Handle inline keyboard button presses."""
    query = update.callback_query
    query.answer()

    action = query.data

    if action == "action_top5":
        query.message.chat.send_action("typing")
        props = fetch_all_properties()
        if not props:
            query.message.reply_text("No property data available.")
            return
        top_props = get_top_rated_properties(props, 5)
        if not top_props:
            query.message.reply_text("Could not calculate ratings.")
            return
        lines = ["🏆 Top 5 Best Rated Properties\n"]
        for rank, (p, avg) in enumerate(top_props, 1):
            lines.append(format_top_property(rank, p, avg))
        query.message.reply_text("\n".join(lines))
        query.message.chat.send_action("upload_photo")
        chart_buf = generate_ratings_chart(top_props, "Top 5 Properties - Ratings Comparison")
        query.message.reply_photo(photo=chart_buf, caption="📊 Top 5 Properties Rating Chart")

    elif action == "action_top20":
        query.message.chat.send_action("typing")
        props = fetch_all_properties()
        if not props:
            query.message.reply_text("No property data available.")
            return
        limit = min(20, len(props))
        top_props = get_top_rated_properties(props, limit)
        if not top_props:
            query.message.reply_text("Could not calculate ratings.")
            return
        lines = [f"🏆 Top {limit} Best Rated Properties\n"]
        for rank, (p, avg) in enumerate(top_props, 1):
            lines.append(format_top_property(rank, p, avg))
        split_and_send(query.message, "\n".join(lines))
        query.message.chat.send_action("upload_photo")
        chart_buf = generate_ratings_chart(top_props, f"Top {limit} Properties - Ratings Comparison")
        query.message.reply_photo(photo=chart_buf, caption=f"📊 Top {limit} Properties Rating Chart")

    elif action == "action_ratings":
        query.message.chat.send_action("typing")
        props = fetch_all_properties()
        if not props:
            query.message.reply_text("No property data available.")
            return
        lines = ["🏡 Property Ratings\n"]
        for p in props:
            lines.append(format_property(p))
        message = "\n".join(lines)
        split_and_send(query.message, message)

    elif action == "action_properties":
        query.message.chat.send_action("typing")
        props = fetch_properties_list()
        if not props:
            query.message.reply_text("No properties available.")
            return
        lines = ["🏠 Properties List\n"]
        for p in props:
            lines.append(format_property_basic(p))
        lines.append("\n💡 Use /property <id> for details")
        message = "\n".join(lines)
        split_and_send(query.message, message)

    elif action == "action_property_help":
        query.message.reply_text(
            "🔍 Property Details\n\n"
            "To view details for a specific property, use:\n"
            "/property <id>\n\n"
            "Example: /property 1"
        )

    elif action == "action_complaints_help":
        query.message.reply_text(
            "📋 View Complaints\n\n"
            "To see complaints for a specific property, use:\n"
            "/complaints <property_id>\n\n"
            "Example: /complaints 1"
        )


def error_handler(update, context):
    logger.error("Update caused error: %s", context.error)


def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Command handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("menu", menu_handler))
    dp.add_handler(CommandHandler("ratings", ratings_handler))
    dp.add_handler(CommandHandler("top5", top5_handler))
    dp.add_handler(CommandHandler("top20", top20_handler))
    dp.add_handler(CommandHandler("properties", properties_handler))
    dp.add_handler(CommandHandler("property", property_handler, pass_args=True))
    dp.add_handler(CommandHandler("complaints", complaints_handler, pass_args=True))

    # Callback handler for inline keyboard buttons
    dp.add_handler(CallbackQueryHandler(button_callback_handler))

    dp.add_error_handler(error_handler)

    logger.info("Starting bot...")
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
