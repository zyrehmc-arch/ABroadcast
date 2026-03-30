import os
import asyncio
import logging
from datetime import datetime, time as dtime
import pytz

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters, ConversationHandler
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ── LOGGING ──
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── CONFIG ──
BOT_TOKEN   = os.environ["BOT_TOKEN"]
CHANNEL_ID  = os.environ["CHANNEL_ID"]   # es. @miocanale o -100xxxxxxxx
ADMIN_IDS = set(map(int, os.environ["ADMIN_IDS"].split(",")))
TIMEZONE    = os.environ.get("TIMEZONE", "Europe/Rome")

tz = pytz.timezone(TIMEZONE)

# ── STATI conversazione ──
WAIT_MSG, WAIT_DATE, WAIT_TIME, WAIT_REPEAT = range(4)

# ── SCHEDULER ──
scheduler = AsyncIOScheduler(timezone=tz)

# ══════════════════════════════════════
#   HELPERS
# ══════════════════════════════════════
def only_admin(func):
    """Decorator — solo l'admin può usare il comando."""
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS:
            await update.message.reply_text("❌ Non autorizzato.")
            return
        return await func(update, ctx)
    return wrapper

def main_menu():
    kb = [
        [InlineKeyboardButton("🖥 Apri Pannello", web_app=WebAppInfo(url="https://zyrehmc-arch.github.io/ABroadcast"))],
        [InlineKeyboardButton("📤 Invia messaggio ora",     callback_data="send_now")],
        [InlineKeyboardButton("🕐 Programma messaggio",     callback_data="schedule")],
        [InlineKeyboardButton("⏰ Vedi coda messaggi",      callback_data="queue")],
        [InlineKeyboardButton("📰 Invia news trading ora",  callback_data="news")],
    ]
    return InlineKeyboardMarkup(kb)

def cancel_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Annulla", callback_data="cancel")]])

# ══════════════════════════════════════
#   /start  /menu
# ══════════════════════════════════════
@only_admin
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Benvenuto nel Broadcaster!*\n\nScegli un'azione:",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

