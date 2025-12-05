import discord
from discord.ext import commands, tasks
from discord import app_commands
from dotenv import load_dotenv
import os, json, time

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Config file path
CONFIG_PATH = "config.json"

# VIP role name (conforme você pediu)
VIP_ROLE_NAME = "AMIGO SUPREMO"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# -----------------------
# CORES: normais + VIP
# -----------------------
cores_quentes = {
    "🔴 Vermelho": "#FF0000",
    "🟠 Laranja": "#FF7A00",
    "🔥 Amarelo": "#FFFF33",
}
cores_frias = {
    "🔵 Azul": "#0066FF",
    "❄️ Azul Escuro": "#003399",
    "🟣 Roxo": "#8000FF",
    "🟦 Ciano": "#00FFFF",
}
cores_vibrantes = {
    "💚 Verde": "#00CC44",
    "💜 Rosa": "#FF66CC",
    "🟡 Bege": "#F5E6C8",
}
cores_pastel = {
    "🪄 Lilás": "#C39BFF",
    "🌸 Rosa Pastel": "#FFB3D9",
    "🌊 Turquesa": "#1ABC9C",
}
cores_vip = {
    "👑 VIP Dourado": "#D4AF37",
    "💎 VIP Diamante": "#6AA9FF",
    "🔹 VIP Safira": "#1ABC9C",
    "❤️ VIP Ruby": "#8B0000",
    "⚪ VIP Platina": "#C0C0C0",
    "🌟 VIP Neon": "#39FF14",
}

# junta tudo (ordem para menu)
todas_as_cores_categorizadas = {
    "🔥 Quentes": cores_quentes,
    "❄️ Frias": cores_frias,
    "🌈 Vibrantes": cores_vibrantes,
    "🪄 Pastel": cores_pastel,
    "👑 VIP": cores_vip,
}
# mapa plano nome -> hex
todas_as_cores = {}
for cat in todas_as_cores_categorizadas.values():
    todas_as_cores.update(cat)


# -----------------------
# UTIL: config (logs channel)
# -----------------------
def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

config = load_config()


# -----------------------
# COOLDOWN simples (em segundos)
# -----------------------
COOLDOWN_SECONDS = 3
_user_cooldowns = {}  # user_id -> last_timestamp

def check_cooldown(user_id):
    last = _user_cooldowns.get(str(user_id), 0)
    now = time.time()
    if now - last < COOLDOWN_SECONDS:
        return False, int(COOLDOWN_SECONDS - (now - last))
    _user_cooldowns[str(user_id)] = now
    return True, 0


