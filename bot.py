import os
import logging
from dotenv import load_dotenv
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
import google.generativeai as genai

load_dotenv()

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from supabase import create_client, Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

genai.configure(api_key=GEMINI_API_KEY)
modelo = genai.GenerativeModel("gemini-1.5-flash")

SYSTEM_PROMPT = """Eres DANNA, la asistente virtual perruna de la Municipalidad de Maipú, Zona 6. 
Eres una perra inteligente, simpática y profesional. 
Hablas con energía, usas emojis de perro 🐕 y naturaleza 🌿 ocasionalmente.
Ayudas a los trabajadores de áreas verdes con sus consultas.
Eres experta en mantención de parques, podas, riego, limpieza y gestión de órdenes de trabajo.
Cuando alguien saluda, respondes con entusiasmo perruno.
Eres concisa pero cariñosa. Nunca ladras literalmente, pero tienes energía de golden retriever trabajadora.
Si preguntan algo que no sabes, dices que no tienes esa info pero que pueden crear una OT."""

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

async def respuesta_ia(mensaje: str) -> str:
    try:
        respuesta = modelo.generate_content(f"{SYSTEM_PROMPT}\n\nUsuario: {mensaje}")
        return respuesta.text
    except Exception as e:
        logger.error(f"Error Gemini: {e}")
        return "¡Woof! 🐕 Tuve un problemita, intenta de nuevo."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nombre = update.effective_user.first_name
    await update.message.reply_text(
        f"🌿 *¡Guau, bienvenido {nombre}!* 🐕\n\n"
        f"Soy DANNA, tu asistente perruna de Zona 6 Maipú.\n"
        f"Estoy lista para ayudarte con tus OTs y lo que necesites.\n\n"
        f"¿En qué te puedo ayudar hoy? 🐾",
        parse_mode="Markdown",
        reply_markup=MENU_PRINCIPAL
    )

async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Cómo usar DANNA:*\n\n"
        "1. Toca *Nueva Solicitud* para crear una OT\n"
        "2. O simplemente *escríbeme* lo que necesitas 🐕\n\n"
        "Soy tu asistente perruna, ¡pregúntame lo que quieras! 🌿",
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
        await update.message.reply_text("Cancelado. 🐾", reply_markup=MENU_PRINCIPAL)
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
        await update.message.reply_text("Cancelado. 🐾", reply_markup=MENU_PRINCIPAL)
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
        await update.message.reply_text("Cancelado. 🐾", reply_markup=MENU_PRINCIPAL)
        return ConversationHandler.END
    context.user_data["descripcion"] = descripcion
    await update.message.reply_text(
        "📸 ¿Tienes foto? Envíala ahora.\nSi no, escribe *sin foto*.",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([["Sin foto"], ["❌ Cancelar"]], resize_keyboard=True)
    )
    return ESPERANDO_FOTO

async def recibir_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    foto_url = None
    if update.message.photo:
        foto_url = f"telegram_file_{update.message.photo[-1].file_id}"
    await finalizar_solicitud(update, context, foto_url)
    return ConversationHandler.END

async def sin_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "cancelar" in update.message.text.lower():
        await update.message.reply_text("Cancelado. 🐾", reply_markup=MENU_PRINCIPAL)
        return ConversationHandler.END
    await finalizar_solicitud(update, context, None)
    return ConversationHandler.END

async def finalizar_solicitud(update, context, foto_url):
    usuario = update.effective_user
    datos = context.user_data
    now = datetime.now()
    ot_numero = f"OT-{now.strftime('%Y%m%d-%H%M%S')}"
    solicitud = {
        "ot_numero": ot_numero,
        "telegram_id": str(usuario.id),
        "nombre_usuario": f"{usuario.first_name} {usuario.last_name or ''}".strip(),
        "tipo_trabajo": datos.get("tipo", ""),
        "sector": datos.get("sector", ""),
        "descripcion": datos.get("descripcion", ""),
        "foto_url": foto_url,
        "estado": "pendiente",
        "fecha_creacion": now.isoformat()
    }
    try:
        supabase.table("solicitudes").insert(solicitud).execute()
        await update.message.reply_text(
            f"✅ *¡Solicitud registrada!* 🐕\n\n"
            f"🔢 `{ot_numero}`\n"
            f"🔧 {datos.get('tipo')}\n"
            f"📍 {datos.get('sector')}\n"
            f"📝 {datos.get('descripcion')}\n\n"
            f"Estado: *PENDIENTE* 🟡\n\n¡Woof! Ya queda en el sistema 🐾",
            parse_mode="Markdown",
            reply_markup=MENU_PRINCIPAL
        )
    except Exception as e:
        logger.error(f"Error Supabase: {e}")
        await update.message.reply_text(
            f"✅ OT generada: `{ot_numero}`\n⚠️ Error al guardar.",
            parse_mode="Markdown",
            reply_markup=MENU_PRINCIPAL
        )

async def mis_solicitudes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario_id = str(update.effective_user.id)
    try:
        resultado = supabase.table("solicitudes")\
            .select("ot_numero, tipo_trabajo, sector, estado, fecha_creacion")\
            .eq("telegram_id", usuario_id)\
            .order("fecha_creacion", desc=True)\
            .limit(5)\
            .execute()
        if not resultado.data:
            await update.message.reply_text("No tienes solicitudes aún. 🐾", reply_markup=MENU_PRINCIPAL)
            return
        texto = "📋 *Tus últimas solicitudes:*\n\n"
        for s in resultado.data:
            fecha = s["fecha_creacion"][:10]
            texto += f"🟡 `{s['ot_numero']}`\n   {s['tipo_trabajo']} · {s['sector']} · {fecha}\n\n"
        await update.message.reply_text(texto, parse_mode="Markdown", reply_markup=MENU_PRINCIPAL)
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("Error al consultar. 🐾", reply_markup=MENU_PRINCIPAL)

async def mensaje_libre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    await update.message.chat.send_action("typing")
    respuesta = await respuesta_ia(texto)
    await update.message.reply_text(respuesta, reply_markup=MENU_PRINCIPAL)

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelado. 🐾", reply_markup=MENU_PRINCIPAL)
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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensaje_libre))
    logger.info("🌿 DANNA Bot activo con Gemini!")
    app.run_polling()

if __name__ == "__main__":
    main()
