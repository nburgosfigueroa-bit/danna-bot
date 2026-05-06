# 🌿 DANNA Bot - Zona 6 Maipú

Bot de Telegram para gestión de solicitudes de trabajo en áreas verdes.

## Archivos
- `bot.py` — Código principal
- `requirements.txt` — Dependencias
- `Procfile` — Configuración Railway

## Variables de entorno (configurar en Railway)
```
TELEGRAM_TOKEN=tu_token
SUPABASE_URL=tu_url
SUPABASE_ANON_KEY=tu_key
```

## Tabla Supabase requerida
Crear en Supabase > SQL Editor:

```sql
CREATE TABLE solicitudes (
  id SERIAL PRIMARY KEY,
  ot_numero TEXT NOT NULL,
  telegram_id TEXT,
  nombre_usuario TEXT,
  tipo_trabajo TEXT,
  sector TEXT,
  descripcion TEXT,
  foto_url TEXT,
  estado TEXT DEFAULT 'pendiente',
  fecha_creacion TIMESTAMPTZ DEFAULT NOW()
);
```
