from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from datetime import datetime

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json

# ================== GOOGLE SHEETS ==================

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# 🔥 FUNCIONA LOCAL E RENDER
if os.environ.get("GOOGLE_CREDENTIALS"):
    credenciais_dict = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
    creds = ServiceAccountCredentials.from_json_keyfile_dict(credenciais_dict, scope)
else:
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        "credenciais.json",
        scope
    )

client = gspread.authorize(creds)
planilha = client.open("REFUGO").sheet1

# ================== TOKEN ==================

TOKEN = os.environ.get("TOKEN")

# ================== GRUPO ==================

GROUP_ID = -5191123192

# ================== ESTADOS ==================

DATA, PLACA, CATEGORIA, QUANTIDADE, CONFIRMAR, RESPONSAVEL = range(6)

# ================== PLACAS ==================

placas = [
    ["QRC-1G60", "QRD-0J81"],
    ["QRE-4J38", "QRE-4J44"],
    ["RBF-7H12", "QRE-0I89"],
    ["JCC-9B27", "SFP-4J08"],
    ["QRE-4J26", "RBF-7H06"],
    ["JCC-9B37", "RBF-7H16"],
    ["RQR-4J50", "SFP-4I75"],
    ["RQP-9C54", "RQR-4J57"],
    ["RQR-4J64", "RQQ-3I52"],
    ["RBF-7H07", "SJE-2I43"],
    ["RQS-0J05", "RQS-0J57"],
    ["RQS-0J63", "RQR-4J76"],
    ["RQR-4J96", "RQR-6I53"],
    ["RQS-2B29", "JCC-9B31"],
    ["SFP-4J14", "JCC-9B16"],
    ["RBF-7H10", "JCC-9B42"],
    ["JCC-9B23", "RQS-0E69"],
    ["SJE-2I50", "SJE-2I44"],
    ["SJE-2I45", "SJE-2I46"]
]

# ================== VASILHAMES ==================

vasilhames = [
    ["600ML", "1L"],
    ["HNK 600ML", "HNK 330ML"],
    ["CAIXA CONCORRENCIA"]
]

# ================== SALVAR ==================

def salvar_dados(data, placa, itens, responsavel):
    for item in itens:
        planilha.append_row([
            data,
            placa,
            item['categoria'],
            item['quantidade'],
            responsavel
        ])

# ================== FLUXO ==================

async def refugo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["itens"] = []

    await update.message.reply_text("📦 Registro de Refugo\n\nVamos começar 👇")
    await update.message.reply_text("Digite a data (dd/mm/aaaa) ou 'hoje':")
    return DATA

async def data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text

    if texto.lower() == "hoje":
        data_formatada = datetime.now().strftime("%d/%m/%Y")
    else:
        data_formatada = texto

    context.user_data["data"] = data_formatada

    await update.message.reply_text(
        "Escolha a placa:",
        reply_markup=ReplyKeyboardMarkup(placas, resize_keyboard=True)
    )
    return PLACA

async def placa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["placa"] = update.message.text

    await update.message.reply_text(
        "Escolha o vasilhame:",
        reply_markup=ReplyKeyboardMarkup(vasilhames, resize_keyboard=True)
    )
    return CATEGORIA

async def categoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["categoria_temp"] = update.message.text
    await update.message.reply_text("Digite a quantidade:")
    return QUANTIDADE

async def quantidade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        await update.message.reply_text("Digite apenas números:")
        return QUANTIDADE

    item = {
        "categoria": context.user_data["categoria_temp"],
        "quantidade": update.message.text
    }

    context.user_data["itens"].append(item)

    botoes = [["SIM", "NÃO"]]
    await update.message.reply_text(
        "Deseja adicionar outro refugo?",
        reply_markup=ReplyKeyboardMarkup(botoes, resize_keyboard=True)
    )
    return CONFIRMAR

async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "SIM":
        await update.message.reply_text(
            "Escolha o vasilhame:",
            reply_markup=ReplyKeyboardMarkup(vasilhames, resize_keyboard=True)
        )
        return CATEGORIA
    else:
        await update.message.reply_text("Digite o nome do responsável:")
        return RESPONSAVEL

async def responsavel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["responsavel"] = update.message.text

    try:
        salvar_dados(
            context.user_data["data"],
            context.user_data["placa"],
            context.user_data["itens"],
            context.user_data["responsavel"]
        )
        status = "✅ Registro salvo"
    except Exception as e:
        print(e)
        status = "❌ Erro ao salvar"

    texto_itens = ""
    for item in context.user_data["itens"]:
        texto_itens += f"\n📦 {item['categoria']}: {item['quantidade']}"

    resposta = f"""
📦 REGISTRO DE REFUGO

📅 Data: {context.user_data['data']}
🚛 Placa: {context.user_data['placa']}
{texto_itens}

👤 Responsável: {context.user_data['responsavel']}

{status}
"""

    await update.message.reply_text(
        resposta,
        reply_markup=ReplyKeyboardRemove()
    )

    await context.bot.send_message(
        chat_id=GROUP_ID,
        text=resposta
    )

    return ConversationHandler.END

# ================== MAIN ==================

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", refugo),
            CommandHandler("refugo", refugo)
        ],
        states={
            DATA: [MessageHandler(filters.TEXT & ~filters.COMMAND, data)],
            PLACA: [MessageHandler(filters.TEXT & ~filters.COMMAND, placa)],
            CATEGORIA: [MessageHandler(filters.TEXT & ~filters.COMMAND, categoria)],
            QUANTIDADE: [MessageHandler(filters.TEXT & ~filters.COMMAND, quantidade)],
            CONFIRMAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar)],
            RESPONSAVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, responsavel)],
        },
        fallbacks=[]
    )

    app.add_handler(conv)

    print("Bot rodando...")
    app.run_polling()

if __name__ == "__main__":
    main()
