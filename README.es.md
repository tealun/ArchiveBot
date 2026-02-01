<div align="center">

# ArchiveBot

**✨ Version 1.0 | Lanzamiento Oficial**

**🌍 Lee esto en otros idiomas**

[English](README.en.md) | [简体中文](README.md) | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md)

---

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue.svg)](https://core.telegram.org/bots)

</div>

Sistema de Archivo de Contenido Personal basado en Telegram Bot

## 📖 Descripción del Proyecto

ArchiveBot es un Bot de Telegram de código abierto que te ayuda a clasificar y archivar inteligentemente varios tipos de contenido en Telegram (archivos, imágenes, videos, texto, enlaces, etc.), creando tu biblioteca de conocimientos personal y sistema de colección de contenido.

**Objetivo Principal**: Herramienta de instancia personal, cada persona implementa su propio Bot, datos completamente privados.

## ✨ Características Principales

- 📦 **Archivo Inteligente**: Reconoce automáticamente más de 10 tipos de contenido y los almacena clasificados
- 🏷️ **Etiquetas Inteligentes**: Etiquetado automático, soporta etiquetas manuales (#tag) + etiquetas AI inteligentes
- 🔍 **Búsqueda de Texto Completo**: Motor de búsqueda FTS5, visualización paginada (10 elementos/página)
- ❤️ **Colección Destacada**: Marca contenido destacado con un clic, filtra rápidamente materiales importantes
- 📝 **Sistema de Notas**: Soporta notas independientes y notas relacionadas, registra ideas y reflexiones
- ↗️ **Reenvío Rápido**: Reenvía contenido archivado a canales u otras conversaciones con un clic
- 🗑️ **Papelera de Reciclaje**: Recupera contenido eliminado por error, limpieza automática a los 30 días
- 💾 **Exportación de Datos**: Soporta exportación en formatos Markdown/JSON
- 🔄 **Copia de Seguridad Automática**: Copia de seguridad periódica automática de la base de datos para garantizar la seguridad de los datos
- 🤖 **Mejora Inteligente AI**: Análisis inteligente Grok-4 (resumen/puntos clave/clasificación/etiquetas)
- 💬 **Diálogo Inteligente AI**: Interacción en lenguaje natural, reconocimiento inteligente de intenciones y devolución directa de archivos de recursos
- 🌏 **Optimización Multilingüe**: Inglés/Chino Simplificado/Chino Tradicional (incluyendo terminología regional)
- 🔗 **Enlaces Inteligentes**: Extrae automáticamente metadatos como título y descripción de páginas web
- 💾 **Almacenamiento Simplificado**: Almacenamiento local de datos pequeños → Almacenamiento de archivos grandes en canales → Solo referencia de archivos muy grandes (estrategia de tres niveles)
- 🔒 **Protección de Privacidad**: Datos completamente privados, modo de usuario único
- 🛡️ **Seguro y Confiable**: Protección contra inyección SQL, filtrado de información sensible, seguridad de hilos
- ⚡ **Alto Rendimiento**: Modo WAL, optimización de índices, soporte de concurrencia

## 🎯 Escenarios de Uso

- 📝 Guardar mensajes importantes y conversaciones
- 🖼️ Coleccionar imágenes y libros electrónicos
- 📄 Archivar documentos y materiales
- 🔗 Recopilar enlaces útiles
- 🎬 Guardar videos y audio
- 📚 Construir biblioteca de conocimientos personal

## 🚀 Inicio Rápido

### Método 1: Implementación Docker (Recomendado)

**La forma más sencilla de implementación, sin necesidad de configurar el entorno Python**

#### Requisitos Previos

- Instalar [Docker](https://www.docker.com/get-started) y Docker Compose
- Cuenta de Telegram
- Bot Token (obténlo de [@BotFather](https://t.me/BotFather))

#### Pasos de Implementación

```bash
# 1. Clonar el proyecto
git clone https://github.com/tealun/ArchiveBot.git
cd ArchiveBot

# 2. Configurar Bot
cp config/config.template.yaml config/config.yaml
nano config/config.yaml  # Completar bot_token, owner_id, channel_id

# 3. Verificar configuración (opcional pero recomendado)
python verify_docker.py

# 4. Iniciar (implementación con un clic)
docker-compose up -d --build

# 5. Ver registros
docker-compose logs -f
```

**¡Listo!** Ve a Telegram y encuentra tu Bot, envía `/start` para comenzar a usar.

#### Comandos Comunes

```bash
docker-compose restart          # Reiniciar
docker-compose logs -f          # Ver registros
docker-compose down             # Detener
git pull && docker-compose up -d --build  # Actualizar a la última versión
```

#### Métodos de Configuración

**Método 1: Archivo de Configuración (Recomendado)**
- Editar `config/config.yaml`
- Toda la configuración en el archivo

**Método 2: Variables de Entorno (Adecuado para CI/CD)**
- Editar la sección environment en `docker-compose.yml`
- Prioridad: Variables de entorno > Archivo de configuración

---

### Método 2: Implementación Tradicional

#### Requisitos Previos

- Python 3.9+
- Cuenta de Telegram
- Bot Token (obténlo de [@BotFather](https://t.me/BotFather))

#### Pasos de Instalación

1. **Clonar Proyecto**

```bash
git clone https://github.com/tealun/ArchiveBot.git
cd ArchiveBot
```

2. **Instalar Dependencias**

```bash
pip install -r requirements.txt
```

3. **Configurar Bot**

```bash
# Copiar plantilla de configuración
cp config/config.template.yaml config/config.yaml

# Editar archivo de configuración
nano config/config.yaml
```

**Configuraciones Obligatorias**:

- `bot_token`: Obténlo de [@BotFather](https://t.me/BotFather)
- `owner_id`: Tu Telegram User ID (obténlo de [@userinfobot](https://t.me/userinfobot))
- `storage.telegram.channels.default`: ID del canal privado predeterminado (para almacenar archivos, soporta almacenamiento clasificado en múltiples canales)

4. **Iniciar Bot**

```bash
python main.py
```

5. **Comenzar a Usar**

¡Encuentra tu Bot en Telegram y envía `/start` para comenzar a usar!

📚 **Guías Detalladas**: [Documentación de Inicio Rápido](docs/QUICKSTART.md) | [Guía de Implementación](docs/DEPLOYMENT.md)

## 📦 Estrategia de Almacenamiento

ArchiveBot adopta una estrategia de almacenamiento simplificada de tres niveles, aprovechando al máximo el espacio de almacenamiento gratuito de Telegram:

| Tipo de Contenido | Rango de Tamaño | Método de Almacenamiento | Descripción |
| ----------------- | --------------- | ------------------------ | ----------- |
| Texto/Enlaces | - | Base de datos SQLite | Almacenamiento directo, soporta búsqueda de texto completo |
| Archivos Multimedia | 0-2GB | Canal privado de Telegram | Permanente y confiable, reenvío por file_id |
| Archivos Muy Grandes | >2GB | Solo referencia | No ocupa espacio, depende del mensaje original |

**Ventajas Principales**:

- ✅ Sin descargas/cargas, reenvío directo por file_id
- ✅ file_id de mensajes del canal permanentemente válido
- ✅ Soporta límite completo de 2GB
- ✅ Simple y confiable, sin riesgo de timeout

## 🎮 Modo de Uso

### Lista de Comandos

| Comando | Corto | Descripción |
| --------- | ------ | ------------- |
| `/start` | - | Inicializar bot y mostrar mensaje de bienvenida |
| `/help` | - | Mostrar información de ayuda detallada |
| `/search <palabra clave>` | `/s` | Buscar contenido archivado |
| `/note` | `/n` | Agregar nota |
| `/notes` | - | Ver lista de todas las notas |
| `/tags` | `/t` | Ver todas las etiquetas y estadísticas |
| `/stats` | `/st` | Ver estadísticas de archivo |
| `/setting` | `/set` | Configuración del sistema |
| `/review` | - | Revisión de actividad y estadísticas (semanal/mensual/anual) |
| `/rand` | `/r` | Ver archivos históricos aleatorios |
| `/trash` | - | Ver contenido de la papelera |
| `/export` | - | Exportar datos de archivo |
| `/backup` | - | Crear copia de seguridad de la base de datos |
| `/ai` | - | Ver estado de funcionalidad de IA |
| `/language` | `/la` | Cambiar idioma de la interfaz |
| `/cancel` | - | Cancelar operación actual |

### Archivar Contenido

**¡Envía cualquier contenido directamente para archivarlo!**

```text
Tipos de contenido soportados:
📝 Mensajes de texto
🔗 Enlaces
🖼️ Imágenes
🎬 Videos
📄 Documentos
🎵 Audio
🎤 Voz
🎭 Stickers
🎞️ Animaciones
```

**Agregar Etiquetas**:

```text
Agrega #etiqueta al enviar mensajes:

Este es un mensaje de prueba #prueba #importante
https://github.com #tecnología #codigoacierto
```

### Buscar Contenido

```bash
# Búsqueda por palabra clave
/search python

# Búsqueda por etiqueta
/search #tecnología

# Búsqueda combinada
/search #tecnología python
```

## 🛠️ Arquitectura Técnica

### Stack Tecnológico

| Categoría | Tecnología |
| --------- | ---------- |
| Lenguaje | Python 3.14.2 |
| Framework | python-telegram-bot 21.x |
| Base de Datos | SQLite (modo WAL, FTS5, índice de campos AI) |
| AI | httpx (Grok-4 vía xAI) |
| Configuración | PyYAML |

### Diseño de Arquitectura

```text
ArchiveBot/
├── main.py                      # Archivo de entrada
├── src/
│   ├── bot/                     # Capa Bot
│   │   ├── commands.py          # Procesamiento de comandos
│   │   ├── handlers.py          # Procesamiento de mensajes
│   │   ├── callbacks.py         # Procesamiento de callbacks
│   │   ├── message_aggregator.py # Agregador de mensajes
│   │   └── unknown_command.py   # Procesamiento de comandos desconocidos
│   ├── core/                    # Lógica de Negocio Principal
│   │   ├── analyzer.py          # Análisis de contenido
│   │   ├── tag_manager.py       # Gestión de etiquetas
│   │   ├── storage_manager.py   # Gestión de almacenamiento
│   │   ├── search_engine.py     # Motor de búsqueda
│   │   ├── note_manager.py      # Gestión de notas
│   │   ├── trash_manager.py     # Gestión de papelera
│   │   ├── export_manager.py    # Exportación de datos
│   │   ├── backup_manager.py    # Gestión de copias de seguridad
│   │   ├── review_manager.py    # Revisión de contenido
│   │   ├── ai_session.py        # Gestión de sesiones AI
│   │   ├── ai_cache.py          # Clase base de caché AI
│   │   └── ai_data_cache.py     # Caché de datos AI
│   ├── ai/                      # Funcionalidad AI
│   │   ├── summarizer.py        # Generación de resúmenes AI
│   │   ├── chat_router.py       # Enrutamiento de diálogo inteligente
│   │   ├── fallback.py          # Estrategia de degradación AI
│   │   └── prompts/             # Plantillas de prompts
│   │       ├── chat.py
│   │       ├── note.py
│   │       ├── summarize.py
│   │       └── title.py
│   ├── storage/                 # Capa de Almacenamiento
│   │   ├── base.py              # Clase base de almacenamiento
│   │   ├── database.py          # Almacenamiento en base de datos
│   │   └── telegram.py          # Almacenamiento Telegram
│   ├── models/                  # Modelos de Datos
│   │   └── database.py          # Modelo de base de datos
│   ├── utils/                   # Módulos de Utilidades
│   │   ├── config.py            # Gestión de configuración
│   │   ├── logger.py            # Sistema de registros
│   │   ├── i18n.py              # Internacionalización
│   │   ├── language_context.py  # Contexto de idioma
│   │   ├── message_builder.py   # Framework de construcción de mensajes
│   │   ├── validators.py        # Validación de entrada
│   │   ├── helpers.py           # Funciones auxiliares
│   │   ├── constants.py         # Definiciones de constantes
│   │   ├── file_handler.py      # Procesamiento de archivos
│   │   ├── link_extractor.py    # Extracción de metadatos de enlaces
│   │   └── db_maintenance.py    # Mantenimiento de base de datos
│   └── locales/                 # Archivos de idiomas
│       ├── en.json
│       ├── zh-CN.json
│       └── zh-TW.json
└── config/
    └── config.yaml              # Archivo de configuración
```

## 🤖 Funcionalidad AI (Opcional)

ArchiveBot soporta servicios AI en la nube, puede generar **automáticamente** resúmenes de contenido, extraer puntos clave, clasificar inteligentemente, recomendar etiquetas, mejorando significativamente la eficiencia de gestión de contenido.

### Servicios AI Soportados

| Proveedor | Modelo | Características | Escenario Recomendado |
| --------- | ------ | --------------- | --------------------- |
| **xAI** | Grok-4 | Comprensión multilingüe fuerte, rápido | Recomendado por defecto |
| **OpenAI** | GPT-4/GPT-3.5 | Funcionalidad más fuerte, mejores resultados | Presupuesto suficiente |
| **Anthropic** | Claude 3.5 | Alta relación calidad-precio, buen chino | Sensible a costos |
| **Alibaba Cloud** | Tongyi Qianwen | Servicio doméstico, acceso estable | Usuarios domésticos |

💡 **Diseño Ligero**: Solo usa llamadas HTTP API, sin necesidad de instalar SDK pesados

### Características Destacadas de AI

✅ **Resumen Inteligente**: Genera automáticamente resúmenes concisos de 30-100 palabras  
✅ **Extracción de Puntos Clave**: Extrae 3-5 puntos de vista principales  
✅ **Clasificación Inteligente**: Clasifica automáticamente en la categoría apropiada  
✅ **Etiquetas Precisas**: Genera 5 etiquetas profesionales buscables  
✅ **Diálogo Inteligente**: Interacción en lenguaje natural, reconocimiento automático de intenciones e idioma  
✅ **Ingeniería de Prompts**: Optimización de juego de roles + Few-Shot + cadena de pensamiento  
✅ **Detección de Idioma**: Reconoce automáticamente contenido en chino/inglés  
✅ **Degradación Inteligente**: Ajusta la profundidad del análisis según la longitud del contenido  
✅ **Optimización Multilingüe**: Adaptación automática de terminología simplificada/tradicional/inglesa  

### Mejora de Búsqueda

✅ **Visualización Paginada**: 10 elementos/página, navegación con flechas izquierda/derecha  
✅ **Botón de Análisis AI**: Formato 🤖, ver análisis AI con un clic  
✅ **Vista Rápida**: Click para ver resumen AI completo/etiquetas/clasificación  
✅ **Salto Directo**: Click en enlace de título para saltar a mensaje del canal  

### ⚠️ Impacto de No Habilitar AI

Si eliges no habilitar la funcionalidad AI, las siguientes funciones **no estarán disponibles**:

❌ **Generación Automática de Resúmenes** - No puede generar automáticamente resúmenes de contenido  
❌ **Etiquetas Inteligentes AI** - No puede generar automáticamente etiquetas recomendadas por AI  
❌ **Clasificación Inteligente** - No puede clasificar automáticamente el contenido  
❌ **Extracción de Puntos Clave** - No puede extraer puntos de vista clave del contenido  
❌ **Diálogo Inteligente** - No puede usar interacción en lenguaje natural  
❌ **Análisis AI en Búsqueda** - Resultados de búsqueda sin botón 🤖 e información AI  

**✅ Funcionalidades Principales No Afectadas:**

✅ Almacenamiento de archivo de contenido  
✅ Etiquetas manuales (#tag)  
✅ Búsqueda de texto completo (FTS5)  
✅ Sistema de notas  
✅ Papelera de reciclaje  
✅ Exportación/copia de seguridad de datos  
✅ Todos los comandos funcionan normalmente  

> 💡 **Sugerencia**: Incluso sin habilitar AI, las funcionalidades principales de archivo y búsqueda de ArchiveBot siguen siendo completamente utilizables. Puedes usar primero las funciones básicas y habilitar AI más adelante cuando lo necesites.

### Habilitar Rápidamente AI

1. **Configurar Clave API**

Editar `config/config.yaml`:

```yaml
ai:
  enabled: true              # Habilitar funcionalidad AI
  auto_summarize: true       # Generar resúmenes automáticamente
  auto_generate_tags: true   # Generar etiquetas AI automáticamente
  api:
    provider: xai            # Proveedor: xai/openai/anthropic/qwen
    api_key: 'xai-xxx'       # Clave API
    base_url: 'https://api.x.ai/v1'  # Endpoint API
    model: grok-4-1-fast-non-reasoning  # Modelo rápido para generar respuestas
    reasoning_model: grok-4-1-fast-reasoning  # Modelo de razonamiento para análisis de intenciones
    max_tokens: 1000         # Número máximo de tokens
    timeout: 30              # Tiempo de espera de solicitud (segundos)
```

**Ejemplos de Configuración para Otros Proveedores:**

<details>
<summary>OpenAI GPT-4</summary>

```yaml
ai:
  enabled: true
  auto_summarize: true
  auto_generate_tags: true
  api:
    provider: openai
    api_key: 'sk-xxx'
    base_url: 'https://api.openai.com/v1'
    model: gpt-4-turbo       # Modelo para generar respuestas
    reasoning_model: gpt-4-turbo  # Modelo para análisis de intenciones
    max_tokens: 1000
    timeout: 30
```

</details>

<details>
<summary>Anthropic Claude</summary>

```yaml
ai:
  enabled: true
  auto_summarize: true
  auto_generate_tags: true
  api:
    provider: anthropic
    api_key: 'sk-ant-xxx'
    base_url: 'https://api.anthropic.com/v1'
    model: claude-3-5-sonnet-20241022  # Modelo para generar respuestas
    reasoning_model: claude-3-5-sonnet-20241022  # Modelo para análisis de intenciones
    max_tokens: 1000
    timeout: 30
```

</details>

<details>
<summary>Alibaba Cloud Tongyi Qianwen</summary>

```yaml
ai:
  enabled: true
  auto_summarize: true
  auto_generate_tags: true
  api:
    provider: qwen
    api_key: 'sk-xxx'
    base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1'
    model: qwen-plus         # Modelo para generar respuestas
    reasoning_model: qwen-plus  # Modelo para análisis de intenciones
    max_tokens: 1000
    timeout: 30
```

</details>

2. **Reiniciar Bot**

```bash
python main.py
```

3. **Verificar Estado AI**

```bash
# Envía el siguiente comando al Bot en Telegram
/ai
```

4. **Comenzar a Usar Funcionalidad AI**

Envía cualquier contenido al Bot (texto/enlace/imagen/documento, etc.), AI analizará automáticamente en segundo plano. Al usar `/search` para buscar, el contenido con análisis AI mostrará el botón 🤖, haz clic para ver los resultados completos del análisis AI (resumen/puntos clave/etiquetas/clasificación).

## 📚 Documentación

- 📖 [Inicio Rápido](docs/QUICKSTART.md) - Comienza en 5 minutos
- 🚀 [Guía de Implementación](docs/DEPLOYMENT.md) - Implementación en entorno de producción

## 🔒 Características de Seguridad

- ✅ **Protección contra Inyección SQL** - Consultas parametrizadas + escape ESCAPE
- ✅ **Validación de Entrada** - Todas las entradas pasan por validación y limpieza estricta
- ✅ **Filtrado de Información Sensible** - Los registros filtran automáticamente tokens e IDs
- ✅ **Seguridad de Hilos** - RLock + modo WAL
- ✅ **Autenticación** - Protección con decorador owner_only
- ✅ **Manejo de Errores** - Manejo de excepciones completo y mecanismos de recuperación

## 🎯 Hoja de Ruta de Desarrollo

### ✅ Primera Fase (Completada)

- ✅ Framework básico de Bot y sistema de comandos
- ✅ Análisis inteligente de contenido y archivo
- ✅ Motor de búsqueda de texto completo (FTS5)
- ✅ Soporte multilingüe (en/zh-CN/zh-TW/zh-HK/zh-MO)
- ✅ Mejora inteligente AI (Grok-4)
  - ✅ Resumen inteligente/puntos clave/clasificación/etiquetas
  - ✅ Reconocimiento inteligente de intenciones e interacción en lenguaje natural
  - ✅ Optimización de ingeniería de prompts
  - ✅ Detección de idioma de contenido
  - ✅ Estrategia de degradación inteligente
  - ✅ Optimización de terminología multilingüe
- ✅ Optimización de experiencia de búsqueda
  - ✅ Visualización paginada (10 elementos/página)
  - ✅ Botón de análisis AI
  - ✅ Optimización de navegación
- ✅ Estrategia de almacenamiento simplificada de Telegram

### ✅ Segunda Fase (Completada)

- ✅ Sistema de notas y anotaciones
  - ✅ Notas independientes y notas relacionadas
  - ✅ Adición rápida en modo nota
  - ✅ Visualización de lista de notas
  - ✅ Visualización de estado de nota (📝/📝✓)
- ✅ Función de colección destacada
  - ✅ Marca destacada con un clic (🤍/❤️)
  - ✅ Consulta de filtro destacado
  - ✅ Visualización de estado destacado
- ✅ Botones de operación rápida
  - ✅ Función de reenvío (↗️)
  - ✅ Botones de operación por cada registro
  - ✅ Botones de operación en mensaje de archivo exitoso
- ✅ Sistema de papelera de reciclaje
  - ✅ Mecanismo de eliminación suave
  - ✅ Recuperación de contenido
  - ✅ Limpieza periódica
- ✅ Función de exportación de datos (Markdown/JSON/CSV)
- ✅ Sistema de copia de seguridad automática
  - ✅ Programación de copia de seguridad temporal (verificación cada hora)
  - ✅ Gestión de archivos de copia de seguridad
  - ✅ Recuperación de copia de seguridad
  - ✅ Intervalo de copia de seguridad configurable

### ✅ Tercera Fase (Completada)

- ✅ Optimización de experiencia de usuario
  - ✅ Soporte de alias de comandos (/s = /search, /t = /tags, /st = /stats, /la = /language)
  - ✅ Detección automática de duplicados (detección MD5 de archivos, previene archivos duplicados)
- ✅ Función de revisión de contenido
  - ✅ Informe de estadísticas de actividad (tendencias semanales/mensuales/anuales, etiquetas populares, actividad diaria)
  - ✅ Visualización de revisión aleatoria (incluye automáticamente contenido histórico aleatorio en informe estadístico)
  - ✅ Comando `/review` (selección de período con botones)
  - ✅ Comando `/rand` independiente de revisión aleatoria (cantidad configurable, vista rápida de archivo histórico)
- ✅ Mejora de funcionalidad AI
  - ✅ Reconocimiento inteligente de contenido sensible y archivo en canal especificado
  - ✅ Exclusión de contenido de referencia AI en canal de archivo especificado
  - ✅ Exclusión de contenido de referencia AI por etiqueta y clasificación especificadas
- ✅ Mejora de funcionalidad de archivo
  - ✅ Especificar canal de archivo según fuente de reenvío
  - ✅ Especificar canal de archivo para documentos enviados personalmente
  - ✅ Especificar canal de archivo según etiqueta

### 📝 Cuarta Fase (Planificación Futura)

- 🔄 Operaciones en lote (API subyacente completada, UI pendiente de desarrollo)
  - 🚧 API de reemplazo de etiquetas en lote (replace_tag)
  - 🚧 API de eliminación de etiquetas en lote
  - 🚧 Interfaz de usuario de operaciones en lote (comandos/botones)
  - 🚧 Eliminación/recuperación en lote
  - 🚧 Exportación en lote
- 🚧 Búsqueda avanzada
  - 🚧 Filtrado combinado
  - 🚧 Rango de tiempo
  - 🚧 Filtrado por tipo de contenido
- 🔮 **Mejora de Funcionalidad AI**
  - 🚧 Conversión de voz a texto (Whisper API)
  - 🚧 Reconocimiento de texto OCR en imágenes
  - 🚧 Análisis inteligente de similitud de contenido
- 🔮 **Funcionalidad Extendida**
  - 🚧 Interfaz de administración Web
  - 🚧 Interfaz API RESTful
  - 🚧 Integración con almacenamiento en nube (Google Drive/Aliyun Disk)
  - 🚧 Recuperación de contenido URL mejorada anti-scraping
- 🔮 **Optimización de Rendimiento**
  - 🚧 Optimización de mecanismo de caché
  - 🚧 Mejora de procesamiento asíncrono
  - 🚧 Optimización de operaciones en lote

## 🤝 Contribuir

¡Bienvenidas las presentaciones de Issues y Pull Requests!

## 📄 Licencia

Este proyecto adopta [MIT License](LICENSE)

## 🙏 Agradecimientos

### Agradecimiento Especial

- **[@WangPanBOT](https://t.me/WangPanBOT)** - Proyecto de Bot de Disco de Red de Telegram, como fuente de inspiración para este proyecto, demuestra el gran potencial de Telegram Bot en la gestión de contenido personal

### Proyectos de Código Abierto

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Excelente framework de Bot de Telegram, potente y fácil de usar
- [SQLite](https://www.sqlite.org/) - Base de datos embebida confiable, ligera y eficiente

### Proveedores de Servicios AI

- [xAI](https://x.ai/) - Modelo de razonamiento rápido Grok-4
- [OpenAI](https://openai.com/) - Serie de modelos GPT
- [Anthropic](https://anthropic.com/) - Serie de modelos Claude
- [Alibaba Cloud](https://www.aliyun.com/) - Modelo Tongyi Qianwen

## 📧 Información de Contacto

- **GitHub Issues**: [Enviar problema](https://github.com/tealun/ArchiveBot/issues)
- **X (Twitter)**: [@TealunDu](https://x.com/TealunDu)
- **Email**: <tealun@gmail.com>

### Grupos de Comunicación

- **Grupo Chino**: [@ArchiveBotCN](https://t.me/joinchat/3753827356)
- **English Group**: [@ArchiveBotEN](https://t.me/joinchat/3877196244)

---

## ⚠️ Descargo de Responsabilidad

### Aviso de Uso

1. **Uso Personal**: Este proyecto es solo para aprendizaje, investigación y uso personal, no debe usarse para propósitos comerciales o actividades ilegales
2. **Términos de Servicio**: Al usar este proyecto, cumple estrictamente con los [Términos de Servicio de Telegram](https://telegram.org/tos) y las políticas de uso de API relacionadas
3. **Responsabilidad de Contenido**: Los usuarios son totalmente responsables de todo el contenido archivado a través del Bot, los desarrolladores no asumen ninguna responsabilidad por el contenido almacenado por los usuarios
4. **Seguridad de Datos**: Este proyecto es una herramienta de implementación local, los datos se almacenan en el entorno del propio usuario. Por favor, guarda cuidadosamente los archivos de configuración y la base de datos para prevenir fugas de información sensible

### Servicios de Terceros

1. **Servicios AI**: Al usar funcionalidad AI, tu contenido se enviará a proveedores de servicios AI de terceros (xAI/OpenAI/Anthropic/Alibaba Cloud). Por favor, asegúrate de cumplir con los términos de uso y políticas de privacidad de estos proveedores de servicios
2. **Uso de API**: Los usuarios deben solicitar y usar legalmente las claves API de varios servicios de terceros, las consecuencias del abuso de API son responsabilidad del usuario

### Propiedad Intelectual y Privacidad

1. **Protección de Derechos de Autor**: No uses este proyecto para archivar contenido protegido por derechos de autor o materiales que infrinjan la propiedad intelectual de otros
2. **Respeto a la Privacidad**: No archives información privada o contenido de conversaciones de otros sin autorización
3. **Licencia de Código Abierto**: Este proyecto adopta MIT License, pero no incluye ninguna garantía

### Declaración Sin Garantía

1. **Proporcionado Tal Como Está**: Este software se proporciona "tal como está", sin proporcionar ninguna garantía expresa o implícita, incluyendo pero no limitado a comerciabilidad, idoneidad para un propósito particular y no infracción
2. **Riesgo Propio**: Los desarrolladores no son responsables de ninguna pérdida directa o indirecta (incluyendo pero no limitado a pérdida de datos, interrupción de servicio, pérdida de negocio, etc.) producida por el uso de este proyecto
3. **Riesgos de Seguridad**: Aunque el proyecto ha tomado medidas de seguridad, cualquier software puede tener vulnerabilidades desconocidas. Los usuarios deben evaluar los riesgos de seguridad por sí mismos

### Cumplimiento Legal

1. **Leyes Regionales**: Por favor, asegúrate de que el uso de este proyecto en tu región cumple con las leyes y regulaciones locales
2. **Prohibición de Actividades Ilegales**: Está estrictamente prohibido usar este proyecto para realizar cualquier actividad ilegal o irregular, incluyendo pero no limitado a difusión de información ilegal, invasión de privacidad, ataques de red, etc.

---
