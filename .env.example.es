# ArchiveBot Ejemplo de configuración de variables de entorno
# Copie este archivo como .env y complete con valores reales

# ====================
# Configuración de Telegram Bot (obligatorio)
# ====================
# Obténgalo de @BotFather
BOT_TOKEN=YOUR_BOT_TOKEN_HERE

# Obtenga su ID de Telegram desde @userinfobot
OWNER_ID=0

# ====================
# Configuración de canal de almacenamiento de Telegram (opcional)
# ====================
# ID de canal de almacenamiento predeterminado (obligatorio)
CHANNEL_DEFAULT=-1001234567890

# ID de canales por tipo de documento (opcional, si no se configura se usa el canal predeterminado)
CHANNEL_TEXT=-1001234567891 # Canal dedicado para texto
CHANNEL_EBOOK=-1001234567892 # Canal dedicado para libros electrónicos
CHANNEL_DOCUMENT=-1001234567893 # Canal dedicado para documentos
CHANNEL_IMAGE=-1001234567894 # Canal dedicado para imágenes
CHANNEL_MEDIA=-1001234567895 # Canal dedicado para archivos multimedia

# El tipo NOTE es especial, es el canal de archivo para notas personales creadas en modo NOTE. Si no se configura, se guardará en el canal TEXT
CHANNEL_NOTE=-1001234567896  # Canal dedicado para notas (opcional)

# Canal de almacenamiento para contenido directo personal (opcional)
CHANNEL_DIRECT_DEFAULT=-1001234567897

# Configuración de mapeo de fuente a canal (prioridad más alta que el mapeo de tipos) debe configurarse en config.yaml
# Configuración de mapeo de etiquetas a canal (máxima prioridad) debe configurarse en config.yaml

# ====================
# Configuración de AI API (opcional)
# ====================

# Selección de proveedor de API (opcional, predeterminado es grok)
AI_API_PROVIDER=

# Clave de API (si usa funciones de AI)
AI_API_KEY=

# Dirección de API (opcional, si no se completa se usa el valor predeterminado)
AI_API_URL=

# Nombre del modelo (opcional)
AI_MODEL=
AI_REASONING_MODEL=

# Configuración de exclusión de contenido de referencia de AI (formato JSON)
# Lista de IDs de canales a excluir, por ejemplo: [-1003497030097]
AI_EXCLUDE_CHANNELS=[]
# Lista de etiquetas a excluir, por ejemplo: ["私密", "草稿"]
AI_EXCLUDE_TAGS=[]

# ====================
# Instrucciones de uso
# ====================
# 1. Copie este archivo como .env
# 2. Complete el BOT_TOKEN y OWNER_ID reales (obligatorio)
# 3. Complete los IDs de canal (cuando necesite habilitar almacenamiento de Telegram)
# 4. Complete AI_API_KEY (cuando necesite usar funciones de AI)
# 5. Agregue .env a .gitignore para evitar la filtración de información sensible

# ====================
# Prioridad
# ====================
# Variables de entorno > configuración de config.yaml
# Si se establecen variables de entorno, se sobrescribirá la configuración correspondiente en config.yaml
