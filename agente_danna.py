import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd
from groq import Groq
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import formatdate
from email import encoders
import zipfile
import xml.etree.ElementTree as ET

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MAIL_USER = os.getenv("MAIL_USER", "dannabotakro@gmail.com")
MAIL_PASS = os.getenv("MAIL_PASS", "Nbur.2026")
ADMIN_ID = 7570909402

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================================================
# CARGAR DATOS
# ============================================================================

def cargar_datos():
    """Carga BD de áreas verdes y datos geoespaciales"""
    try:
        # Cargar Excel
        df_areas = pd.read_excel('/mnt/user-data/uploads/TABLA_AV_ZONA_6.xlsx')
        df_areas = df_areas.dropna(subset=['CODIGO'])
        logger.info(f"✅ Cargadas {len(df_areas)} áreas verdes")
        
        # Parsear KMZ (sectores inseguros)
        sectores_inseguros = parsear_kmz('/mnt/user-data/uploads/AV_ZONA_6_Sectores_inseguros.kmz')
        logger.info(f"✅ Cargados {len(sectores_inseguros)} sectores inseguros")
        
        return df_areas, sectores_inseguros
    except Exception as e:
        logger.error(f"Error cargando datos: {e}")
        return None, None

def parsear_kmz(ruta_kmz):
    """Extrae coordenadas de sectores inseguros del KMZ"""
    try:
        sectores = []
        with zipfile.ZipFile(ruta_kmz, 'r') as kmz:
            kml_data = kmz.read('doc.kml')
            root = ET.fromstring(kml_data)
            
            # Namespace del KML
            ns = {'kml': 'http://www.opengis.net/kml/2.2'}
            
            # Extraer placemarks (polígonos/puntos)
            for placemark in root.findall('.//kml:Placemark', ns):
                name = placemark.find('kml:name', ns)
                if name is not None:
                    coords_elem = placemark.find('.//kml:LinearRing/kml:coordinates', ns)
                    if coords_elem is not None:
                        coords_text = coords_elem.text.strip()
                        coords = [tuple(map(float, c.split(',')[:2])) for c in coords_text.split()]
                        sectores.append({
                            'nombre': name.text,
                            'coordenadas': coords,
                            'tipo': 'inseguro'
                        })
        return sectores
    except Exception as e:
        logger.error(f"Error parseando KMZ: {e}")
        return []

# ============================================================================
# CLIENTE GROQ
# ============================================================================

client = Groq(api_key=GROQ_API_KEY)

