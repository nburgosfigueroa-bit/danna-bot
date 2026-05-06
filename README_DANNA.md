# 🐕 AGENTE DANNA - Gestor de Solicitudes de Mantenimiento

Agente inteligente basado en **Groq AI** para gestionar solicitudes de mantenimiento de áreas verdes en Zone 6, Maipú.

## 🎯 Características

✅ **Inteligencia Artificial (Groq)** - Razonamiento avanzado
✅ **Gestión de Solicitudes** - Crear, listar, cerrar trabajos
✅ **Base de Datos Integrada** - 324 áreas verdes de Zone 6
✅ **Mapas Interactivos** - Visualización con advertencias
✅ **Sectores Inseguros** - Identifica zonas de riesgo (KMZ)
✅ **Excel Automático** - Exporta datos de solicitudes
✅ **Notificaciones por Mail** - Confirmaciones automáticas
✅ **Interfaz Telegram** - Acceso desde cualquier dispositivo

## 📋 Datos Incluidos

- **BD Áreas Verdes**: 445 registros (TABLA_AV_ZONA_6.xlsx)
  - Código, característica, nombre, ubicación
  - Superficie, barrio, supervisor asignado
  
- **Sectores Inseguros**: KMZ con polígonos de riesgo
  - Zonas marcadas en rojo
  - Coordenadas geoespaciales

## 🚀 Instalación Rápida

### 1. Copia los archivos a tu PC

```
C:\Users\nburgos\Desktop\DANNA BOT V2\
├── agente_danna.py
├── .env_danna
├── requirements_danna.txt
├── README.md
├── TABLA_AV_ZONA_6.xlsx
└── AV_ZONA_6_Sectores_inseguros.kmz
```

### 2. Instala dependencias

```powershell
cd "C:\Users\nburgos\Desktop\DANNA BOT V2"
pip install -r requirements_danna.txt
```

### 3. Configura el .env_danna

Abre `.env_danna` y reemplaza:
```
TELEGRAM_TOKEN=8703459540:AAH9JZbvgZTXiAMXMWtVGUvw6J3ITHzWZBA
GROQ_API_KEY=gsk_iRLAX2AU_TU_KEY_AQUI
MAIL_USER=dannabotakro@gmail.com
MAIL_PASS=Nbur.2026
```

### 4. Ejecuta el agente

```powershell
python agente_danna.py
```

Deberías ver:
```
2026-05-04 08:30:00 - __main__ - INFO - ✅ Cargadas 445 áreas verdes
2026-05-04 08:30:01 - __main__ - INFO - ✅ Cargados 18 sectores inseguros
2026-05-04 08:30:02 - __main__ - INFO - 🚀 Iniciando AGENTE DANNA...
2026-05-04 08:30:03 - __main__ - INFO - ✅ AGENTE DANNA corriendo...
```

## 📱 Comandos en Telegram

### Crear Solicitud
```
/nueva_solicitud
```
El agente te pregunta:
1. Tipo de trabajo (Poda, Infraestructura, etc.)
2. Código del área (6-315, 6-098, etc.)
3. Observaciones en terreno
4. Responsable (supervisor)

### Ver Pendientes
```
/listar
```
Muestra todas las solicitudes abiertas.

### Exportar Excel
```
/exportar
```
Descarga archivo `solicitudes_danna.xlsx` con todos los datos.

### Ver Mapa
```
/mapa
```
Genera mapa HTML interactivo con:
- 🔴 Sectores inseguros (rojo)
- 🟡 Solicitudes planificadas (amarillo)
- 🔵 En ejecución (azul)
- 🟢 Finalizadas (verde)

### Ayuda
```
/ayuda
```
Muestra guía completa.

## 📊 Estructura de Datos

### Solicitud
```python
{
    'id': 1001,
    'fecha_solicitud': '2026-05-04T08:30:00',
    'tipo': 'Poda',
    'area': '6-315',
    'observaciones': 'Árbol seco, requiere tala',
    'responsable': 'Supervisor Poda',
    'estado': 'Planificado',
    'fecha_realizado': None
}
```

### Estados
- 🟡 **Planificado** - Trabajo programado
- 🔵 **En ejecución** - Supervisor en terreno
- 🟠 **Pendiente** - Requiere atención
- 🟢 **Finalizado** - Trabajo completado

## ⚠️ Sectores Inseguros

El KMZ incluye polígonos de zonas de riesgo. Cuando creas una solicitud en área roja:
```
⚠️ ADVERTENCIA: Esta área está en zona insegura según los reportes.
```

**Recomendación**: Coordina con supervisor antes de ingresar.

## 📧 Notificaciones por Mail

Cada solicitud envía mail a `dannabotakro@gmail.com` con:
- ID de solicitud
- Tipo y ubicación
- Observaciones
- Responsable asignado

## 🗺️ Mapas HTML

Se generan automáticamente en:
```
C:\Users\nburgos\Desktop\DANNA BOT V2\mapa_solicitudes.html
```

Puedes abrirlo en navegador para ver:
- Sectores inseguros en rojo
- Todas las solicitudes por estado
- Zoom y pan interactivo

## 💾 Excel Exportado

Se genera automáticamente en:
```
C:\Users\nburgos\Desktop\DANNA BOT V2\solicitudes_danna.xlsx
```

Contiene columnas:
- ID, Fecha, Tipo, Área, Observaciones, Responsable, Estado, Fecha Realizado

## 🔧 Troubleshooting

### Error: "No module named 'groq'"
```powershell
pip install groq --upgrade
```

### Error: "TELEGRAM_TOKEN is invalid"
- Verifica que el token sea correcto en `.env_danna`
- Asegúrate de que el bot @dannaia_bot esté activo

### Error: "Mail cannot be sent"
- Habilita "Aplicaciones menos seguras" en Gmail
- O usa contraseña de app (recomendado)

### KMZ no carga
- Verifica que `AV_ZONA_6_Sectores_inseguros.kmz` esté en la carpeta
- Comprueba que el archivo no esté corrupto

## 📈 Próximas Mejoras

- [ ] Cargar fotos de evidencia
- [ ] Historial de cambios (audit trail)
- [ ] Reportes por supervisor
- [ ] Integración con Google Drive
- [ ] Dashboard web (no solo Telegram)
- [ ] Estimación de costos automática
- [ ] Alertas por áreas críticas

## 👤 Autor

**Nicolás Burgos Figueroa**
- Email: nburgosfigueroa-bit@github.com
- Municipalidad de Maipú, Zone 6

## 📄 Licencia

MIT

---

**Creado con ❤️ para mejorar la gestión de áreas verdes en Maipú**
