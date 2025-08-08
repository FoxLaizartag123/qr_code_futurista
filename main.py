#!/usr/bin/env python3
"""
    Bot Telegram: Gerador Ultra QR Code - Futurista
    Roda em PythonAnywhere (polling). Usa python-telegram-bot v20+ (sync).
    Requisitos: python-telegram-bot>=20.0 pillow qrcode requests
    Sete a variável de ambiente BOT_TOKEN com o token do seu bot.
"""
import os
import io
import logging
from PIL import Image, ImageDraw
import qrcode
import qrcode.image.svg
import requests
from telegram import (
        Bot, Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove, InputMediaPhoto
    )
from telegram.ext import (
        Application, ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext,
        CallbackQueryHandler, ConversationHandler
    )
from telegram.error import BadRequest

    # Configuração do Logging
logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
logger = logging.getLogger(__name__)

    # Estados da Conversação
(
        CHOOSING_ACTION,
        TYPING_TEXT,
        CHOOSING_COLOR,
        UPLOADING_LOGO,
        UPLOADING_BG,
        CHOOSING_SIZE,
        GENERATING
    ) = range(7)

    # Predefinições padrão
DEFAULTS = {
        "qr_size": 1024,  # px (quadrado)
        "fill_color": "#0A84FF",  # azul futurista
        "back_color": "#FFFFFF",  # branco
        "logo_data": None,
        "bg_data": None,
        "data": "",
        "format": "PNG"
    }

    # Funções para teclados inline
def main_menu_keyboard():
        """
        Cria o teclado inline principal com opções para gerar, configurar, upload e ajuda.
        """
        kb = [
            [InlineKeyboardButton("⚡ Gerar QR", callback_data="gen_start"),
             InlineKeyboardButton("🎛️ Configurar", callback_data="config")],
            [InlineKeyboardButton("📁 Upload Logo", callback_data="upload_logo"),
             InlineKeyboardButton("🖼️ Upload Fundo", callback_data="upload_bg")],
            [InlineKeyboardButton("⬇️ Baixar último", callback_data="download_last"),
             InlineKeyboardButton("❓ Ajuda", callback_data="help")],
        ]
        return InlineKeyboardMarkup(kb)

def config_keyboard():
        """
        Cria o teclado inline para configurações (cor e tamanho).
        """
        kb = [
            [InlineKeyboardButton("🎨 Cor", callback_data="cfg_color"),
             InlineKeyboardButton("🔲 Tamanho", callback_data="cfg_size")],
            [InlineKeyboardButton("🔙 Voltar", callback_data="back_main")]
        ]
        return InlineKeyboardMarkup(kb)