# -----------------------
# ON READY (sincroniza comandos)
# -----------------------
@bot.event
async def on_ready():
    print(f"Bot online como {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"Comandos sincronizados: {len(synced)}")
    except Exception as e:
        print("Erro sync:", e)
    # Se existirem views persistentes que queira recarregar, adicionar aqui.
    # (Nós usaremos timeout=None para manter view enquanto o bot rodar.)
    

# -----------------------
# /criar_cargos
# -----------------------
@bot.tree.command(name="criar_cargos", description="Cria todos os cargos de cores e VIP (admins/mods).")
async def criar_cargos(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_roles:
        return await interaction.response.send_message(
            "❌ Você precisa da permissão **Gerenciar Cargos** para usar este comando.",
            ephemeral=True
        )

    await interaction.response.send_message("🎨 Criando cargos... aguarde.", ephemeral=True)
    guild = interaction.guild

    # cria cargos por categoria
    created = []
    for cat_name, cat_dict in todas_as_cores_categorizadas.items():
        for label, hexc in cat_dict.items():
            # limpa emoji do nome para o role (opcional: manter emoji no nome causa caracteres especiais no role)
            role_name = label  # mantendo emoji no nome pois pode ficar legal; se preferir, remova emoji.
            if discord.utils.get(guild.roles, name=role_name):
                continue
            color = discord.Color(int(hexc.replace("#", ""), 16))
            r = await guild.create_role(name=role_name, color=color, reason="Criando roles de cor/painel")
            created.append(r.name)

    await interaction.followup.send(f"✅ Cargos criados/confirmados: {len(created)}", ephemeral=True)


# -----------------------
# VIEW: Menu de seleção (dropdown)
# -----------------------
class MenuCores(discord.ui.Select):
    def __init__(self, include_vip=True):
        # montar opções agrupadas com prefixo de categoria no label
        options = []
        # adicionar opção para remover cor
        options.append(discord.SelectOption(label="🧹 Remover Cor", value="__remover__", description="Remove qualquer cor que você tenha"))
        # adicionar categorias e items
        for cat_name, cat_dict in todas_as_cores_categorizadas.items():
            for label, hexc in cat_dict.items():
                # VIP será verificada no callback
                options.append(discord.SelectOption(label=label, value=label, description=f"{cat_name}"))
        super().__init__(
            placeholder="Escolha uma cor...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="select_cores_painel"
        )

    async def callback(self, interaction: discord.Interaction):
        member = interaction.user
        guild = interaction.guild

        # cooldown
        ok, left = check_cooldown(member.id)
        if not ok:
            return await interaction.response.send_message(f"⏳ Aguarde {left}s antes de trocar de novo.", ephemeral=True)

        escolha = self.values[0]

        # remover quaisquer roles de cor que o membro tenha
        removed = []
        for role in list(member.roles):
            if role.name in todas_as_cores:
                await member.remove_roles(role)
                removed.append(role.name)

        # se pedir para remover
        if escolha == "__remover__":
            # log
            await send_log(guild, f"🧹 **{member}** removeu sua cor (antes: {', '.join(removed) if removed else 'nenhuma'}).")
            return await interaction.response.send_message("🧹 Sua cor foi removida.", ephemeral=True)

        # verificar se é VIP
        if escolha in cores_vip:
            vip_role = discord.utils.get(guild.roles, name=VIP_ROLE_NAME)
            if vip_role not in member.roles:
                return await interaction.response.send_message(
                    "⛔ Você não tem permissão para escolher cores VIP. Adquira o cargo **AMIGO SUPREMO**.",
                    ephemeral=True
                )

        # checar se o cargo existe no servidor
        role = discord.utils.get(guild.roles, name=escolha)
        if not role:
            return await interaction.response.send_message(
                "❌ Cargo não encontrado no servidor. Peça para algum staff usar /criar_cargos primeiro.",
                ephemeral=True
            )

        # adicionar novo role
        await member.add_roles(role)
        await send_log(guild, f"🎨 **{member}** trocou cor para **{escolha}** (removidos: {', '.join(removed) if removed else 'nenhum'}).")
        await interaction.response.send_message(f"✅ Você agora tem a cor **{escolha}**!", ephemeral=True)


class ViewCores(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # timeout None para permanecer enquanto o bot rodar
        self.add_item(MenuCores())


# -----------------------
# /cores (abre menu ephemeral)
# -----------------------
@bot.tree.command(name="cores", description="Abra o menu para escolher/trocar/remover sua cor.")
async def cores(interaction: discord.Interaction):
    await interaction.response.send_message("🎨 Escolha sua cor abaixo:", view=ViewCores(), ephemeral=True)


# -----------------------
# /painel_cores (envia painel fixo para o canal)
# -----------------------
@bot.tree.command(name="painel_cores", description="Envia um painel fixo com o menu de cores (mods/admins).")
async def painel_cores(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_guild and not interaction.user.guild_permissions.manage_roles:
        return await interaction.response.send_message("❌ Você precisa de permissão de administrador ou gerenciar cargos.", ephemeral=True)

    embed = discord.Embed(title="🎨 Painel de Cores",
                          description="Escolha sua cor abaixo. Use /cores se preferir o menu privado.\n\nCategorias:\n" +
                                      "\n".join([f"{k}" for k in todas_as_cores_categorizadas.keys()]),
                          color=discord.Color.blurple())
    embed.set_footer(text="Cores VIP exigem o cargo AMIGO SUPREMO")

    msg = await interaction.channel.send(embed=embed, view=ViewCores())
    await interaction.response.send_message("✅ Painel enviado. Você pode fixar (pin) a mensagem se quiser.", ephemeral=True)


# -----------------------
# /setar_logs (define canal de logs)
# -----------------------
@bot.tree.command(name="setar_logs", description="Define o canal de logs de trocas de cor (use #canal).")
@app_commands.describe(canal="Canal para onde as ações serão registradas (ex: #logs)")
async def setar_logs(interaction: discord.Interaction, canal: discord.TextChannel):
    if not interaction.user.guild_permissions.manage_guild and not interaction.user.guild_permissions.manage_roles:
        return await interaction.response.send_message("❌ Você precisa de permissão de administrador ou gerenciar cargos.", ephemeral=True)

    cfg = load_config()
    guild_cfg = cfg.get(str(interaction.guild.id), {})
    guild_cfg["logs_channel_id"] = canal.id
    cfg[str(interaction.guild.id)] = guild_cfg
    save_config(cfg)
    await interaction.response.send_message(f"✅ Canal de logs definido: {canal.mention}", ephemeral=True)


# -----------------------
# Helper: enviar logs (se configurado)
# -----------------------
async def send_log(guild: discord.Guild, mensagem: str):
    cfg = load_config()
    guild_cfg = cfg.get(str(guild.id), {})
    channel_id = guild_cfg.get("logs_channel_id")
    if not channel_id:
        return  # não configurado: ignora
    channel = guild.get_channel(channel_id)
    if not channel:
        return
    try:
        await channel.send(mensagem)
    except Exception as e:
        print("Erro enviando log:", e)


# -----------------------
# RUN
# -----------------------
if __name__ == "__main__":
    if not TOKEN:
        print("ERRO: Defina DISCORD_TOKEN no .env")
    else:
        bot.run(TOKEN)