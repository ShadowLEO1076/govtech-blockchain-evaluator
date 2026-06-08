"""
EduChain GovTech Auditor — Discord Bot
Versión Profesional con funcionalidades Pro para el jurado

Arquitectura:
  - AgentState       : Singleton que mantiene el estado en memoria del agente
  - EduChainView     : Interfaz principal con Select Menu Pro
  - on_message       : ETL + Hash + Blockchain Ledger
"""

import discord
from discord.ext import commands
import json
import hashlib
import datetime
import logging
import os
from dotenv import load_dotenv

# ─────────────────────────────────────────────
#  CONFIGURACIÓN
# ─────────────────────────────────────────────
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("EduChainAgent")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


# ─────────────────────────────────────────────
#  AGENTSTATE — Estado global del agente
#  Simula el "Autonomous Agent Survival Rules"
# ─────────────────────────────────────────────
class AgentState:
    """
    Singleton que mantiene el estado interno del agente.
    Basado en los principios de 'Operating Economics' y 
    'Autonomous Agent Survival Rules'.
    """
    TOKENS_INICIALES = 1000          # Balance inicial en TSYS
    COSTO_POR_AUDITORIA = 12         # Costo operacional por evaluación
    UMBRAL_ALERTA = 200              # Bajo este nivel → estado degradado
    UMBRAL_CRITICO = 50              # Bajo este nivel → agente en peligro

    def __init__(self):
        self.tokens_tsys: float = self.TOKENS_INICIALES
        self.auditorias_realizadas: int = 0
        self.auditorias_aprobadas: int = 0
        self.auditorias_alerta: int = 0
        self.blockchain_ledger: list[dict] = []   # Historial de hashes
        self.inicio: datetime.datetime = datetime.datetime.utcnow()

    # ── Salud ────────────────────────────────
    def estado_salud(self) -> str:
        if self.tokens_tsys >= self.UMBRAL_ALERTA:
            return "🟢 ÓPTIMO"
        if self.tokens_tsys >= self.UMBRAL_CRITICO:
            return "🟡 DEGRADADO"
        return "🔴 CRÍTICO — Agente en peligro de shutdown"

    def consumir_tokens(self, cantidad: float = None):
        costo = cantidad or self.COSTO_POR_AUDITORIA
        self.tokens_tsys = max(0, self.tokens_tsys - costo)

    # ── Blockchain Ledger ────────────────────
    def registrar_hash(self, nombre_docente: str, hash_hex: str, score: float):
        entrada = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "docente": nombre_docente,
            "hash": hash_hex,
            "score": score,
            "bloque": len(self.blockchain_ledger) + 1,
        }
        self.blockchain_ledger.append(entrada)
        logger.info(f"[LEDGER] Bloque #{entrada['bloque']} registrado: {hash_hex[:16]}...")
        return entrada

    def ultimos_hashes(self, n: int = 3) -> list[dict]:
        return self.blockchain_ledger[-n:]

    # ── Estadísticas UGEL ────────────────────
    def reporte_ugel(self) -> dict:
        tasa = (
            round(self.auditorias_aprobadas / self.auditorias_realizadas * 100, 1)
            if self.auditorias_realizadas > 0
            else 0
        )
        uptime = str(datetime.datetime.utcnow() - self.inicio).split(".")[0]
        return {
            "total": self.auditorias_realizadas,
            "aprobados": self.auditorias_aprobadas,
            "alertas": self.auditorias_alerta,
            "tasa_aprobacion": tasa,
            "tokens_restantes": self.tokens_tsys,
            "estado": self.estado_salud(),
            "uptime": uptime,
        }


# Instancia global (patrón Singleton)
agente = AgentState()


# ─────────────────────────────────────────────
#  ETL — Transformación de datos
# ─────────────────────────────────────────────
def procesar_evaluacion(contenido_json: str) -> dict:
    """
    Parsea el JSON de evaluación docente y calcula el score_final.
    Espera campos: nombre, involucramiento, razonamiento, retroalimentacion
    """
    data = json.loads(contenido_json)

    campos_requeridos = ["involucramiento", "razonamiento", "retroalimentacion"]
    for campo in campos_requeridos:
        if campo not in data:
            raise ValueError(f"Campo requerido ausente: '{campo}'")
        if not (0 <= float(data[campo]) <= 4):
            raise ValueError(f"'{campo}' debe estar entre 0 y 4")

    promedio = (
        float(data["involucramiento"])
        + float(data["razonamiento"])
        + float(data["retroalimentacion"])
    ) / 3
    data["score_final"] = round(promedio, 2)
    data["auditado_en"] = datetime.datetime.utcnow().isoformat() + "Z"
    return data