# ══════════════════════════════════════
#   SEND NOW — conversazione
# ══════════════════════════════════════
@only_admin
async def cmd_send_now(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q: await q.answer()
    target = q.message if q else update.message
    await target.reply_text(
        "✏️ Scrivi il messaggio da inviare *subito* al canale.\n\n"
        "Puoi usare il formato Telegram standard: *grassetto*, _corsivo_, `codice`\n\n"
        "Digita /annulla per tornare al menu.",
        parse_mode="Markdown",
        reply_markup=cancel_kb()
    )
    return WAIT_MSG

async def receive_now_msg(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "/annulla":
        return await cancel(update, ctx)
    try:
        await ctx.bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode="Markdown")
        await update.message.reply_text("✅ Messaggio inviato al canale!", reply_markup=main_menu())
    except Exception as e:
        await update.message.reply_text(f"❌ Errore: {e}\n\nControlla il Channel ID nelle variabili.")
    return ConversationHandler.END

# ══════════════════════════════════════
#   SCHEDULE — conversazione
# ══════════════════════════════════════
@only_admin
async def cmd_schedule(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q: await q.answer()
    target = q.message if q else update.message
    await target.reply_text(
        "✏️ Scrivi il messaggio da *programmare*.\n\nDigita /annulla per tornare.",
        parse_mode="Markdown",
        reply_markup=cancel_kb()
    )
    return WAIT_MSG

async def sched_got_msg(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "/annulla":
        return await cancel(update, ctx)
    ctx.user_data["sched_msg"] = update.message.text
    await update.message.reply_text(
        "📅 Quando vuoi inviarlo?\n\n"
        "Scrivi la *data* nel formato `GG/MM/AAAA`\nEs: `25/12/2025`",
        parse_mode="Markdown",
        reply_markup=cancel_kb()
    )
    return WAIT_DATE

async def sched_got_date(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "/annulla":
        return await cancel(update, ctx)
    try:
        d = datetime.strptime(update.message.text.strip(), "%d/%m/%Y").date()
        ctx.user_data["sched_date"] = d
        await update.message.reply_text(
            "🕐 A che ora? Formato `HH:MM`\nEs: `09:30`",
            parse_mode="Markdown",
            reply_markup=cancel_kb()
        )
        return WAIT_TIME
    except ValueError:
        await update.message.reply_text("⚠️ Formato non valido. Usa `GG/MM/AAAA`", parse_mode="Markdown")
        return WAIT_DATE

async def sched_got_time(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "/annulla":
        return await cancel(update, ctx)
    try:
        t = datetime.strptime(update.message.text.strip(), "%H:%M").time()
        ctx.user_data["sched_time"] = t
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("1️⃣ Una volta sola",   callback_data="rep_once")],
            [InlineKeyboardButton("📆 Ogni giorno",       callback_data="rep_daily")],
            [InlineKeyboardButton("📅 Ogni settimana",    callback_data="rep_weekly")],
            [InlineKeyboardButton("🗓 Lun–Ven",           callback_data="rep_weekdays")],
        ])
        await update.message.reply_text("🔁 Ripetizione?", reply_markup=kb)
        return WAIT_REPEAT
    except ValueError:
        await update.message.reply_text("⚠️ Formato non valido. Usa `HH:MM`", parse_mode="Markdown")
        return WAIT_TIME

async def sched_got_repeat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    repeat = q.data  # rep_once / rep_daily / rep_weekly / rep_weekdays

    msg   = ctx.user_data["sched_msg"]
    date  = ctx.user_data["sched_date"]
    t     = ctx.user_data["sched_time"]
    run_dt = tz.localize(datetime.combine(date, t))

    rep_labels = {
        "rep_once":"Una volta","rep_daily":"Ogni giorno",
        "rep_weekly":"Ogni settimana","rep_weekdays":"Lun–Ven"
    }

    job_id = f"sched_{int(run_dt.timestamp())}"

    async def send_job():
        await ctx.bot.send_message(chat_id=CHANNEL_ID, text=msg, parse_mode="Markdown")

    if repeat == "rep_once":
        scheduler.add_job(send_job, "date", run_date=run_dt, id=job_id)
    elif repeat == "rep_daily":
        scheduler.add_job(send_job, "cron", hour=t.hour, minute=t.minute, id=job_id)
    elif repeat == "rep_weekly":
        scheduler.add_job(send_job, "cron", day_of_week=date.weekday(), hour=t.hour, minute=t.minute, id=job_id)
    elif repeat == "rep_weekdays":
        scheduler.add_job(send_job, "cron", day_of_week="mon-fri", hour=t.hour, minute=t.minute, id=job_id)

    await q.message.reply_text(
        f"✅ *Programmato!*\n\n"
        f"📅 {date.strftime('%d/%m/%Y')} alle {t.strftime('%H:%M')}\n"
        f"🔁 {rep_labels[repeat]}\n\n"
        f"📝 _{msg[:80]}{'...' if len(msg)>80 else ''}_",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )
    return ConversationHandler.END

# ══════════════════════════════════════
#   QUEUE — mostra messaggi programmati
# ══════════════════════════════════════
@only_admin
async def cmd_queue(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q: await q.answer()
    target = q.message if q else update.message

    jobs = scheduler.get_jobs()
    if not jobs:
        await target.reply_text("📭 Nessun messaggio in coda.", reply_markup=main_menu())
        return

    now = datetime.now(tz)
    lines = ["⏰ *Messaggi programmati:*\n"]
    kb_rows = []

    for job in jobs:
        next_run = job.next_run_time
        if next_run:
            diff = next_run - now
            total_secs = int(diff.total_seconds())
            if total_secs < 0:
                time_str = "⚡ Imminente"
            else:
                h = total_secs // 3600
                m = (total_secs % 3600) // 60
                time_str = f"tra {h}h {m}m" if h else f"tra {m}m"
            lines.append(f"• `{next_run.strftime('%d/%m %H:%M')}` — {time_str}")
            kb_rows.append([InlineKeyboardButton(f"❌ Elimina {next_run.strftime('%d/%m %H:%M')}", callback_data=f"del_{job.id}")])

    kb_rows.append([InlineKeyboardButton("🔙 Menu", callback_data="menu")])
    await target.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb_rows)
    )

async def delete_job(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    job_id = q.data.replace("del_", "")
    try:
        scheduler.remove_job(job_id)
        await q.message.reply_text("✅ Messaggio eliminato dalla coda.", reply_markup=main_menu())
    except Exception:
        await q.message.reply_text("⚠️ Messaggio non trovato.", reply_markup=main_menu())

# ══════════════════════════════════════
#   NEWS TRADING
# ══════════════════════════════════════
TRADING_NEWS = [
    {"tag":"📈 FOREX",   "text":"EUR/USD rimbalza dopo dati CPI USA: dollaro perde terreno. Livello chiave: 1.0850"},
    {"tag":"₿ CRYPTO",  "text":"Bitcoin consolida sopra $70K. Volumi istituzionali in aumento pre-halving."},
    {"tag":"📊 MACRO",   "text":"Fed: Powell segnala pausa rialzi. Mercati prezzano taglio tassi a settembre."},
    {"tag":"🏦 STOCKS",  "text":"S&P 500 ai massimi storici dopo earnings solidi di Meta e Microsoft."},
]

@only_admin
async def cmd_news(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q: await q.answer()
    target = q.message if q else update.message

    kb = []
    for i, n in enumerate(TRADING_NEWS):
        kb.append([InlineKeyboardButton(f"{n['tag']} — Invia", callback_data=f"sendnews_{i}")])
    kb.append([InlineKeyboardButton("📤 Invia TUTTE", callback_data="sendnews_all")])
    kb.append([InlineKeyboardButton("🔙 Menu", callback_data="menu")])

    text = "📰 *Trading News disponibili:*\n\n"
    for n in TRADING_NEWS:
        text += f"{n['tag']}\n_{n['text'][:60]}..._\n\n"

    await target.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

async def send_news_item(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "sendnews_all":
        for n in TRADING_NEWS:
            msg = f"{n['tag']}\n\n{n['text']}\n\n⏱ {datetime.now(tz).strftime('%H:%M')} · #trading"
            await ctx.bot.send_message(chat_id=CHANNEL_ID, text=msg)
        await q.message.reply_text("✅ Tutte le news inviate!", reply_markup=main_menu())
    else:
        idx = int(q.data.replace("sendnews_", ""))
        n = TRADING_NEWS[idx]
        msg = f"{n['tag']}\n\n{n['text']}\n\n⏱ {datetime.now(tz).strftime('%H:%M')} · #trading"
        await ctx.bot.send_message(chat_id=CHANNEL_ID, text=msg)
        await q.message.reply_text("✅ News inviata!", reply_markup=main_menu())

# ══════════════════════════════════════
#   UTILS
# ══════════════════════════════════════
async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.callback_query.message
    await msg.reply_text("❌ Operazione annullata.", reply_markup=main_menu())
    return ConversationHandler.END

async def back_to_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.message.reply_text("Scegli un'azione:", reply_markup=main_menu())

# ══════════════════════════════════════
#   MAIN
# ══════════════════════════════════════
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Conversazione: invia ora
    conv_send = ConversationHandler(
        entry_points=[CallbackQueryHandler(cmd_send_now, pattern="^send_now$")],
        states={WAIT_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_now_msg)]},
        fallbacks=[CommandHandler("annulla", cancel)],
    )

    # Conversazione: programma
    conv_sched = ConversationHandler(
        entry_points=[CallbackQueryHandler(cmd_schedule, pattern="^schedule$")],
        states={
            WAIT_MSG:    [MessageHandler(filters.TEXT & ~filters.COMMAND, sched_got_msg)],
            WAIT_DATE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, sched_got_date)],
            WAIT_TIME:   [MessageHandler(filters.TEXT & ~filters.COMMAND, sched_got_time)],
            WAIT_REPEAT: [CallbackQueryHandler(sched_got_repeat, pattern="^rep_")],
        },
        fallbacks=[CommandHandler("annulla", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu",  start))
    app.add_handler(conv_send)
    app.add_handler(conv_sched)
    app.add_handler(CallbackQueryHandler(cmd_queue,      pattern="^queue$"))
    app.add_handler(CallbackQueryHandler(delete_job,     pattern="^del_"))
    app.add_handler(CallbackQueryHandler(cmd_news,       pattern="^news$"))
    app.add_handler(CallbackQueryHandler(send_news_item, pattern="^sendnews_"))
    app.add_handler(CallbackQueryHandler(back_to_menu,   pattern="^menu$"))

    scheduler.start()
    app.run_polling()

if __name__ == "__main__":
    main()
