"""Listrik Bot — Electricity Monitor & Token Tracker Telegram Bot."""

import sys
import os
import logging
from datetime import datetime, timedelta

from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from storage import Storage
from monitor import PowerMonitor

# ======================== LOGGING ========================

logging.basicConfig(
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("listrik-bot")

# ======================== GLOBALS ========================

storage = Storage(Config.DB_PATH)
power_monitor = None  # Initialized after config validation
last_alert_time = None  # Cooldown tracker for low balance alerts
ALERT_COOLDOWN_HOURS = 4


# ======================== HELPERS ========================


def escape_md(text):
    """Escape MarkdownV2 special characters."""
    special = r"_*[]()~`>#+-=|{}.!\\"
    result = ""
    for ch in str(text):
        if ch in special:
            result += "\\" + ch
        else:
            result += ch
    return result


def esc(value, fmt=""):
    """Format a value and escape for MarkdownV2."""
    if fmt:
        return escape_md(format(value, fmt))
    return escape_md(str(value))


def is_authorized(update: Update) -> bool:
    """Check if the user is the authorized chat."""
    return str(update.effective_chat.id) == str(Config.TELEGRAM_CHAT_ID)


# ======================== COMMANDS ========================


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    msg = (
        "⚡ *Listrik Bot* — Electricity Monitor\n\n"
        "Track your prepaid electricity usage in real\\-time\\.\n\n"
        "*Commands:*\n"
        "/status — Current reading \\+ balance\n"
        "/topup `<kwh>` — Add purchased kWh\n"
        "/setbalance `<kwh>` — Set balance manually\n"
        "/usage — Monthly usage report\n"
        "/today — Today's hourly breakdown\n"
        "/history — Top\\-up history\n"
        "/help — Show this message"
    )
    await update.message.reply_text(msg, parse_mode="MarkdownV2")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await cmd_start(update, context)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    reading = storage.get_latest_reading()
    balance_data = storage.get_balance()
    balance = balance_data["current_kwh"]
    daily_avg = storage.get_daily_usage(days=7)

    lines = ["⚡ *Electricity Monitor*\n"]

    if reading:
        ts = datetime.fromisoformat(reading["timestamp"])
        age_seconds = (datetime.now() - ts).total_seconds()

        if age_seconds < 300:
            status_icon = "🟢"
        elif age_seconds < 600:
            status_icon = "🟡"
        else:
            status_icon = "🔴"

        v = esc(reading["voltage"], ".1f")
        a = esc(reading["current"], ".3f")
        w = esc(reading["power"], ".1f")

        lines.append(f"{status_icon} *Current Reading:*")
        lines.append(f"   Voltage : {v} V")
        lines.append(f"   Current : {a} A")
        lines.append(f"   Power   : {w} W")
        lines.append("")
    else:
        lines.append("🔴 *No readings yet*")
        lines.append("")

    lines.append(f"💰 *Balance:* {esc(balance, '.1f')} kWh")

    if daily_avg > 0:
        days_remaining = balance / daily_avg
        est_date = datetime.now() + timedelta(days=days_remaining)

        lines.append(f"📊 Daily Avg: {esc(daily_avg, '.1f')} kWh/day")

        if days_remaining < 1:
            hours_remaining = days_remaining * 24
            lines.append(f"⏰ Estimated: \\~{esc(hours_remaining, '.0f')} hours remaining")
        else:
            lines.append(f"📅 Estimated: \\~{esc(days_remaining, '.1f')} days remaining")
        lines.append(f"📆 Empty on : {esc(est_date.strftime('%b %d, %Y %H:%M'))}")
    else:
        lines.append("📊 Daily Avg: _Not enough data yet_")

    now = datetime.now()
    month_kwh = storage.get_monthly_usage(now.year, now.month)
    if month_kwh > 0:
        lines.append("")
        lines.append(f"📈 This Month: {esc(month_kwh, '.1f')} kWh")

    await update.message.reply_text("\n".join(lines), parse_mode="MarkdownV2")


async def cmd_topup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "Usage: `/topup <kwh>`\n\nExample: `/topup 135.1`",
            parse_mode="MarkdownV2",
        )
        return

    try:
        kwh = float(context.args[0])
        if kwh <= 0:
            raise ValueError("Must be positive")
    except ValueError:
        await update.message.reply_text("❌ Invalid kWh value\\. Use a positive number\\.", parse_mode="MarkdownV2")
        return

    new_balance = storage.add_topup(kwh)

    msg = (
        f"✅ *Token Top\\-up Recorded*\n\n"
        f"➕ Added: {esc(kwh, '.1f')} kWh\n"
        f"💰 New Balance: {esc(new_balance, '.1f')} kWh"
    )
    await update.message.reply_text(msg, parse_mode="MarkdownV2")