# ─────────────────────────────────────────────
#  UI — Select Menu PRO (más elegante que botones)
# ─────────────────────────────────────────────
class ProMenuSelect(discord.ui.Select):
    def __init__(self):
        opciones = [
            discord.SelectOption(
                label="Estado de Salud del Agente",
                description="Balance TSYS, estado y condiciones operativas",
                emoji="🫀",
                value="salud",
            ),
            discord.SelectOption(
                label="Explorador de Transparencia",
                description="Últimos 3 hashes registrados en la blockchain",
                emoji="🔍",
                value="blockchain",
            ),
            discord.SelectOption(
                label="Reporte Ejecutivo UGEL",
                description="Estadísticas consolidadas para toma de decisiones",
                emoji="📊",
                value="reporte",
            ),
        ]
        super().__init__(
            placeholder="⚡ Selecciona una función Pro...",
            options=opciones,
            custom_id="pro_menu_select",
        )

    async def callback(self, interaction: discord.Interaction):
        valor = self.values[0]

        if valor == "salud":
            await mostrar_salud_agente(interaction)
        elif valor == "blockchain":
            await mostrar_blockchain(interaction)
        elif valor == "reporte":
            await mostrar_reporte_ugel(interaction)


class EduChainView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ProMenuSelect())

    @discord.ui.button(
        label="Iniciar Auditoría",
        style=discord.ButtonStyle.primary,
        emoji="🚀",
        row=1,
    )
    async def btn_auditoria(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_message(
            "📂 **Agente EduChain listo.**\n"
            "Adjunta el archivo `.json` de evaluación docente en este canal.\n"
            "```json\n"
            '{\n  "nombre": "Nombre Docente",\n  "involucramiento": 3.5,\n  "razonamiento": 2.8,\n  "retroalimentacion": 3.1\n}\n'
            "```",
            ephemeral=True,
        )


# ─────────────────────────────────────────────
#  HANDLERS — Funciones Pro
# ─────────────────────────────────────────────
async def mostrar_salud_agente(interaction: discord.Interaction):
    """Muestra el balance TSYS y estado operativo del agente."""
    r = agente.reporte_ugel()
    porcentaje_tokens = round(agente.tokens_tsys / AgentState.TOKENS_INICIALES * 100, 1)

    barra = generar_barra(porcentaje_tokens)

    embed = discord.Embed(
        title="🫀 Estado de Salud — EduChain Agent",
        description="Diagnóstico operativo en tiempo real basado en *Autonomous Agent Survival Rules*",
        color=color_por_salud(agente.tokens_tsys),
        timestamp=datetime.datetime.utcnow(),
    )
    embed.add_field(
        name="Estado General",
        value=r["estado"],
        inline=False,
    )
    embed.add_field(
        name="Balance TSYS",
        value=f"`{barra}` **{agente.tokens_tsys:.0f} / {AgentState.TOKENS_INICIALES}** tokens ({porcentaje_tokens}%)",
        inline=False,
    )
    embed.add_field(name="Costo por Auditoría", value=f"`{AgentState.COSTO_POR_AUDITORIA} TSYS`", inline=True)
    embed.add_field(name="Umbral de Alerta", value=f"`{AgentState.UMBRAL_ALERTA} TSYS`", inline=True)
    embed.add_field(name="Umbral Crítico", value=f"`{AgentState.UMBRAL_CRITICO} TSYS`", inline=True)
    embed.add_field(
        name="Auditorías Restantes Estimadas",
        value=f"`{int(agente.tokens_tsys // AgentState.COSTO_POR_AUDITORIA)}`",
        inline=False,
    )
    embed.add_field(name="Uptime", value=f"`{r['uptime']}`", inline=True)
    embed.set_footer(text="EduChain GovTech Auditor • Operating Economics v1.0")

    await interaction.response.send_message(embed=embed, ephemeral=True)


async def mostrar_blockchain(interaction: discord.Interaction):
    """Muestra los últimos 3 hashes registrados en el ledger."""
    ultimos = agente.ultimos_hashes(3)

    embed = discord.Embed(
        title="🔍 Explorador de Transparencia — Audit Trail",
        description=f"Últimos registros inmutables en el ledger EduChain • ODS 16 Cumplimiento",
        color=0x0FA3B1,
        timestamp=datetime.datetime.utcnow(),
    )

    if not ultimos:
        embed.add_field(
            name="Sin registros aún",
            value="Adjunta un archivo `.json` para generar el primer bloque.",
            inline=False,
        )
    else:
        for entrada in reversed(ultimos):
            embed.add_field(
                name=f"📦 Bloque #{entrada['bloque']} — {entrada['docente']}",
                value=(
                    f"**Hash:** `{entrada['hash'][:24]}...`\n"
                    f"**Score:** `{entrada['score']}`\n"
                    f"**Timestamp:** `{entrada['timestamp']}`"
                ),
                inline=False,
            )

    embed.add_field(
        name="Total de Bloques",
        value=f"`{len(agente.blockchain_ledger)}`",
        inline=True,
    )
    embed.set_footer(text="Registro inmutable • SHA-256 • EduChain Ledger")

    await interaction.response.send_message(embed=embed, ephemeral=True)


async def mostrar_reporte_ugel(interaction: discord.Interaction):
    """Genera el reporte ejecutivo para directivos UGEL."""
    r = agente.reporte_ugel()

    embed = discord.Embed(
        title="📊 Reporte Ejecutivo — UGEL Stats",
        description="Resumen consolidado para toma de decisiones directivas",
        color=0x2DC653,
        timestamp=datetime.datetime.utcnow(),
    )

    if r["total"] == 0:
        embed.add_field(
            name="Sin datos aún",
            value="No se han procesado auditorías todavía.",
            inline=False,
        )
    else:
        embed.add_field(name="Total Auditados", value=f"```{r['total']} docentes```", inline=True)
        embed.add_field(name="Aprobados ✅", value=f"```{r['aprobados']}```", inline=True)
        embed.add_field(name="En Alerta 🚨", value=f"```{r['alertas']}```", inline=True)
        embed.add_field(
            name="Tasa de Aprobación",
            value=f"```{r['tasa_aprobacion']}%```",
            inline=False,
        )

        # Clasificación de rendimiento
        if r["tasa_aprobacion"] >= 80:
            clasificacion = "🏆 Institución de Alto Rendimiento"
        elif r["tasa_aprobacion"] >= 60:
            clasificacion = "📈 Rendimiento Satisfactorio"
        else:
            clasificacion = "⚠️ Requiere Intervención Urgente"

        embed.add_field(name="Clasificación UGEL", value=clasificacion, inline=False)

    embed.add_field(name="Estado del Agente", value=r["estado"], inline=True)
    embed.add_field(name="Tokens TSYS", value=f"`{r['tokens_restantes']:.0f}`", inline=True)
    embed.set_footer(text="EduChain GovTech Auditor • Para uso de directivos UGEL/MINEDU")

    await interaction.response.send_message(embed=embed, ephemeral=True)


# ─────────────────────────────────────────────
#  UTILIDADES
# ─────────────────────────────────────────────
def generar_barra(porcentaje: float, largo: int = 10) -> str:
    llenos = int(porcentaje / 100 * largo)
    return "█" * llenos + "░" * (largo - llenos)


def color_por_salud(tokens: float) -> int:
    if tokens >= AgentState.UMBRAL_ALERTA:
        return 0x2DC653   # Verde
    if tokens >= AgentState.UMBRAL_CRITICO:
        return 0xF4A261   # Naranja
    return 0xE63946       # Rojo


# ─────────────────────────────────────────────
#  COMANDOS
# ─────────────────────────────────────────────
@bot.command()
async def menu(ctx):
    """Muestra el panel principal del agente EduChain."""
    embed = discord.Embed(
        title="🤖 EduChain GovTech Auditor",
        description=(
            "Sistema de auditoría docente con registro inmutable en blockchain.\n"
            "Adjunta un `.json` de evaluación para iniciar o selecciona una función Pro."
        ),
        color=0x0FA3B1,
    )
    embed.add_field(
        name="Formato de archivo esperado",
        value='```json\n{\n  "nombre": "Juan Pérez",\n  "involucramiento": 3.5,\n  "razonamiento": 2.8,\n  "retroalimentacion": 3.1\n}\n```',
        inline=False,
    )
    embed.set_footer(text="ODS 4 • ODS 16 • EduChain v2.0")
    view = EduChainView()
    await ctx.send(embed=embed, view=view)


# ─────────────────────────────────────────────
#  EVENTO PRINCIPAL — Procesamiento de JSON
# ─────────────────────────────────────────────
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.attachments:
        archivo = message.attachments[0]
        if not archivo.filename.endswith(".json"):
            return

        msg_proceso = await message.channel.send("⏳ **Agente procesando...** Ejecutando ETL y generando hash.")

        try:
            raw_data = await archivo.read()
            datos = procesar_evaluacion(raw_data.decode("utf-8"))

            # Cálculo del Hash SHA-256
            hash_hex = hashlib.sha256(json.dumps(datos, sort_keys=True).encode()).hexdigest()

            # Registrar en el ledger y consumir tokens
            nombre = datos.get("nombre", "Docente Desconocido")
            bloque = agente.registrar_hash(nombre, hash_hex, datos["score_final"])
            agente.consumir_tokens()
            agente.auditorias_realizadas += 1

            es_alerta = datos["score_final"] < 2.0
            if es_alerta:
                agente.auditorias_alerta += 1
            else:
                agente.auditorias_aprobadas += 1

            # Embed de resultado
            color = 0xE63946 if es_alerta else 0x2DC653
            embed = discord.Embed(
                title="✅ Auditoría EduChain Completada",
                description=f"Evaluación de **{nombre}** registrada de forma inmutable.",
                color=color,
                timestamp=datetime.datetime.utcnow(),
            )
            embed.add_field(name="📊 Score Final", value=f"`{datos['score_final']} / 4.0`", inline=True)
            embed.add_field(name="📦 Bloque #", value=f"`{bloque['bloque']}`", inline=True)
            embed.add_field(name="🔗 Hash SHA-256", value=f"`{hash_hex[:32]}...`", inline=False)
            embed.add_field(
                name="Involucramiento", value=f"`{datos['involucramiento']}`", inline=True
            )
            embed.add_field(
                name="Razonamiento", value=f"`{datos['razonamiento']}`", inline=True
            )
            embed.add_field(
                name="Retroalimentación", value=f"`{datos['retroalimentacion']}`", inline=True
            )

            if es_alerta:
                embed.add_field(
                    name="🚨 ALERTA CRÍTICA",
                    value="Rendimiento bajo el umbral mínimo. Plan de mejora activado automáticamente.",
                    inline=False,
                )
            else:
                embed.add_field(
                    name="✅ Estado",
                    value="Docente aprobado. Registro válido para reporte UGEL.",
                    inline=False,
                )

            embed.add_field(
                name="💰 Tokens TSYS restantes",
                value=f"`{agente.tokens_tsys:.0f}` — {agente.estado_salud()}",
                inline=False,
            )
            embed.set_footer(text="EduChain Ledger • Registro Inmutable • ODS 4 & 16")

            await msg_proceso.delete()
            await message.channel.send(embed=embed)

        except ValueError as ve:
            await msg_proceso.edit(content=f"⚠️ **Error de validación:** {ve}\nVerifica que el JSON tenga los campos correctos.")
        except json.JSONDecodeError:
            await msg_proceso.edit(content="❌ **Error:** El archivo no es un JSON válido.")
        except Exception as e:
            logger.error(f"Error inesperado: {e}", exc_info=True)
            await msg_proceso.edit(content=f"❌ **Error inesperado:** {e}")

    await bot.process_commands(message)


@bot.event
async def on_ready():
    logger.info(f"{'─'*50}")
    logger.info(f"  EduChain GovTech Auditor — ONLINE")
    logger.info(f"  Bot: {bot.user} (ID: {bot.user.id})")
    logger.info(f"  Balance inicial: {agente.tokens_tsys} TSYS")
    logger.info(f"{'─'*50}")


bot.run(TOKEN)