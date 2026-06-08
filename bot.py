import discord
from discord.ext import commands
import json
import hashlib
import datetime
import logging
import os
import asyncio
from dotenv import load_dotenv
from web3 import Web3
from web3.exceptions import ContractLogicError


# ─────────────────────────────────────────────
#  CONFIGURACIÓN
# ─────────────────────────────────────────────
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
RPC_URL = os.getenv("RPC_URL", "https://rpc.tanenbaum.io")
CHAIN_ID = int(os.getenv("CHAIN_ID", "5700"))
EXPLORER_URL = os.getenv("EXPLORER_URL", "https://tanenbaum.io")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("EduChainAgent")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


# ─────────────────────────────────────────────
#  WEB3 — Conexión a Syscoin Tanenbaum Testnet
# ─────────────────────────────────────────────
w3 = Web3(Web3.HTTPProvider(RPC_URL))

# Cargar ABI del contrato
ABI_PATH = os.path.join(os.path.dirname(__file__), "contract_abi.json")
with open(ABI_PATH, "r") as f:
    CONTRACT_ABI = json.load(f)

# Instancia del contrato (se inicializa después de validar la dirección)
contract = None
if CONTRACT_ADDRESS and CONTRACT_ADDRESS != "0xesto me falta":
    try:
        checksum_address = Web3.to_checksum_address(CONTRACT_ADDRESS)
        contract = w3.eth.contract(address=checksum_address, abi=CONTRACT_ABI)
        logger.info(f"Contrato cargado: {checksum_address}")
    except Exception as e:
        logger.error(f"Error cargando contrato: {e}")
        contract = None


# ─────────────────────────────────────────────
#  BLOCKCHAIN — Funciones de interacción on-chain
# ─────────────────────────────────────────────
async def registrar_en_blockchain(
    docente_id: str, data_hash_hex: str, score_final: float, es_alerta: bool
) -> dict:
    """
    Envía una transacción al smart contract para registrar la evaluación.
    Retorna un dict con tx_hash, block_number, explorer_url, y bloque_contrato.
    Lanza excepciones si falla.
    """
    if contract is None:
        raise ConnectionError(
            "Contrato no configurado. Verifica CONTRACT_ADDRESS en .env"
        )

    if not w3.is_connected():
        raise ConnectionError(
            "No se pudo conectar al nodo RPC. Verifica la conexión a la red Syscoin."
        )

    # Convertir hash SHA-256 (hex string) a bytes32
    # SHA-256 produce 32 bytes = 64 hex chars, compatible con bytes32
    hash_bytes = bytes.fromhex(data_hash_hex)

    # Score a uint16 (multiplicar por 100)
    score_uint16 = int(round(score_final * 100))

    wallet = Web3.to_checksum_address(WALLET_ADDRESS)
    nonce = w3.eth.get_transaction_count(wallet)

    # Estimar gas
    try:
        gas_estimate = contract.functions.registrarEvaluacion(
            docente_id, hash_bytes, score_uint16, es_alerta
        ).estimate_gas({"from": wallet})
    except ContractLogicError as e:
        raise ValueError(f"Contrato rechazó la operación: {e}")
    except Exception as e:
        raise ConnectionError(f"Error estimando gas: {e}")

    # Construir transacción
    txn = contract.functions.registrarEvaluacion(
        docente_id, hash_bytes, score_uint16, es_alerta
    ).build_transaction(
        {
            "from": wallet,
            "nonce": nonce,
            "gas": int(gas_estimate * 1.2),  # +20% margen de seguridad
            "gasPrice": w3.eth.gas_price,
            "chainId": CHAIN_ID,
        }
    )

    # Firmar y enviar
    signed_txn = w3.eth.account.sign_transaction(txn, private_key=PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)

    logger.info(f"[BLOCKCHAIN] Tx enviada: {tx_hash.hex()}")

    # Esperar confirmación (en un thread separado para no bloquear el event loop)
    receipt = await asyncio.get_event_loop().run_in_executor(
        None, lambda: w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    )

    if receipt.status != 1:
        raise RuntimeError(
            f"Transacción fallida. Hash: {tx_hash.hex()}"
        )

    # Obtener el número de bloque del contrato (totalEvaluaciones)
    bloque_contrato = contract.functions.totalEvaluaciones().call()

    tx_hash_str = tx_hash.hex()
    explorer_tx_url = f"{EXPLORER_URL}/tx/0x{tx_hash_str}" if not tx_hash_str.startswith("0x") else f"{EXPLORER_URL}/tx/{tx_hash_str}"

    logger.info(
        f"[BLOCKCHAIN] ✅ Confirmada en bloque #{receipt.blockNumber} | "
        f"Contrato bloque #{bloque_contrato} | Gas usado: {receipt.gasUsed}"
    )

    return {
        "tx_hash": f"0x{tx_hash_str}" if not tx_hash_str.startswith("0x") else tx_hash_str,
        "block_number": receipt.blockNumber,
        "gas_used": receipt.gasUsed,
        "bloque_contrato": bloque_contrato,
        "explorer_url": explorer_tx_url,
    }


