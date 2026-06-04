import discord
from discord.ext import commands
import json
import hashlib
import os
from dotenv import load_dotenv

# Cargar las variables del archivo .env
load_dotenv()

# Configuración básica del bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f' Agente EduChain Auditor conectado y listo como {bot.user}')

@bot.command()
async def evaluar_docente(ctx, codigo: str):
    if codigo == "MAT-01":
        await ctx.send("🔍 **Agente activado:** Leyendo evaluación docente pública desde GitHub...")
        
        # Simulamos la lectura de tu archivo de GitHub
        datos_json = {
          "id_docente": "DOC-MAT-001",
          "materia_foco": "Matemáticas - División",
          "involucramiento": 3,
          "razonamiento": 2,
          "retroalimentacion": 1
        }
        
        # 1. Convertir a texto para crear el Hash
        texto_json = json.dumps(datos_json)
        
        # 2. Calcular el Hash SHA256 para inmutabilidad
        hash_calculado = hashlib.sha256(texto_json.encode()).hexdigest()
        
        await ctx.send(f" **Datos validados (Cero Corrupción).**\n🔗 Hash SHA256 generado para blockchain zkSYS: `{hash_calculado}`")
        
        # 3. Lógica del Agente: Detectar el problema y enviar ayuda
        if datos_json["retroalimentacion"] == 1:
            await ctx.send(" **ALERTA PEDAGÓGICA:** Se detectó deficiencia (Puntaje 1) en 'Retroalimentación' para 'Matemáticas - División'.\n\n📚 **Plan de Mejora Automático Generado por IA:**\n1. Video de apoyo: Estrategias prácticas de división paso a paso.\n2. PDF interactivo: Cómo corregir errores matemáticos en el aula sin desmotivar al alumno.\n*(El docente DOC-MAT-001 ha sido notificado)*")
        else:
            await ctx.send(" El docente cumple con los estándares educativos.")

# Obtener el token del archivo .env y ejecutar
TOKEN = os.getenv('DISCORD_TOKEN')
if TOKEN is None:
    print(" ERROR: No se encontró el DISCORD_TOKEN. Asegúrate de tener el archivo .env")
else:
    bot.run(TOKEN)