import json
import os
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")

print(f"Токен получен: {'ДА' if BOT_TOKEN else 'НЕТ'}")

if not BOT_TOKEN:
    print("Ошибка: BOT_TOKEN не найден!")
    exit(1)

DATA_FILE = "user_data.json"

TASKS = [
    {"name": "💊 Витамины", "time": "09:00", "days": None},
    {"name": "📋 Планка", "time": "10:00", "days": None},
    {"name": "🏋️ Упражнения", "time": "18:00", "days": [0,1,2,3,4]},
    {"name": "😊 Дофаминовые шаги", "time": "12:00", "days": None},
    {"name": "🏃 Беговая дорожка", "time": "19:00", "days": [1,3,5]},
    {"name": "📖 Чтение", "time": "21:00", "days": None},
    {"name": "🎓 Обучение", "time": "15:00", "days": [0,2,4]},
    {"name": "💆‍♀️ Расчёска", "time": "22:30", "days": None},
    {"name": "🦷 Зубы + макияж", "time": "22:20", "days": None},
    {"name": "🍳 Ужин", "time": "21:30", "days": None},
]

DAYS_RU = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user_data(user_id):
    data = load_data()
    user_id_str = str(user_id)
    if user_id_str not in data:
        data[user_id_str] = {
            "tasks": {task["name"]: False for task in TASKS},
            "custom_tasks": []
        }
        save_data(data)
    return data, data[user_id_str]

async def main_menu():
    keyboard = [
        [InlineKeyboardButton("📋 Список задач", callback_data="list")],
        [InlineKeyboardButton("✅ Отметить выполнение", callback_data="complete")],
        [InlineKeyboardButton("➕ Своя задача", callback_data="add_custom")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("🔄 Сбросить всё", callback_data="reset")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    get_user_data(user_id)
    await update.message.reply_text(
        "🏆 *Умный Планировщик*\n\n"
        "✅ Напоминания в нужное время\n"
        "📅 Задачи на определённые дни\n"
        "➕ Свои задачи\n\n"
        "Выбери действие 👇",
        reply_markup=await main_menu(),
        parse_mode="Markdown"
    )

def check_day(task_days):
    if task_days is None:
        return True
    today = datetime.now().weekday()
    return today in task_days

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    _, user_data = get_user_data(user_id)
    
    if data == "list":
        text = "📋 *Твои задачи:*\n\n"
        for task in TASKS:
            status = "✅" if user_data["tasks"].get(task["name"], False) else "❌"
            days_str = "каждый день" if task["days"] is None else " ".join(DAYS_RU[d] for d in task["days"])
            text += f"{status} {task['name']} ({days_str})\n"
        if user_data["custom_tasks"]:
            text += "\n*Мои задачи:*\n"
            for ct in user_data["custom_tasks"]:
                status = "✅" if ct.get("done", False) else "❌"
                days_str = "каждый день" if ct["days"] is None else " ".join(DAYS_RU[d] for d in ct["days"])
                text += f"{status} {ct['name']} ({days_str})\n"
        await query.edit_message_text(text, reply_markup=await main_menu(), parse_mode="Markdown")
    
    elif data == "complete":
        keyboard = []
        for task in TASKS:
            if check_day(task["days"]) and not user_data["tasks"].get(task["name"], False):
                keyboard.append([InlineKeyboardButton(f"⬜ {task['name']}", callback_data=f"done_{task['name']}")])
        for i, ct in enumerate(user_data["custom_tasks"]):
            if not ct.get("done", False):
                keyboard.append([InlineKeyboardButton(f"⬜ {ct['name']}", callback_data=f"done_custom_{i}")])
        if not keyboard:
            keyboard.append([InlineKeyboardButton("🎉 Всё сделано!", callback_data="noop")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back")])
        await query.edit_message_text("✅ Отметь выполненное:", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data.startswith("done_"):
        task_name = data.replace("done_", "")
        user_data["tasks"][task_name] = True
        save_data({str(user_id): user_data})
        await query.edit_message_text(f"✅ {task_name} выполнена!", reply_markup=await main_menu())
    
    elif data.startswith("done_custom_"):
        idx = int(data.replace("done_custom_", ""))
        user_data["custom_tasks"][idx]["done"] = True
        save_data({str(user_id): user_data})
        await query.edit_message_text(f"✅ {user_data['custom_tasks'][idx]['name']} выполнена!", reply_markup=await main_menu())
    
    elif data == "stats":
        total = sum(1 for task in TASKS if check_day(task["days"])) + len(user_data["custom_tasks"])
        completed = sum(1 for task in TASKS if check_day(task["days"]) and user_data["tasks"].get(task["name"], False))
        completed += sum(1 for ct in user_data["custom_tasks"] if ct.get("done", False))
        percent = int(completed / total * 100) if total > 0 else 0
        text = f"📊 *Статистика:*\n✅ {completed} из {total} ({percent}%)\n🏆 " + "█" * (percent // 10) + "░" * (10 - percent // 10)
        await query.edit_message_text(text, reply_markup=await main_menu(), parse_mode="Markdown")
    
    elif data == "reset":
        for task in TASKS:
            user_data["tasks"][task["name"]] = False
        for ct in user_data["custom_tasks"]:
            ct["done"] = False
        save_data({str(user_id): user_data})
        await query.edit_message_text("🔄 Задачи сброшены!", reply_markup=await main_menu())
    
    elif data == "add_custom":
        context.user_data["custom_step"] = "name"
        await query.edit_message_text(
            "✏️ Введи название задачи:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Отмена", callback_data="back")]])
        )
    
    elif data == "back":
        await query.edit_message_text("Главное меню:", reply_markup=await main_menu())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    step = context.user_data.get("custom_step")
    
    if step == "name":
        context.user_data["custom_name"] = text
        context.user_data["custom_step"] = "time"
        await update.message.reply_text("Введи время в формате ЧЧ:ММ (например: 14:30):")
    
    elif step == "time":
        try:
            datetime.strptime(text, "%H:%M")
            context.user_data["custom_time"] = text
            context.user_data["selected_days"] = None
            await save_custom_task(update, context, user_id)
        except:
            await update.message.reply_text("❌ Неверный формат. Введи ЧЧ:ММ")
    
    else:
        await update.message.reply_text("Используй кнопки меню 👆", reply_markup=await main_menu())

async def days_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if not context.user_data.get("selected_days"):
        context.user_data["selected_days"] = []
    
    data = query.data
    
    if data == "days_every":
        context.user_data["selected_days"] = None
        await save_custom_task(update, context, user_id)
    elif data.startswith("day_"):
        day = int(data.split("_")[1])
        if day in context.user_data["selected_days"]:
            context.user_data["selected_days"].remove(day)
        else:
            context.user_data["selected_days"].append(day)
        await show_days_selection(update, context)
    elif data == "days_done":
        if not context.user_data["selected_days"]:
            await query.edit_message_text("Выбери хотя бы один день")
        else:
            await save_custom_task(update, context, user_id)

async def show_days_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    selected = context.user_data.get("selected_days", [])
    keyboard = []
    row = []
    for i, day in enumerate(DAYS_RU):
        marker = "✅" if i in selected else "⬜"
        row.append(InlineKeyboardButton(f"{marker} {day}", callback_data=f"day_{i}"))
        if i == 1 or i == 3 or i == 5:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("✅ Готово", callback_data="days_done")])
    keyboard.append([InlineKeyboardButton("Каждый день", callback_data="days_every")])
    await update.callback_query.edit_message_text("Выбери дни:", reply_markup=InlineKeyboardMarkup(keyboard))