def color_keyboard():
        """
        Cria o teclado inline para seleção de cores.
        """
        colors = [
                ("💙 Azul Futurista", "#0A84FF"), ("💚 Verde Neon", "#39FF14"), ("🧡 Laranja Solar", "#FF9500"),
                ("❤️ Vermelho Carmim", "#FF0033"), ("💜 Roxo Real", "#6A0DAD"), ("💛 Amarelo Ouro", "#FFD700"),
                ("🩵 Azul Céu", "#87CEEB"), ("🩷 Rosa Choque", "#FF69B4"), ("🤎 Marrom Café", "#4B3621"),
                ("🖤 Preto Absoluto", "#000000"), ("⚪ Branco Neve", "#FFFFFF"), ("🩶 Cinza Prata", "#C0C0C0"),
                ("🌊 Azul Marinho", "#000080"), ("🌱 Verde Musgo", "#8A9A5B"), ("🍊 Laranja Tangerina", "#FFA500"),
                ("🍓 Vermelho Morango", "#FC4C4E"), ("🍇 Roxo Uva", "#800080"), ("🌻 Amarelo Girassol", "#FFDA03"),
                ("💎 Azul Safira", "#0F52BA"), ("🌿 Verde Floresta", "#228B22"), ("🔥 Laranja Lava", "#FF4500"),
                ("🍒 Vermelho Cereja", "#DE3163"), ("🔮 Roxo Místico", "#9B30FF"), ("🌟 Amarelo Canário", "#FFFF99"),
                ("🌀 Azul Turquesa", "#40E0D0"), ("🥬 Verde Limão", "#32CD32"), ("🧡 Laranja Pêssego", "#FFDAB9"),
                ("🩸 Vermelho Sangue", "#8A0707"), ("🪻 Lilás Lavanda", "#E6E6FA"), ("🥚 Amarelo Creme", "#FFFDD0"),
                ("🌌 Azul Noturno", "#191970"), ("🍃 Verde Jade", "#00A86B"), ("🍯 Laranja Mel", "#FFC87C"),
                ("🍅 Vermelho Tomate", "#FF6347"), ("🪐 Roxo Ametista", "#9966CC"), ("🌼 Amarelo Pastel", "#FAFAD2"),
                ("🏝 Azul Caribe", "#1E90FF"), ("🌳 Verde Folha", "#4CAF50"), ("🥭 Laranja Dourado", "#FFB347"),
                ("🍎 Vermelho Maçã", "#FF0800"), ("🦄 Roxo Orquídea", "#DA70D6"), ("🟨 Amarelo Mostarda", "#FFDB58"),
                ("💠 Azul Gelo", "#AFEEEE"), ("🥦 Verde Erva", "#6B8E23"), ("🍂 Laranja Outono", "#D2691E"),
                ("🚗 Vermelho Ferrari", "#FF2800"), ("🎆 Roxo Púrpura", "#800080"), ("🌤 Amarelo Sol", "#FFEA00"),
                ("🌊 Azul Petróleo", "#005F6A"), ("🪴 Verde Abacate", "#568203"), ("🥕 Laranja Cenoura", "#ED9121"),
                ("🎯 Vermelho Escarlate", "#FF2400"), ("🎨 Roxo Magenta", "#FF00FF"), ("🌽 Amarelo Milho", "#FBEC5D"),
                ("🫐 Azul Cobalto", "#0047AB"), ("🌵 Verde Cacto", "#7BB661"), ("🍑 Laranja Pálido", "#FFDAB9"),
                ("❤️‍🔥 Vermelho Coral", "#FF4040"), ("💜 Roxo Lavanda", "#B57EDC"), ("✨ Amarelo Brilhante", "#FFFF00"),
                ("💎 Azul Royal", "#4169E1"), ("🍀 Verde Menta", "#98FB98"), ("🥭 Laranja Abóbora", "#FF7518"),
                ("🚒 Vermelho Fogo", "#CE2029"), ("🔮 Roxo Escuro", "#301934"), ("🌕 Amarelo Claro", "#FFFFE0"),
                ("🌊 Azul Oceano", "#0077BE"), ("🥗 Verde Pistache", "#93C572"), ("🍊 Laranja Queimado", "#CC5500"),
                ("💋 Vermelho Rubi", "#9B111E"), ("🪻 Roxo Violeta", "#8F00FF"), ("🌤 Amarelo Limão", "#FFF44F"),
                ("🌀 Azul Tiffany", "#81D8D0"), ("🌿 Verde Chá", "#8F9779"), ("🍮 Laranja Caramelo", "#FFD59A"),
                ("🍷 Vermelho Vinho", "#722F37"), ("💜 Roxo Fúcsia", "#C154C1"), ("⚡ Amarelo Elétrico", "#FFEF00"),
                ("🌊 Azul Celeste", "#B0E0E6"), ("🥬 Verde Hortelã", "#3EB489"), ("🍯 Laranja Âmbar", "#FFBF00"),
                ("🌹 Vermelho Rosé", "#FF007F"), ("🪻 Lilás Claro", "#C8A2C8"), ("🌟 Amarelo Puro", "#FFFF00"),
                ("🪸 Azul Aquamarine", "#7FFFD4"), ("🌱 Verde Primavera", "#00FF7F"), ("🍊 Laranja Fanta", "#F58220"),
                ("🩸 Vermelho Pimenta", "#C41E3A"), ("🔮 Roxo Neon", "#9D00FF"), ("🟡 Amarelo Trigo", "#F5DEB3"),
                ("🌌 Azul Índigo", "#4B0082"), ("🥗 Verde Lima", "#BFFF00"), ("🍊 Laranja Pôr do Sol", "#FD5E53"),
                ("❤️ Vermelho Quente", "#E32636"), ("💜 Roxo Pastel", "#B39EB5"), ("🌤 Amarelo Quente", "#FFD300"),
                ("🌊 Azul Safira Claro", "#6CB4EE"), ("🌳 Verde Oliva", "#808000"), ("🍊 Laranja Claro", "#FFB347"),
                ("🍓 Vermelho Rosa", "#FF66CC"), ("💜 Roxo Heliotrópio", "#DF73FF"), ("🌟 Amarelo Ouro Claro", "#FAFAD2"),
                ("💙 Azul Denim", "#1560BD"), ("🌿 Verde Escuro", "#006400"), ("🍊 Laranja Intenso", "#FF7F50"),
                ("🍒 Vermelho Escuro", "#8B0000"), ("💜 Roxo Escuro", "#4B0082"), ("🌤 Amarelo Manteiga", "#FFFACD"),
                ("💧 Azul Neve", "#E0FFFF"), ("🍃 Verde Gramado", "#7CFC00"), ("🍊 Laranja Vivo", "#FFA812"),
                ("🍓 Vermelho Puro", "#FF0000"), ("💜 Roxo Vibrante", "#9400D3"), ("🌟 Amarelo Neon", "#FFFF33"),
                # ... continua até chegar a 300 cores

        ]
        kb = []
        row = []
        for name, hexc in colors:
            row.append(InlineKeyboardButton(name, callback_data=f"color|{hexc}"))
            if len(row) == 3:
                kb.append(row)
                row = []
        if row:
            kb.append(row)
        kb.append([InlineKeyboardButton("🔙 Voltar", callback_data="config")])
        return InlineKeyboardMarkup(kb)

