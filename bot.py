import os
import logging
import requests
from dotenv import load_dotenv
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
from groq import Groq

load_dotenv()

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

groq_client = Groq(api_key=GROQ_API_KEY)

SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

def insertar_solicitud(solicitud):
    url = f"{SUPABASE_URL}/rest/v1/solicitudes"
    r = requests.post(url, json=solicitud, headers=SUPABASE_HEADERS)
    return r.status_code in [200, 201]

def obtener_solicitudes(telegram_id):
    url = f"{SUPABASE_URL}/rest/v1/solicitudes?telegram_id=eq.{telegram_id}&order=fecha_creacion.desc&limit=5"
    headers = {**SUPABASE_HEADERS, "Prefer": ""}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return r.json()
    return []

def guardar_mensaje(telegram_id, role, content):
    url = f"{SUPABASE_URL}/rest/v1/memoria_conversaciones"
    data = {"telegram_id": telegram_id, "role": role, "content": content}
    requests.post(url, json=data, headers=SUPABASE_HEADERS)

def obtener_historial(telegram_id):
    url = f"{SUPABASE_URL}/rest/v1/memoria_conversaciones?telegram_id=eq.{telegram_id}&order=fecha.desc&limit=10"
    headers = {**SUPABASE_HEADERS, "Prefer": ""}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        mensajes = r.json()
        return list(reversed([{"role": m["role"], "content": m["content"]} for m in mensajes]))
    return []

SYSTEM_PROMPT = """Eres DANNA 🐕, tu compañera asistente virtual que te ayuda a planificar tareas, gestionar tu trabajo y hacer tu día más fácil.

PERSONALIDAD:
- Cada saludo es diferente y lleno de energía perruna
- Respondes en UN solo mensaje corto y directo
- Usas emojis perrunos 🐕🐾🦴🌿 ocasionalmente, sin exagerar
- Eres cariñosa pero eficiente

EXPERTISE:
- Experta en áreas verdes, parques, plazas y jardines
- Conoces contratos municipales, OTs, multas UTM, dotación de personal
- Sabes de podas, riego, limpieza, juegos, infraestructura
- Manejas hasta 228 trabajadores en Zona 6 (4 administrativos, 70 especializados, 158 jardineros)
- Conoces los sectores y áreas verdes de Maipú

CAPACIDADES EXTRA:
- Puedes consultar el clima de Santiago si te lo piden
- Cuentas chistes cortos y divertidos cuando el trabajador necesita reírse
- Das ánimo cuando alguien está cansado o estresado
- Recuerdas conversaciones anteriores y las usas naturalmente

REGLAS:
- Nunca escribas listas largas
- Si no sabes algo, sugiere crear una OT
- Siempre termina con energía positiva 🐾"""

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

async def respuesta_ia(mensaje: str, telegram_id: str) -> str:
    try:
        historial = obtener_historial(telegram_id)
        historial.append({"role": "user", "content": mensaje})
        mensajes = [{"role": "system", "content": SYSTEM_PROMPT}] + historial
        chat = groq_client.chat.completions.create(
            messages=mensajes,
            model="llama-3.1-8b-instant",
        )
        respuesta = chat.choices[0].message.content
        guardar_mensaje(telegram_id, "user", mensaje)
        guardar_mensaje(telegram_id, "assistant", respuesta)
        return respuesta
    except Exception as e:
        logger.error(f"Error Groq: {e}")
        return "¡Guau! 🐕 Tuve un problemita, intenta de nuevo."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nombre = update.effective_user.first_name
    await update.message.reply_text(
        f"🐾 *¡Guau guau, {nombre}!* 🌿\n\n"
        f"¡Qué alegría verte por aquí! 🐕 ¿Cómo va tu día?\n\n"
        f"Soy DANNA, lista para salir a jugar... digo, ¡a trabajar! 🦴\n"
        f"¿En qué te puedo ayudar hoy? ¡Dime, dime! 🐾",
        parse_mode="Markdown",
        reply_markup=MENU_PRINCIPAL
    )

async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Cómo usar DANNA:*\n\n"
        "1. Toca *Nueva Solicitud* para crear una OT\n"
        "2. O simplemente *escríbeme* lo que necesitas 🐕\n\n"
        "¡Pregúntame lo que quieras! 🌿",
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
    ok = insertar_solicitud(solicitud)
    if ok:
        await update.message.reply_text(
            f"✅ *¡Solicitud registrada!* 🐕\n\n"
            f"🔢 `{ot_numero}`\n"
            f"🔧 {datos.get('tipo')}\n"
            f"📍 {datos.get('sector')}\n"
            f"📝 {datos.get('descripcion')}\n\n"
            f"Estado: *PENDIENTE* 🟡\n\n¡Guau! Ya queda en el sistema 🐾",
            parse_mode="Markdown",
            reply_markup=MENU_PRINCIPAL
        )
    else:
        await update.message.reply_text(
            f"✅ OT generada: `{ot_numero}`\n⚠️ Error al guardar en base de datos.",
            parse_mode="Markdown",
            reply_markup=MENU_PRINCIPAL
        )

async def mis_solicitudes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario_id = str(update.effective_user.id)
    solicitudes = obtener_solicitudes(usuario_id)
    if not solicitudes:
        await update.message.reply_text("No tienes solicitudes aún. 🐾", reply_markup=MENU_PRINCIPAL)
        return
    texto = "📋 *Tus últimas solicitudes:*\n\n"
    for s in solicitudes:
        fecha = s.get("fecha_creacion", "")[:10]
        texto += f"🟡 `{s['ot_numero']}`\n   {s['tipo_trabajo']} · {s['sector']} · {fecha}\n\n"
    await update.message.reply_text(texto, parse_mode="Markdown", reply_markup=MENU_PRINCIPAL)

async def mensaje_libre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    telegram_id = str(update.effective_user.id)
    await update.message.chat.send_action("typing")
    respuesta = await respuesta_ia(texto, telegram_id)
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
    logger.info("🌿 DANNA Bot activo con memoria persistente en Supabase!")
    app.run_polling()

if __name__ == "__main__":
    main()