async def verificar_hash_onchain(data_hash_hex: str) -> bool:
    """Consulta el contrato para verificar si un hash ya fue registrado."""
    if contract is None:
        raise ConnectionError("Contrato no configurado.")
    hash_bytes = bytes.fromhex(data_hash_hex)
    return contract.functions.verificarHash(hash_bytes).call()


async def obtener_evaluacion_onchain(bloque: int) -> dict:
    """Obtiene los datos de una evaluación por su número de bloque en el contrato."""
    if contract is None:
        raise ConnectionError("Contrato no configurado.")
    result = contract.functions.obtenerEvaluacion(bloque).call()
    return {
        "docenteId": result[0],
        "dataHash": result[1].hex(),
        "scoreFinal": result[2] / 100,
        "timestamp": result[3],
        "alerta": result[4],
    }


def obtener_balance_tsys() -> float:
    """Obtiene el balance real de tSYS de la wallet del agente."""
    if not w3.is_connected():
        return -1
    wallet = Web3.to_checksum_address(WALLET_ADDRESS)
    balance_wei = w3.eth.get_balance(wallet)
    return float(w3.from_wei(balance_wei, "ether"))


def obtener_total_evaluaciones() -> int:
    """Obtiene el total de evaluaciones registradas en el contrato."""
    if contract is None:
        return 0
    try:
        return contract.functions.totalEvaluaciones().call()
    except Exception:
        return 0


# ─────────────────────────────────────────────
#  AGENTSTATE — Estado del agente (ahora híbrido)
# ─────────────────────────────────────────────
class AgentState:
    """
    Estado interno del agente. Combina datos on-chain (balance real,
    total evaluaciones del contrato) con métricas locales de sesión.
    """
    COSTO_ESTIMADO_GAS = 0.001  # Costo estimado por tx en tSYS
    UMBRAL_ALERTA_TSYS = 0.05  # Balance bajo en tSYS reales
    UMBRAL_CRITICO_TSYS = 0.01  # Balance crítico

    def __init__(self):
        self.auditorias_sesion: int = 0
        self.auditorias_aprobadas_sesion: int = 0
        self.auditorias_alerta_sesion: int = 0
        self.cache_ledger: list[dict] = []  # Caché local de la sesión
        self.inicio: datetime.datetime = datetime.datetime.utcnow()

    def estado_salud(self) -> str:
        balance = obtener_balance_tsys()
        if balance < 0:
            return "⚫ DESCONECTADO — Sin conexión al nodo RPC"
        if balance >= self.UMBRAL_ALERTA_TSYS:
            return "🟢 ÓPTIMO"
        if balance >= self.UMBRAL_CRITICO_TSYS:
            return "🟡 DEGRADADO — Balance bajo"
        return "🔴 CRÍTICO — Sin fondos para operar"

    def registrar_en_cache(self, nombre: str, hash_hex: str, score: float, tx_data: dict):
        entrada = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "docente": nombre,
            "hash": hash_hex,
            "score": score,
            "tx_hash": tx_data.get("tx_hash", "N/A"),
            "bloque_chain": tx_data.get("block_number", 0),
            "bloque_contrato": tx_data.get("bloque_contrato", 0),
            "explorer_url": tx_data.get("explorer_url", ""),
        }
        self.cache_ledger.append(entrada)
        return entrada

    def ultimos_registros(self, n: int = 3) -> list[dict]:
        return self.cache_ledger[-n:]

    def reporte_ugel(self) -> dict:
        tasa = (
            round(self.auditorias_aprobadas_sesion / self.auditorias_sesion * 100, 1)
            if self.auditorias_sesion > 0
            else 0
        )
        uptime = str(datetime.datetime.utcnow() - self.inicio).split(".")[0]
        balance = obtener_balance_tsys()
        total_onchain = obtener_total_evaluaciones()

        return {
            "sesion": self.auditorias_sesion,
            "total_onchain": total_onchain,
            "aprobados": self.auditorias_aprobadas_sesion,
            "alertas": self.auditorias_alerta_sesion,
            "tasa_aprobacion": tasa,
            "balance_tsys": balance,
            "estado": self.estado_salud(),
            "uptime": uptime,
        }