async def cmd_setbalance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "Usage: `/setbalance <kwh>`\n\nExample: `/setbalance 50.0`",
            parse_mode="MarkdownV2",
        )
        return

    try:
        kwh = float(context.args[0])
        if kwh < 0:
            raise ValueError("Cannot be negative")
    except ValueError:
        await update.message.reply_text("❌ Invalid kWh value\\.", parse_mode="MarkdownV2")
        return

    storage.set_balance(kwh)

    msg = f"✅ Balance set to {esc(kwh, '.1f')} kWh"
    await update.message.reply_text(msg, parse_mode="MarkdownV2")


async def cmd_usage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    summary = storage.get_monthly_summary(months=6)
    month_names = [
        "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]

    lines = ["📊 *Monthly Electricity Usage*\n"]

    has_data = False
    for entry in summary:
        m = month_names[entry["month"]]
        kwh = entry["kwh"]
        yr = entry["year"]
        if kwh > 0:
            has_data = True
            bar_len = min(int(kwh / 2), 20)
            bar = "█" * bar_len
            lines.append(f"`{m} {yr}` {escape_md(bar)} {esc(kwh, '.1f')} kWh")
        else:
            lines.append(f"`{m} {yr}` _No data_")

    if not has_data:
        lines.append("\n_No usage data recorded yet\\. The bot needs to run for a while first\\._")

    await update.message.reply_text("\n".join(lines), parse_mode="MarkdownV2")


async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    hourly = storage.get_hourly_usage_today()

    if not hourly:
        await update.message.reply_text("📊 No usage data for today yet\\.", parse_mode="MarkdownV2")
        return

    lines = ["📊 *Today's Hourly Usage*\n"]

    total = 0.0
    for hour in range(24):
        kwh = hourly.get(hour, 0.0)
        total += kwh
        if kwh > 0:
            bar_len = min(int(kwh * 10), 15)
            bar = "▓" * bar_len if bar_len > 0 else "░"
            lines.append(f"`{hour:02d}:00` {escape_md(bar)} {esc(kwh, '.3f')}")

    lines.append(f"\n⚡ Total today: {esc(total, '.2f')} kWh")

    await update.message.reply_text("\n".join(lines), parse_mode="MarkdownV2")


async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    topups = storage.get_topup_history(limit=10)

    if not topups:
        await update.message.reply_text(
            "📭 No top\\-up history yet\\.\n\nUse `/topup <kwh>` to record a purchase\\.",
            parse_mode="MarkdownV2",
        )
        return

    lines = ["🧾 *Top\\-up History*\n"]

    for i, t in enumerate(topups, 1):
        ts = datetime.fromisoformat(t["timestamp"])
        date_str = esc(ts.strftime("%Y-%m-%d %H:%M"))
        kwh_str = esc(t["kwh_added"], ".1f")
        bal_str = esc(t["balance_after"], ".1f")
        lines.append(f"{i}\\. {date_str} — \\+{kwh_str} kWh \\(bal: {bal_str}\\)")

    await update.message.reply_text("\n".join(lines), parse_mode="MarkdownV2")


# ======================== BACKGROUND TASKS ========================


async def poll_power(context: ContextTypes.DEFAULT_TYPE):
    """Background job: read power and update balance."""
    global last_alert_time

    reading = power_monitor.read()
    if reading is None:
        logger.warning("Failed to read power data, skipping this cycle")
        return

    storage.save_reading(reading["voltage"], reading["current"], reading["power"])

    interval_hours = Config.POLL_INTERVAL_SECONDS / 3600.0
    kwh_consumed = reading["power"] * interval_hours / 1000.0

    new_balance = storage.deduct_usage(kwh_consumed)

    logger.info(
        "Reading: %.1fV %.3fA %.1fW | Used: %.4f kWh | Balance: %.2f kWh",
        reading["voltage"], reading["current"], reading["power"],
        kwh_consumed, new_balance,
    )

    if new_balance <= Config.LOW_BALANCE_KWH:
        now = datetime.now()
        should_alert = (
            last_alert_time is None
            or (now - last_alert_time).total_seconds() > ALERT_COOLDOWN_HOURS * 3600
        )
        if should_alert:
            last_alert_time = now
            await send_low_balance_alert(context, new_balance, reading)


async def send_low_balance_alert(context, balance, reading):
    """Send low balance warning to Telegram."""
    daily_avg = storage.get_daily_usage(days=7)

    lines = [
        "⚠️ *LOW ELECTRICITY BALANCE*\n",
        f"⚡ Current Balance: {esc(balance, '.1f')} kWh",
    ]

    if daily_avg > 0:
        days_left = balance / daily_avg
        if days_left < 1:
            hours_left = days_left * 24
            est = datetime.now() + timedelta(hours=hours_left)
            lines.append(f"📊 Daily Average: {esc(daily_avg, '.1f')} kWh/day")
            lines.append(
                f"⏰ Estimated Empty: \\~{esc(hours_left, '.0f')} hours "
                f"\\({esc(est.strftime('%b %d, %H:%M'))}\\)"
            )
        else:
            est = datetime.now() + timedelta(days=days_left)
            lines.append(f"📊 Daily Average: {esc(daily_avg, '.1f')} kWh/day")
            lines.append(
                f"⏰ Estimated Empty: \\~{esc(days_left, '.1f')} days "
                f"\\({esc(est.strftime('%b %d, %Y'))}\\)"
            )

    pw = esc(reading["power"], ".1f")
    lines.append(f"\n🔌 Current Draw: {pw} W")
    lines.append("\n💡 Time to recharge\\! Use /topup `<kwh>`")

    try:
        await context.bot.send_message(
            chat_id=Config.TELEGRAM_CHAT_ID,
            text="\n".join(lines),
            parse_mode="MarkdownV2",
        )
        logger.info("Low balance alert sent (%.1f kWh)", balance)
    except Exception as e:
        logger.error("Failed to send alert: %s", e)


# ======================== MAIN ========================


async def post_init(application: Application):
    """Called after the bot starts — set up commands and background jobs."""
    commands = [
        BotCommand("status", "Current reading + balance"),
        BotCommand("topup", "Add purchased kWh"),
        BotCommand("setbalance", "Set balance manually"),
        BotCommand("usage", "Monthly usage report"),
        BotCommand("today", "Today's hourly breakdown"),
        BotCommand("history", "Top-up history"),
        BotCommand("help", "Show all commands"),
    ]
    await application.bot.set_my_commands(commands)

    application.job_queue.run_repeating(
        poll_power,
        interval=Config.POLL_INTERVAL_SECONDS,
        first=10,
        name="power_poll",
    )
    logger.info("Background polling started (every %ds)", Config.POLL_INTERVAL_SECONDS)

    balance = storage.get_balance()["current_kwh"]
    reading_count = storage.get_reading_count()
    mode_emoji = "☁️" if Config.CONNECTION_MODE == "cloud" else "🏠"
    mode_label = "Cloud" if Config.CONNECTION_MODE == "cloud" else "Local"

    msg = (
        f"🟢 *Listrik Bot Started*\n\n"
        f"Mode: {mode_emoji} {esc(mode_label)}\n"
        f"Balance: {esc(balance, '.1f')} kWh\n"
        f"Readings: {esc(reading_count)}\n"
        f"Poll Interval: {esc(Config.POLL_INTERVAL_SECONDS)}s\n"
        f"Alert Threshold: {esc(Config.LOW_BALANCE_KWH, '.0f')} kWh"
    )

    try:
        await application.bot.send_message(
            chat_id=Config.TELEGRAM_CHAT_ID,
            text=msg,
            parse_mode="MarkdownV2",
        )
    except Exception as e:
        logger.error("Failed to send startup message: %s", e)


def main():
    """Entry point."""
    try:
        Config.validate()
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)

    global power_monitor
    power_monitor = PowerMonitor()

    logger.info("Testing device connection...")
    test_reading = power_monitor.read()
    if test_reading:
        logger.info(
            "Connection OK: %.1fV %.3fA %.1fW",
            test_reading["voltage"], test_reading["current"], test_reading["power"],
        )
    else:
        logger.warning("Could not read device — will retry in background")

    app = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("topup", cmd_topup))
    app.add_handler(CommandHandler("setbalance", cmd_setbalance))
    app.add_handler(CommandHandler("usage", cmd_usage))
    app.add_handler(CommandHandler("today", cmd_today))
    app.add_handler(CommandHandler("history", cmd_history))

    logger.info("Listrik Bot starting...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