async def save_custom_task(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    _, user_data = get_user_data(user_id)
    
    new_task = {
        "name": context.user_data["custom_name"],
        "time": context.user_data["custom_time"],
        "days": context.user_data.get("selected_days"),
        "done": False
    }
    
    user_data["custom_tasks"].append(new_task)
    save_data({str(user_id): user_data})
    
    context.user_data["custom_step"] = None
    context.user_data["selected_days"] = None
    
    days_str = "каждый день" if new_task["days"] is None else " ".join(DAYS_RU[d] for d in new_task["days"])
    await update.callback_query.edit_message_text(
        f"✅ Задача «{new_task['name']}» добавлена!\n⏰ {new_task['time']}\n📅 {days_str}",
        reply_markup=await main_menu()
    )

async def reminder_loop(app: Application):
    while True:
        now = datetime.now().strftime("%H:%M")
        data = load_data()
        for user_id_str, user_data in data.items():
            for task in TASKS:
                if task["time"] == now and check_day(task["days"]):
                    if not user_data["tasks"].get(task["name"], False):
                        try:
                            await app.bot.send_message(int(user_id_str), f"⏰ Напоминание: {task['name']}")
                        except:
                            pass
            for ct in user_data.get("custom_tasks", []):
                if ct.get("time") == now:
                    days = ct.get("days")
                    if days is None or datetime.now().weekday() in days:
                        if not ct.get("done", False):
                            try:
                                await app.bot.send_message(int(user_id_str), f"⏰ Напоминание: {ct['name']}")
                            except:
                                pass
        await asyncio.sleep(60)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CallbackQueryHandler(days_callback, pattern="^(day_|days_every|days_done)"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    import threading
    def run_reminders():
        asyncio.run(reminder_loop(app))
    threading.Thread(target=run_reminders, daemon=True).start()
    
    print("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