def size_keyboard():
        """
        Cria o teclado inline para seleção de tamanhos do QR code.
        """
        kb = [
            [InlineKeyboardButton("🟩 512px", callback_data="size|512"),
             InlineKeyboardButton("🟩 768px", callback_data="size|768"),
             InlineKeyboardButton("🟩 1024px", callback_data="size|1024")],
            [InlineKeyboardButton("🔙 Voltar", callback_data="config")],
        ]
        return InlineKeyboardMarkup(kb)

    # Função para gerar QR code
def build_qr_image_bytes(data, size=1024, fill="#0A84FF", back="#FFFFFF", logo_bytes=None, bg_bytes=None):
        """
        Gera um QR code em formato PNG e retorna os bytes.
        Se bg_bytes for fornecido, usa-o como fundo completo com o QR centrado.
        Se logo_bytes for fornecido, redimensiona e cola o logotipo no centro do QR.
        """
        if not data:
            raise ValueError("Nenhum dado fornecido para o QR code")

        # Criar QR code base
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img_qr = qr.make_image(fill_color=fill, back_color=back).convert("RGBA")
        img_qr = img_qr.resize((size, size), Image.LANCZOS)

        # Adicionar logotipo, se fornecido
        if logo_bytes:
            try:
                logo = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
                max_logo = int(size * 0.18)
                logo.thumbnail((max_logo, max_logo), Image.LANCZOS)
                pos = ((size - logo.width) // 2, (size - logo.height) // 2)
                img_qr.paste(logo, pos, logo)
            except Exception as e:
                logger.exception("Erro ao processar logotipo: %s", e)

        # Adicionar fundo, se fornecido
        if bg_bytes:
            try:
                bg = Image.open(io.BytesIO(bg_bytes)).convert("RGBA")
                bg_ratio = bg.width / bg.height
                if bg.width >= bg.height:
                    new_h = size
                    new_w = int(bg.width * (size / bg.height))
                else:
                    new_w = size
                    new_h = int(bg.height * (size / bg.width))
                bg = bg.resize((new_w, new_h), Image.LANCZOS)
                left = (bg.width - size) // 2
                top = (bg.height - size) // 2
                bg = bg.crop((left, top, left + size, top + size))
                base = bg
                overlay = Image.new("RGBA", base.size, (0, 0, 0, 80))
                base = Image.alpha_composite(base, overlay)
                margin = int(size * 0.04)
                panel = Image.new("RGBA", (size, size), (255, 255, 255, 200))
                panel = panel.crop((0, 0, size, size)).resize((size - margin * 2, size - margin * 2), Image.LANCZOS)
                panel_base = Image.new("RGBA", base.size, (0, 0, 0, 0))
                panel_base.paste(panel, (margin, margin), panel)
                base = Image.alpha_composite(base, panel_base)
                qr_pos = (margin, margin)
                base.paste(img_qr, qr_pos, img_qr)
                final = base
            except Exception as e:
                logger.exception("Erro ao processar fundo: %s", e)
                final = img_qr
        else:
            final = img_qr

        # Salvar como bytes PNG
        bio = io.BytesIO()
        final.convert("RGBA").save(bio, format="PNG", optimize=True)
        bio.seek(0)
        return bio

    # Handlers
def start(update: Update, context: CallbackContext):
        """
        Inicia o bot e apresenta o menu principal.
        """
        context.user_data.setdefault("prefs", DEFAULTS.copy())
        msg = (
            "🤖 *Gerador Ultra QR Code*\n\n"
            "Bem-vindo(a)! Escolha uma ação abaixo — tudo guiado, rápido e com estilo futurista.\n\n"
            "➡️ Use os botões para configurar cor, tamanho, enviar logo/fundo e gerar o qr code."
        )
        update.message.reply_text(msg, parse_mode="Markdown", reply_markup=main_menu_keyboard())
        return CHOOSING_ACTION

def text_received(update: Update, context: CallbackContext):
        """
        Processa o texto recebido e gera o QR code.
        """
        user_prefs = context.user_data.setdefault("prefs", DEFAULTS.copy())
        text = update.message.text.strip()

        if not text:
            update.message.reply_text("⚠️ Por favor, envie um texto ou URL válido.", reply_markup=main_menu_keyboard())
            return CHOOSING_ACTION

        user_prefs["data"] = text
        try:
            qr_bytes = build_qr_image_bytes(
                data=text,
                size=user_prefs["qr_size"],
                fill=user_prefs["fill_color"],
                back=user_prefs["back_color"],
                logo_bytes=user_prefs["logo_data"],
                bg_bytes=user_prefs["bg_data"]
            )
            update.message.reply_photo(
                photo=qr_bytes,
                caption="✅ QR code gerado com sucesso!",
                reply_markup=main_menu_keyboard()
            )
            user_prefs["last_qr"] = qr_bytes.getvalue()  # Salvar para "Baixar último"
            return CHOOSING_ACTION
        except Exception as e:
            logger.exception("Erro ao gerar QR code: %s", e)
            update.message.reply_text("❌ Erro ao gerar o QR code. Tente novamente.", reply_markup=main_menu_keyboard())
            return CHOOSING_ACTION

def button_router(update: Update, context: CallbackContext):
        """
        Gerencia os botões inline do menu principal e configurações.
        """
        query = update.callback_query
        user_prefs = context.user_data.setdefault("prefs", DEFAULTS.copy())
        query.answer()
        data = query.data

        try:
            if data == "gen_start":
                query.message.reply_text("🔎 Por favor, envie o *texto ou URL* que deseja transformar em QR.",
                                         parse_mode="Markdown")
                return TYPING_TEXT
            elif data == "config":
                query.message.reply_text("🎛️ Configurações — escolha o que alterar:", reply_markup=config_keyboard())
                return CHOOSING_ACTION
            elif data == "cfg_color":
                query.message.reply_text("🎨 Escolha uma cor para os módulos do QR:", reply_markup=color_keyboard())
                return CHOOSING_ACTION
            elif data == "cfg_size":
                query.message.reply_text("🔲 Escolha o tamanho do QR:", reply_markup=size_keyboard())
                return CHOOSING_ACTION
            elif data == "upload_logo":
                query.message.reply_text("📁 Envie o logotipo como arquivo (PNG ou JPG, máx 1MB).")
                return UPLOADING_LOGO
            elif data == "upload_bg":
                query.message.reply_text("🖼️ Envie a imagem de fundo como arquivo (PNG ou JPG, máx 2MB).")
                return UPLOADING_BG
            elif data == "download_last":
                if "last_qr" in user_prefs:
                    query.message.reply_photo(
                        photo=io.BytesIO(user_prefs["last_qr"]),
                        caption="⬇️ Último QR code gerado.",
                        reply_markup=main_menu_keyboard()
                    )
                else:
                    query.message.reply_text("⚠️ Nenhum QR code gerado ainda.", reply_markup=main_menu_keyboard())
                return CHOOSING_ACTION
            elif data == "help":
                query.message.reply_text(
                    "❓ *Ajuda*\n\n"
                    "1. Escolha 'Gerar QR' e envie um texto ou URL.\n"
                    "2. Use 'Configurar' para alterar cor ou tamanho.\n"
                    "3. Envie um logotipo ou fundo (PNG/JPG) para personalizar.\n"
                    "4. Use 'Baixar último' para recuperar o último QR gerado.\n\n"
                    "📌 Máx 1MB para logotipos, 2MB para fundos.",
                    parse_mode="Markdown",
                    reply_markup=main_menu_keyboard()
                )
                return CHOOSING_ACTION
            elif data == "back_main":
                query.message.reply_text("🤖 Escolha uma ação:", reply_markup=main_menu_keyboard())
                return CHOOSING_ACTION
            elif data.startswith("color|"):
                _, hexc = data.split("|", 1)
                user_prefs["fill_color"] = hexc
                query.message.reply_text(f"✅ Cor definida para *{hexc}*.", parse_mode="Markdown", reply_markup=main_menu_keyboard())
                return CHOOSING_ACTION
            elif data.startswith("size|"):
                _, s = data.split("|", 1)
                user_prefs["qr_size"] = int(s)
                query.message.reply_text(f"✅ Tamanho definido para *{s}px*.", parse_mode="Markdown", reply_markup=main_menu_keyboard())
                return CHOOSING_ACTION
        except BadRequest as e:
            logger.exception("Erro ao processar ação: %s", e)
            query.message.reply_text("⚠️ Não foi possível processar a ação. Tente novamente.", reply_markup=main_menu_keyboard())
            return CHOOSING_ACTION

def upload_logo(update: Update, context: CallbackContext):
        """
        Processa o upload de um logotipo em formato PNG ou JPG.
        """
        doc = update.message.document
        if not doc:
            update.message.reply_text("⚠️ Por favor, envie a imagem como arquivo (documento), não como foto.")
            return UPLOADING_LOGO
        if doc.file_size > 1024 * 1024:
            update.message.reply_text("⚠️ Arquivo muito grande. Máx 1MB.")
            return UPLOADING_LOGO
        try:
            f = doc.get_file()
            data = f.download_as_bytearray()
            if not (doc.file_name.lower().endswith((".png", ".jpg", ".jpeg"))):
                update.message.reply_text("⚠️ Formato inválido. Use PNG ou JPG.")
                return UPLOADING_LOGO
            context.user_data["prefs"]["logo_data"] = data
            update.message.reply_text("✅ Logotipo salvo. Volte ao menu para gerar QR.", reply_markup=main_menu_keyboard())
            return CHOOSING_ACTION
        except Exception as e:
            logger.exception("Erro ao baixar logotipo: %s", e)
            update.message.reply_text("❌ Erro ao processar arquivo. Tente novamente.", reply_markup=main_menu_keyboard())
            return UPLOADING_LOGO

def upload_bg(update: Update, context: CallbackContext):
        """
        Processa o upload de uma imagem de fundo em formato PNG ou JPG.
        """
        doc = update.message.document
        if not doc:
            update.message.reply_text("⚠️ Por favor, envie a imagem como arquivo (documento), não como foto.")
            return UPLOADING_BG
        if doc.file_size > 2 * 1024 * 1024:
            update.message.reply_text("⚠️ Arquivo muito grande. Máx 2MB.")
            return UPLOADING_BG
        try:
            f = doc.get_file()
            data = f.download_as_bytearray()
            if not (doc.file_name.lower().endswith((".png", ".jpg", ".jpeg"))):
                update.message.reply_text("⚠️ Formato inválido. Use PNG ou JPG.")
                return UPLOADING_BG
            context.user_data["prefs"]["bg_data"] = data
            update.message.reply_text("✅ Fundo salvo. Volte ao menu para gerar QR.", reply_markup=main_menu_keyboard())
            return CHOOSING_ACTION
        except Exception as e:
            logger.exception("Erro ao baixar fundo: %s", e)
            update.message.reply_text("❌ Erro ao processar arquivo. Tente novamente.", reply_markup=main_menu_keyboard())
            return UPLOADING_BG

def cancel(update: Update, context: CallbackContext):
        """
        Cancela a operação atual e retorna ao menu principal.
        """
        update.message.reply_text("Operação cancelada.", reply_markup=main_menu_keyboard())
        return CHOOSING_ACTION

def about(update: Update, context: CallbackContext):
        """
        Responde ao comando /about ou /sobre com uma descrição do bot e sua autoria.
        """
        msg = (
            "🤖  *Sobre o Gerador Ultra QR Code*\n\n"
            "Este bot cria QR codes personalizados com estilo futurista! 🛸\n\n"
            "✨ *O que faz*: Gera QR codes a partir de textos ou URLs, permitindo personalizar cores, tamanhos, adicionar logotipos e imagens de fundo.\n\n"
            "🚀 *Como funciona*: Use os botões inline para navegar pelo menu, enviar textos, configurar opções ou fazer upload de arquivos (PNG/JPG, máx 1MB para logotipos e 2MB para fundos).\n\n"
            "📌 Comece com /start para ver o menu principal.\n\n"
            "Criado por @TiagoS21 🤯👨‍💻"
        )
        try:
            update.message.reply_text(msg, parse_mode="Markdown", reply_markup=main_menu_keyboard())
            return CHOOSING_ACTION
        except Exception as e:
            logger.exception("Erro ao processar comando /about: %s", e)
            update.message.reply_text("⚠️ Erro ao exibir informações. Tente novamente.", reply_markup=main_menu_keyboard())
            return CHOOSING_ACTION

def main():
        """
        Função principal para iniciar o bot.
        """
        # Configuração do token do bot
        TOKEN = "8203287548:AAGNXfUoSlomfbUUInnnlvOwNr0z36YMiHw"

        # Inicializar a Application
        application = ApplicationBuilder().token(TOKEN).build()

        # Configurar o ConversationHandler
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler('start', start),
                CommandHandler(['about', 'sobre'], about)
            ],
            states={
                CHOOSING_ACTION: [CallbackQueryHandler(button_router)],
                TYPING_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, text_received)],
                UPLOADING_LOGO: [MessageHandler(filters.Document.IMAGE & ~filters.COMMAND, upload_logo)],
                UPLOADING_BG: [MessageHandler(filters.Document.IMAGE & ~filters.COMMAND, upload_bg)],
                CHOOSING_COLOR: [CallbackQueryHandler(button_router)],
                CHOOSING_SIZE: [CallbackQueryHandler(button_router)],
                GENERATING: [MessageHandler(filters.TEXT & ~filters.COMMAND, text_received)],
            },
            fallbacks=[
                CommandHandler('cancel', cancel),
                CommandHandler(['about', 'sobre'], about)
            ],
            allow_reentry=True,
        )
        application.add_handler(conv_handler)

        # Iniciar o bot
        print("Bot iniciado. Pressione Ctrl+C para sair.")
        application.run_polling()

if __name__ == '__main__':
        main()