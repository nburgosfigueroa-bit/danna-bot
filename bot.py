import os
import logging
import json
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)

load_dotenv()

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ESPERANDO_TIPO, ESPERANDO_SECTOR, ESPERANDO_DESCRIPCION, ESPERANDO_FOTO = range(4)

TIPOS_TRABAJO = [
    "🌳 Poda", "💧 Riego", "🗑️ Limpieza",
    "🛝 Juegos rotos", "🚧 Infraestructura", "⚠️ Otro"
]

MENU_PRINCIPAL = ReplyKeyboardMarkup(
    [["📋 Nueva Solicitud", "📊 Mis Solicitudes"],
     ["❓ Ayuda"]],
    resize_keyboard=True
)

def guardar_en_archivo(solicitud):
    try:
        archivo = "/tmp/solicitudes.json"
        solicitudes = []
        if os.path.exists(archivo):
            with open(archivo, "r") as f:
                solicitudes = json.load(f)
        solicitudes.append(solicitud)
        with open(archivo, "w") as f:
            json.dump(solicitudes, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error guardando: {e}")
        return False

def leer_solicitudes(telegram_id):
    try:
        archivo = "/tmp/solicitudes.json"
        if not os.path.exists(archivo):
            return []
        with open(archivo, "r") as f:
            solicitudes = json.load(f)
        return [s for s in solicitudes if s.get("telegram_id") == telegram_id][-5:]
    except:
        return []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nombre = update.effective_user.first_name
    await update.message.reply_text(
        f"🌿 *¡Bienvenido a DANNA, {nombre}!*\n\n"
        f"Sistema de Gestión Zona 6 - Maipú\n\n"
        f"Usa el menú para crear solicitudes.",
        parse_mode="Markdown",
        reply_markup=MENU_PRINCIPAL
    )

async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Cómo usar DANNA:*\n\n"
        "1. Toca *Nueva Solicitud*\n"
        "2. Selecciona el tipo de trabajo\n"
        "3. Indica el sector\n"
        "4. Describe el problema\n"
        "5. Foto opcional\n\n"
        "✅ Tu OT queda registrada automáticamente",
        parse_mode="Markdown",
        reply_markup=MENU_PRINCIPAL
    )

async def nueva_solicitud(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teclado = ReplyKeyboardMarkup(
        [[t] for t in TIPOS_TRABAJO] + [["❌ Cancelar"]],
        resize_keyboard=True
    )
    await update.message.reply_text(
        "🔧 *Nueva Solicitud*\n\n¿Qué tipo de trabajo es?",
        parse_mode="Markdown",
        reply_markup=teclado
    )
    return ESPERANDO_TIPO

async def recibir_tipo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tipo = update.message.text
    if tipo == "❌ Cancelar":
        await update.message.reply_text("Cancelado.", reply_markup=MENU_PRINCIPAL)
        return ConversationHandler.END
    context.user_data["tipo"] = tipo
    await update.message.reply_text(
        f"✅ *{tipo}*\n\n📍 ¿En qué sector o área verde?",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([["❌ Cancelar"]], resize_keyboard=True)
    )
    return ESPERANDO_SECTOR

async def recibir_sector(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sector = update.message.text
    if sector == "❌ Cancelar":
        await update.message.reply_text("Cancelado.", reply_markup=MENU_PRINCIPAL)
        return ConversationHandler.END
    context.user_data["sector"] = sector
    await update.message.reply_text(
        f"✅ Sector: *{sector}*\n\n📝 Describe el problema:",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([["❌ Cancelar"]], resize_keyboard=True)
    )
    return ESPERANDO_DESCRIPCION

async def recibir_descripcion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    descripcion = update.message.text
    if descripcion == "❌ Cancelar":
        await update.message.reply_text("Cancelado.", reply_markup=MENU_PRINCIPAL)
        return ConversationHandler.END
    context.user_data["descripcion"] = descripcion
    await update.message.reply_text(
        "📸 ¿Tienes foto? Envíala ahora.\nSi no, escribe *sin foto*.",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([["Sin foto"], ["❌ Cancelar"]], resize_keyboard=True)
    )
    return ESPERANDO_FOTO

async def recibir_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await finalizar_solicitud(update, context, tiene_foto=True)
    return ConversationHandler.END

async def sin_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "cancelar" in update.message.text.lower():
        await update.message.reply_text("Cancelado.", reply_markup=MENU_PRINCIPAL)
        return ConversationHandler.END
    await finalizar_solicitud(update, context, tiene_foto=False)
    return ConversationHandler.END

async def finalizar_solicitud(update, context, tiene_foto):
    usuario = update.effective_user
    datos = context.user_data
    now = datetime.now()
    ot_numero = f"OT-{now.strftime('%Y%m%d-%H%M%S')}"
    solicitud = {
        "ot_numero": ot_numero,
        "telegram_id": str(usuario.id),
        "nombre": f"{usuario.first_name} {usuario.last_name or ''}".strip(),
        "tipo": datos.get("tipo", ""),
        "sector": datos.get("sector", ""),
        "descripcion": datos.get("descripcion", ""),
        "tiene_foto": tiene_foto,
        "estado": "pendiente",
        "fecha": now.strftime("%Y-%m-%d %H:%M")
    }
    guardar_en_archivo(solicitud)
    await update.message.reply_text(
        f"✅ *¡Solicitud registrada!*\n\n"
        f"🔢 `{ot_numero}`\n"
        f"🔧 {datos.get('tipo')}\n"
        f"📍 {datos.get('sector')}\n"
        f"📝 {datos.get('descripcion')}\n\n"
        f"Estado: *PENDIENTE* 🟡",
        parse_mode="Markdown",
        reply_markup=MENU_PRINCIPAL
    )

async def mis_solicitudes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario_id = str(update.effective_user.id)
    solicitudes = leer_solicitudes(usuario_id)
    if not solicitudes:
        await update.message.reply_text("No tienes solicitudes aún.", reply_markup=MENU_PRINCIPAL)
        return
    texto = "📋 *Tus últimas solicitudes:*\n\n"
    for s in reversed(solicitudes):
        texto += f"🟡 `{s['ot_numero']}`\n   {s['tipo']} · {s['sector']} · {s['fecha']}\n\n"
    await update.message.reply_text(texto, parse_mode="Markdown", reply_markup=MENU_PRINCIPAL)

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelado.", reply_markup=MENU_PRINCIPAL)
    return ConversationHandler.END

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^📋 Nueva Solicitud$"), nueva_solicitud),
            CommandHandler("nueva", nueva_solicitud)
        ],
        states={
            ESPERANDO_TIPO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_tipo)],
            ESPERANDO_SECTOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_sector)],
            ESPERANDO_DESCRIPCION: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_descripcion)],
            ESPERANDO_FOTO: [
                MessageHandler(filters.PHOTO, recibir_foto),
                MessageHandler(filters.TEXT & ~filters.COMMAND, sin_foto)
            ],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)]
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ayuda", ayuda))
    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.Regex("^📊 Mis Solicitudes$"), mis_solicitudes))
    app.add_handler(MessageHandler(filters.Regex("^❓ Ayuda$"), ayuda))
    logger.info("🌿 DANNA Bot activo!")
    app.run_polling()

if __name__ == "__main__":
    main()