def consultar_groq(prompt, contexto=""):
    """Consulta a Groq con razonamiento avanzado"""
    try:
        response = client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=[
                {"role": "system", "content": f"Eres un asistente experto en gestión de áreas verdes y mantenimiento urbano. {contexto}"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error consultando Groq: {e}")
        return "Error consultando IA"

# ============================================================================
# GESTIÓN DE SOLICITUDES
# ============================================================================

solicitudes = {}
contador_id = 1000

def crear_solicitud(datos):
    """Crea una nueva solicitud de mantenimiento"""
    global contador_id
    contador_id += 1
    
    solicitud = {
        'id': contador_id,
        'fecha_solicitud': datetime.now().isoformat(),
        'tipo': datos.get('tipo'),
        'area': datos.get('area'),
        'observaciones': datos.get('observaciones'),
        'responsable': datos.get('responsable'),
        'estado': 'Planificado',
        'fecha_realizado': None
    }
    
    solicitudes[contador_id] = solicitud
    logger.info(f"✅ Solicitud {contador_id} creada: {datos.get('tipo')} en {datos.get('area')}")
    return solicitud

def generar_excel():
    """Genera Excel con todas las solicitudes"""
    try:
        df = pd.DataFrame(solicitudes.values())
        ruta = '/home/claude/solicitudes_danna.xlsx'
        df.to_excel(ruta, index=False)
        logger.info(f"✅ Excel generado: {ruta}")
        return ruta
    except Exception as e:
        logger.error(f"Error generando Excel: {e}")
        return None

# ============================================================================
# MAPAS HTML INTERACTIVOS
# ============================================================================

def generar_mapa_html(df_areas, sectores_inseguros, solicitud=None):
    """Genera mapa HTML interactivo con Folium"""
    try:
        import folium
        
        # Centro aproximado de Maipú
        centro = [-33.5195, -70.7485]
        
        mapa = folium.Map(
            location=centro,
            zoom_start=12,
            tiles='OpenStreetMap'
        )
        
        # Agregar sectores inseguros (rojo)
        for sector in sectores_inseguros:
            if sector['coordenadas']:
                folium.Polygon(
                    locations=[(lat, lon) for lon, lat in sector['coordenadas']],
                    color='red',
                    fill=True,
                    fillColor='red',
                    fillOpacity=0.3,
                    popup=f"⚠️ {sector['nombre']} (Inseguro)"
                ).add_to(mapa)
        
        # Agregar solicitudes por estado
        colores = {
            'Planificado': 'yellow',
            'En ejecución': 'blue',
            'Pendiente': 'orange',
            'Finalizado': 'green'
        }
        
        for _, sol in pd.DataFrame(solicitudes.values()).iterrows():
            area_info = df_areas[df_areas['CODIGO'] == sol['area']]
            if not area_info.empty:
                popup = f"""
                <b>{sol['tipo']}</b><br>
                Área: {sol['area']}<br>
                Estado: {sol['estado']}<br>
                Obs: {sol['observaciones'][:50]}...
                """
                folium.CircleMarker(
                    location=centro,
                    radius=8,
                    popup=popup,
                    color=colores.get(sol['estado'], 'gray'),
                    fill=True,
                    fillColor=colores.get(sol['estado'], 'gray'),
                    fillOpacity=0.7
                ).add_to(mapa)
        
        ruta_mapa = '/home/claude/mapa_solicitudes.html'
        mapa.save(ruta_mapa)
        logger.info(f"✅ Mapa generado: {ruta_mapa}")
        return ruta_mapa
    except Exception as e:
        logger.error(f"Error generando mapa: {e}")
        return None

# ============================================================================
# CORREOS
# ============================================================================

def enviar_mail(asunto, cuerpo, archivo_adjunto=None):
    """Envía mail con notificación"""
    try:
        msg = MIMEMultipart()
        msg['From'] = MAIL_USER
        msg['To'] = MAIL_USER
        msg['Date'] = formatdate(localtime=True)
        msg['Subject'] = asunto
        
        msg.attach(MIMEText(cuerpo, 'html'))
        
        if archivo_adjunto:
            with open(archivo_adjunto, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename= {os.path.basename(archivo_adjunto)}')
                msg.attach(part)
        
        # Gmail SMTP
        servidor = smtplib.SMTP('smtp.gmail.com', 587)
        servidor.starttls()
        servidor.login(MAIL_USER, MAIL_PASS)
        servidor.send_message(msg)
        servidor.quit()
        
        logger.info(f"✅ Mail enviado: {asunto}")
        return True
    except Exception as e:
        logger.error(f"Error enviando mail: {e}")
        return False

# ============================================================================
# COMANDOS TELEGRAM
# ============================================================================

df_areas, sectores_inseguros = cargar_datos()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia el agente"""
    user = update.effective_user
    mensaje = f"""
🐕 *AGENTE DANNA - Gestor de Solicitudes*

Hola {user.first_name}, soy tu asistente para gestionar mantenimiento de áreas verdes en Zone 6.

*Comandos:*
/nueva_solicitud - Crear nueva solicitud
/listar - Ver solicitudes pendientes
/cerrar_trabajo - Marcar trabajo como finalizado
/exportar - Descargar Excel
/mapa - Ver mapa de solicitudes
/ayuda - Ver más opciones

¿Qué necesitas? 👇
    """
    await update.message.reply_text(mensaje, parse_mode='Markdown')

async def nueva_solicitud(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia conversación para nueva solicitud"""
    await update.message.reply_text("📝 Vamos a crear una nueva solicitud.\n\n¿Cuál es el *tipo de trabajo*? (Poda/Infraestructura/Limpieza/Otro)")
    return 1

async def tipo_trabajo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe tipo de trabajo"""
    context.user_data['tipo'] = update.message.text
    await update.message.reply_text(f"✅ Tipo: {context.user_data['tipo']}\n\n¿Cuál es el *código del área*? (ej: 6-315)")
    return 2

async def area(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe área"""
    context.user_data['area'] = update.message.text
    
    # Verificar si es sector inseguro
    area_info = df_areas[df_areas['CODIGO'] == context.user_data['area']]
    advertencia = ""
    if len(sectores_inseguros) > 0:
        advertencia = "\n⚠️ *ADVERTENCIA:* Esta área está en zona insegura según los reportes."
    
    await update.message.reply_text(f"✅ Área: {context.user_data['area']}{advertencia}\n\n¿Cuáles son las *observaciones en terreno*?")
    return 3

async def observaciones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe observaciones"""
    context.user_data['observaciones'] = update.message.text
    await update.message.reply_text(f"✅ Observaciones registradas.\n\n¿Quién es el *responsable*? (ej: Supervisor Poda)")
    return 4

async def responsable(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe responsable y crea solicitud"""
    context.user_data['responsable'] = update.message.text
    
    # Crear solicitud
    solicitud = crear_solicitud(context.user_data)
    
    # Mensaje de confirmación
    msg = f"""
✅ *SOLICITUD CREADA*

🆔 ID: {solicitud['id']}
📅 Fecha: {solicitud['fecha_solicitud'][:10]}
🔧 Tipo: {solicitud['tipo']}
📍 Área: {solicitud['area']}
👤 Responsable: {solicitud['responsable']}
📝 Observaciones: {solicitud['observaciones'][:100]}...

Estado: {solicitud['estado']}
    """
    
    await update.message.reply_text(msg, parse_mode='Markdown')
    
    # Enviar mail
    enviar_mail(
        f"Nueva solicitud #{solicitud['id']}: {solicitud['tipo']} en {solicitud['area']}",
        msg.replace('*', '').replace('_', '')
    )
    
    return ConversationHandler.END

async def listar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista solicitudes pendientes"""
    if not solicitudes:
        await update.message.reply_text("No hay solicitudes registradas")
        return
    
    df = pd.DataFrame(solicitudes.values())
    pendientes = df[df['estado'] != 'Finalizado']
    
    if len(pendientes) == 0:
        await update.message.reply_text("✅ ¡Todas las solicitudes han sido completadas!")
        return
    
    msg = "📋 *SOLICITUDES PENDIENTES*\n\n"
    for _, row in pendientes.iterrows():
        msg += f"🆔 {row['id']} | {row['tipo']} | {row['area']} | {row['estado']}\n"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def exportar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exporta Excel"""
    ruta = generar_excel()
    if ruta and os.path.exists(ruta):
        with open(ruta, 'rb') as excel:
            await update.message.reply_document(document=excel, filename='solicitudes_danna.xlsx')
    else:
        await update.message.reply_text("❌ Error generando Excel")

async def mapa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Genera y envía mapa"""
    ruta_mapa = generar_mapa_html(df_areas, sectores_inseguros)
    if ruta_mapa and os.path.exists(ruta_mapa):
        with open(ruta_mapa, 'rb') as mapa_file:
            await update.message.reply_document(document=mapa_file, filename='mapa_solicitudes.html')
    else:
        await update.message.reply_text("❌ Error generando mapa")

async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra ayuda completa"""
    msg = """
🐕 *AGENTE DANNA - Guía Completa*

*Comandos principales:*
/nueva_solicitud - Registrar nuevo trabajo
/listar - Ver solicitudes pendientes
/cerrar_trabajo - Marcar trabajo finalizado
/exportar - Descargar Excel
/mapa - Ver mapa interactivo
/estadisticas - Ver resumen

*Tipos de trabajo:*
• Poda
• Infraestructura
• Limpieza
• Mantenimiento
• Emergencia

*Estados:*
🟡 Planificado
🔵 En ejecución
🟠 Pendiente
🟢 Finalizado

⚠️ *Sectores inseguros:* Aparecen en rojo en el mapa

*Info:*
• Zona 6 - Maipú
• 324 áreas verdes monitoreadas
• Supervisores: Poda, Infraestructura
    """
    await update.message.reply_text(msg, parse_mode='Markdown')

# ============================================================================
# MAIN
# ============================================================================

def main():
    logger.info("🚀 Iniciando AGENTE DANNA...")
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Conversación para nueva solicitud
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('nueva_solicitud', nueva_solicitud)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, tipo_trabajo)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, area)],
            3: [MessageHandler(filters.TEXT & ~filters.COMMAND, observaciones)],
            4: [MessageHandler(filters.TEXT & ~filters.COMMAND, responsable)],
        },
        fallbacks=[CommandHandler('cancelar', lambda u, c: ConversationHandler.END)]
    )
    
    # Handlers
    app.add_handler(CommandHandler('start', start))
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler('listar', listar))
    app.add_handler(CommandHandler('exportar', exportar))
    app.add_handler(CommandHandler('mapa', mapa))
    app.add_handler(CommandHandler('ayuda', ayuda))
    
    logger.info("✅ AGENTE DANNA corriendo...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