# Instancia global
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
#  UI — Select Menu PRO
# ─────────────────────────────────────────────
class ProMenuSelect(discord.ui.Select):
    def __init__(self):
        opciones = [
            discord.SelectOption(
                label="Estado de Salud del Agente",
                description="Balance tSYS real, estado y conexión blockchain",
                emoji="🫀",
                value="salud",
            ),
            discord.SelectOption(
                label="Explorador de Transparencia",
                description="Últimos registros on-chain con links al explorer",
                emoji="🔍",
                value="blockchain",
            ),
            discord.SelectOption(
                label="Reporte Ejecutivo UGEL",
                description="Estadísticas consolidadas (on-chain + sesión)",
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
        emoji="📋",
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
    """Muestra el balance tSYS real y estado operativo del agente."""
    balance = obtener_balance_tsys()
    is_connected = w3.is_connected()
    total_onchain = obtener_total_evaluaciones()

    embed = discord.Embed(
        title="🫀 Estado de Salud — EduChain Agent",
        description="Diagnóstico operativo en tiempo real con datos **on-chain reales**",
        color=color_por_salud(balance),
        timestamp=datetime.datetime.utcnow(),
    )

    # Conexión
    estado_rpc = "✅ Conectado" if is_connected else "❌ Desconectado"
    embed.add_field(
        name="🌐 Nodo RPC",
        value=f"`{RPC_URL}`\nEstado: {estado_rpc}",
        inline=False,
    )

    # Estado general
    embed.add_field(
        name="Estado General",
        value=agente.estado_salud(),
        inline=False,
    )

    # Balance real
    if balance >= 0:
        barra = generar_barra(min(balance / 0.1 * 100, 100))
        embed.add_field(
            name="💰 Balance tSYS (Real)",
            value=f"`{barra}` **{balance:.6f} tSYS**",
            inline=False,
        )
        auditorias_estimadas = int(balance / AgentState.COSTO_ESTIMADO_GAS) if AgentState.COSTO_ESTIMADO_GAS > 0 else "∞"
        embed.add_field(
            name="Auditorías Restantes Estimadas",
            value=f"`~{auditorias_estimadas}` (basado en gas estimado)",
            inline=True,
        )
    else:
        embed.add_field(
            name="💰 Balance tSYS",
            value="⚠️ No se pudo obtener (nodo desconectado)",
            inline=False,
        )

    # Contrato
    contrato_estado = f"`{CONTRACT_ADDRESS}`" if contract else "⚠️ No configurado"
    embed.add_field(name="📜 Contrato", value=contrato_estado, inline=False)
    embed.add_field(name="🔗 Evaluaciones On-Chain", value=f"`{total_onchain}`", inline=True)
    embed.add_field(name="📊 Evaluaciones Sesión", value=f"`{agente.auditorias_sesion}`", inline=True)

    # Uptime
    uptime = str(datetime.datetime.utcnow() - agente.inicio).split(".")[0]
    embed.add_field(name="⏱ Uptime", value=f"`{uptime}`", inline=True)

    embed.set_footer(text=f"EduChain GovTech Auditor • Syscoin Tanenbaum Testnet • Chain ID {CHAIN_ID}")

    await interaction.response.send_message(embed=embed, ephemeral=True)


async def mostrar_blockchain(interaction: discord.Interaction):
    """Muestra los últimos registros on-chain de la sesión."""
    ultimos = agente.ultimos_registros(3)

    embed = discord.Embed(
        title="🔍 Explorador de Transparencia — Audit Trail On-Chain",
        description=f"Últimos registros inmutables en **Syscoin Tanenbaum Testnet** • ODS 16",
        color=0x0FA3B1,
        timestamp=datetime.datetime.utcnow(),
    )

    if not ultimos:
        embed.add_field(
            name="Sin registros en esta sesión",
            value="Adjunta un archivo `.json` para generar el primer registro on-chain.",
            inline=False,
        )
    else:
        for entrada in reversed(ultimos):
            tx_link = f"[Ver en Explorer]({entrada['explorer_url']})" if entrada.get("explorer_url") else "N/A"
            embed.add_field(
                name=f"📦 Bloque #{entrada['bloque_contrato']} — {entrada['docente']}",
                value=(
                    f"**Hash:** `{entrada['hash'][:24]}...`\n"
                    f"**Score:** `{entrada['score']}`\n"
                    f"**Tx:** `{entrada['tx_hash'][:18]}...`\n"
                    f"**Chain Block:** `#{entrada['bloque_chain']}`\n"
                    f"🔗 {tx_link}"
                ),
                inline=False,
            )

    total_onchain = obtener_total_evaluaciones()
    embed.add_field(
        name="Total Evaluaciones On-Chain",
        value=f"`{total_onchain}`",
        inline=True,
    )
    embed.set_footer(text="Registro inmutable • SHA-256 • Syscoin NEVM • EduChain Ledger")

    await interaction.response.send_message(embed=embed, ephemeral=True)


async def mostrar_reporte_ugel(interaction: discord.Interaction):
    """Genera el reporte ejecutivo para directivos UGEL."""
    r = agente.reporte_ugel()

    embed = discord.Embed(
        title="📊 Reporte Ejecutivo — UGEL Stats",
        description="Resumen consolidado para toma de decisiones directivas\n*Datos combinados: blockchain + sesión actual*",
        color=0x2DC653,
        timestamp=datetime.datetime.utcnow(),
    )

    embed.add_field(
        name="🔗 Total On-Chain (histórico)",
        value=f"```{r['total_onchain']} evaluaciones```",
        inline=True,
    )

    if r["sesion"] == 0:
        embed.add_field(
            name="📋 Esta Sesión",
            value="No se han procesado auditorías todavía.",
            inline=False,
        )
    else:
        embed.add_field(name="📋 Auditados (sesión)", value=f"```{r['sesion']} docentes```", inline=True)
        embed.add_field(name="✅ Aprobados", value=f"```{r['aprobados']}```", inline=True)
        embed.add_field(name="⚠️ En Alerta", value=f"```{r['alertas']}```", inline=True)
        embed.add_field(
            name="Tasa de Aprobación",
            value=f"```{r['tasa_aprobacion']}%```",
            inline=False,
        )

        # Clasificación de rendimiento
        if r["tasa_aprobacion"] >= 80:
            clasificacion = "🏆 Institución de Alto Rendimiento"
        elif r["tasa_aprobacion"] >= 60:
            clasificacion = "✅ Rendimiento Satisfactorio"
        else:
            clasificacion = "🚨 Requiere Intervención Urgente"

        embed.add_field(name="Clasificación UGEL", value=clasificacion, inline=False)

    embed.add_field(name="Estado del Agente", value=r["estado"], inline=True)
    embed.add_field(
        name="💰 Balance tSYS",
        value=f"`{r['balance_tsys']:.6f}`" if r["balance_tsys"] >= 0 else "⚠️ N/A",
        inline=True,
    )
    embed.set_footer(text="EduChain GovTech Auditor • Para uso de directivos UGEL/MINEDU")

    await interaction.response.send_message(embed=embed, ephemeral=True)


# ─────────────────────────────────────────────
#  UTILIDADES
# ─────────────────────────────────────────────
def generar_barra(porcentaje: float, largo: int = 10) -> str:
    llenos = int(min(porcentaje, 100) / 100 * largo)
    return "█" * llenos + "░" * (largo - llenos)


def color_por_salud(balance: float) -> int:
    if balance >= AgentState.UMBRAL_ALERTA_TSYS:
        return 0x2DC653   # Verde
    if balance >= AgentState.UMBRAL_CRITICO_TSYS:
        return 0xF4A261   # Naranja
    return 0xE63946       # Rojo


# ─────────────────────────────────────────────
#  COMANDOS
# ─────────────────────────────────────────────
@bot.command()
async def menu(ctx):
    """Muestra el panel principal del agente EduChain."""
    embed = discord.Embed(
        title="⛓️ EduChain GovTech Auditor",
        description=(
            "Sistema de auditoría docente con **registro inmutable en blockchain real**.\n"
            f"Red: **Syscoin Tanenbaum Testnet** (Chain ID: `{CHAIN_ID}`)\n\n"
            "Adjunta un `.json` de evaluación para iniciar o selecciona una función Pro."
        ),
        color=0x0FA3B1,
    )
    embed.add_field(
        name="📄 Formato de archivo esperado",
        value='```json\n{\n  "nombre": "Juan Pérez",\n  "involucramiento": 3.5,\n  "razonamiento": 2.8,\n  "retroalimentacion": 3.1\n}\n```',
        inline=False,
    )

    # Mostrar estado de conexión
    status = "✅ Conectado" if w3.is_connected() else "❌ Desconectado"
    contrato_status = "✅ Cargado" if contract else "⚠️ Pendiente"
    embed.add_field(name="🌐 RPC", value=status, inline=True)
    embed.add_field(name="📜 Contrato", value=contrato_status, inline=True)

    embed.set_footer(text="ODS 4 • ODS 16 • EduChain v3.0 — Blockchain Real")
    view = EduChainView()
    await ctx.send(embed=embed, view=view)


@bot.command()
async def verificar(ctx, hash_hex: str = None):
    """Verifica si un hash de evaluación existe on-chain."""
    if not hash_hex:
        await ctx.send(
            "⚠️ **Uso:** `!verificar <hash_sha256>`\n"
            "Ejemplo: `!verificar a1b2c3d4e5f6...`"
        )
        return

    # Limpiar el hash (quitar 0x si lo tiene)
    hash_hex = hash_hex.replace("0x", "").strip()

    if len(hash_hex) != 64:
        await ctx.send("❌ **Error:** El hash debe tener 64 caracteres hexadecimales (SHA-256).")
        return

    try:
        existe = await verificar_hash_onchain(hash_hex)
        if existe:
            embed = discord.Embed(
                title="✅ Hash Verificado — Registro Encontrado",
                description="Este hash de evaluación **existe en la blockchain**.",
                color=0x2DC653,
            )
            embed.add_field(name="Hash", value=f"`{hash_hex[:32]}...`", inline=False)
            embed.add_field(
                name="Estado",
                value="📜 Registro inmutable confirmado en Syscoin Tanenbaum Testnet",
                inline=False,
            )
        else:
            embed = discord.Embed(
                title="❌ Hash No Encontrado",
                description="Este hash **no existe** en el registro on-chain.",
                color=0xE63946,
            )
            embed.add_field(name="Hash", value=f"`{hash_hex[:32]}...`", inline=False)

        embed.set_footer(text="EduChain Verificador On-Chain")
        await ctx.send(embed=embed)

    except ConnectionError as e:
        await ctx.send(f"⚠️ **Error de conexión:** {e}")
    except Exception as e:
        await ctx.send(f"❌ **Error:** {e}")


@bot.command()
async def balance(ctx):
    """Muestra el balance real de tSYS de la wallet del agente."""
    bal = obtener_balance_tsys()
    if bal >= 0:
        embed = discord.Embed(
            title="💰 Balance del Agente",
            description=f"**{bal:.6f} tSYS**",
            color=0x0FA3B1,
        )
        embed.add_field(name="Wallet", value=f"`{WALLET_ADDRESS}`", inline=False)
        embed.add_field(name="Red", value=f"Syscoin Tanenbaum Testnet", inline=True)
        embed.set_footer(text="EduChain GovTech Auditor")
        await ctx.send(embed=embed)
    else:
        await ctx.send("⚠️ No se pudo obtener el balance. Nodo RPC desconectado.")


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
            await bot.process_commands(message)
            return

        msg_proceso = await message.channel.send(
            "⏳ **Agente procesando...** Ejecutando ETL, generando hash y registrando en blockchain."
        )

        try:
            # ── PASO 1: ETL ──
            raw_data = await archivo.read()
            datos = procesar_evaluacion(raw_data.decode("utf-8"))

            # ── PASO 2: Hash SHA-256 ──
            hash_hex = hashlib.sha256(
                json.dumps(datos, sort_keys=True).encode()
            ).hexdigest()

            nombre = datos.get("nombre", "Docente Desconocido")
            es_alerta = datos["score_final"] < 2.0

            await msg_proceso.edit(
                content="⏳ **Firmando transacción y enviando a Syscoin Tanenbaum Testnet...**"
            )

            # ── PASO 3: Registro On-Chain ──
            tx_data = await registrar_en_blockchain(
                docente_id=nombre,
                data_hash_hex=hash_hex,
                score_final=datos["score_final"],
                es_alerta=es_alerta,
            )

            # ── PASO 4: Actualizar estado local ──
            agente.registrar_en_cache(nombre, hash_hex, datos["score_final"], tx_data)
            agente.auditorias_sesion += 1
            if es_alerta:
                agente.auditorias_alerta_sesion += 1
            else:
                agente.auditorias_aprobadas_sesion += 1

            # ── PASO 5: Embed de resultado ──
            color = 0xE63946 if es_alerta else 0x2DC653
            embed = discord.Embed(
                title="⛓️ Auditoría EduChain — Registrada On-Chain ✅",
                description=f"Evaluación de **{nombre}** registrada de forma **inmutable en blockchain real**.",
                color=color,
                timestamp=datetime.datetime.utcnow(),
            )

            embed.add_field(name="📊 Score Final", value=f"`{datos['score_final']} / 4.0`", inline=True)
            embed.add_field(
                name="📦 Bloque Contrato #",
                value=f"`{tx_data['bloque_contrato']}`",
                inline=True,
            )
            embed.add_field(
                name="🔗 Bloque Chain #",
                value=f"`{tx_data['block_number']}`",
                inline=True,
            )

            embed.add_field(
                name="🔐 Hash SHA-256",
                value=f"`{hash_hex[:32]}...`",
                inline=False,
            )
            embed.add_field(
                name="📝 Tx Hash",
                value=f"`{tx_data['tx_hash'][:32]}...`",
                inline=False,
            )

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

            # Link al explorer
            embed.add_field(
                name="🌐 Ver en Blockchain",
                value=f"[Abrir en Tanenbaum Explorer]({tx_data['explorer_url']})",
                inline=False,
            )

            # Balance restante
            balance = obtener_balance_tsys()
            embed.add_field(
                name="💰 Balance tSYS restante",
                value=f"`{balance:.6f} tSYS` — {agente.estado_salud()}",
                inline=False,
            )

            embed.add_field(
                name="⛽ Gas Usado",
                value=f"`{tx_data['gas_used']}`",
                inline=True,
            )

            embed.set_footer(text="EduChain Ledger • Registro Inmutable • Syscoin NEVM Testnet • ODS 4 & 16")

            await msg_proceso.delete()
            await message.channel.send(embed=embed)

        except ConnectionError as ce:
            await msg_proceso.edit(
                content=f"🌐 **Error de conexión blockchain:** {ce}\n"
                f"Verifica la conexión RPC y que el contrato esté desplegado."
            )
        except ValueError as ve:
            await msg_proceso.edit(
                content=f"❌ **Error de validación:** {ve}\n"
                f"Verifica que el JSON tenga los campos correctos."
            )
        except json.JSONDecodeError:
            await msg_proceso.edit(
                content="❌ **Error:** El archivo no es un JSON válido."
            )
        except Exception as e:
            logger.error(f"Error inesperado: {e}", exc_info=True)
            await msg_proceso.edit(content=f"❌ **Error inesperado:** {e}")

    await bot.process_commands(message)


# ─────────────────────────────────────────────
#  EVENTO ON_READY
# ─────────────────────────────────────────────
@bot.event
async def on_ready():
    is_connected = w3.is_connected()
    balance = obtener_balance_tsys() if is_connected else -1
    total = obtener_total_evaluaciones()

    logger.info(f"{'─'*60}")
    logger.info(f"  ⛓️  EduChain GovTech Auditor — ONLINE (v3.0 Blockchain Real)")
    logger.info(f"  Bot: {bot.user} (ID: {bot.user.id})")
    logger.info(f"  Red: Syscoin Tanenbaum Testnet (Chain ID: {CHAIN_ID})")
    logger.info(f"  RPC: {RPC_URL} — {'✅ Conectado' if is_connected else '❌ Desconectado'}")
    logger.info(f"  Contrato: {CONTRACT_ADDRESS or 'NO CONFIGURADO'}")
    logger.info(f"  Wallet: {WALLET_ADDRESS}")
    logger.info(f"  Balance: {balance:.6f} tSYS" if balance >= 0 else "  Balance: N/A")
    logger.info(f"  Evaluaciones On-Chain: {total}")
    logger.info(f"{'─'*60}")


bot.run(TOKEN)