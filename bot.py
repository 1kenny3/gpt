# Стандартные библиотеки
import os
import re
import sys
import logging
import asyncio
import tempfile
import subprocess
import shutil
from os import path

# Сторонние библиотеки
import aiohttp
import youtube_dl
from pytube import YouTube
from pytube.exceptions import PytubeError
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    Message, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    CallbackQuery
)
from aiogram.enums import ChatAction
from aiogram.filters.command import Command
from config import BOT_TOKEN
from g4f.client import Client
from dataclasses import dataclass
from typing import Dict
import yt_dlp

# Регулярное выражение для проверки YouTube ссылок
YOUTUBE_URL_PATTERN = r'(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[A-Za-z0-9_-]+'

# Константы для OpenRouter API
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_NAME = "anthropic/claude-3-sonnet"

# Регулярное выражение для проверки YouTube URL
YOUTUBE_REGEX = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:watch\?v=|embed\/|v\/)|youtu\.be\/)([a-zA-Z0-9_-]+)'

# Проверка наличия ffmpeg
HAS_FFMPEG = bool(shutil.which('ffmpeg'))
if not HAS_FFMPEG:
    logging.warning("ffmpeg не установлен! Функционал скачивания MP3 будет недоступен.")

# Загрузка переменных окружения
load_dotenv()

# Получение токенов из переменных окружения
API_KEY = os.getenv('OPENROUTER_API_KEY')
BOT_TOKEN = os.getenv('BOT_TOKEN')

if not API_KEY:
    raise ValueError("OPENROUTER_API_KEY не найден в переменных окружения!")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения!")

# Настройка бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация клиента g4f
client = Client()

# Словарь для хранения промптов пользователей
user_prompts: Dict[int, str] = {}

# Доступные модели ARTA
@dataclass
class ArtaModel:
    id: str
    name: str
    description: str
    emoji: str

ARTA_MODELS = [
    ArtaModel("cinematic_art", "Кино", "Кинематографический стиль", "🎥"),
    ArtaModel("anime", "Аниме", "Стиль аниме и японской анимации", "🇯🇵"),
    ArtaModel("realistic", "Реализм", "Фотореалистичные изображения", "📸"),
    ArtaModel("creative", "Креатив", "Абстрактные и художественные образы", "🎨"),
    ArtaModel("manga", "Манга", "Стиль японской манги", "📘"),
    ArtaModel("disney", "Дисней", "Стиль Disney анимации", "🏰"),
    ArtaModel("enhance", "Улучшение", "Улучшение качества изображения", "🔍"),
    ArtaModel("pixel_art", "Пиксели", "Ретро пиксельная графика", "🖼️"),
    ArtaModel("flux", "Flux", "Flux Image Generation", "📸"),
    ArtaModel("medieval", "Medieval", "Средневековый стиль", "📸"),
    ArtaModel("vincent_van_gogh", "Van Gogh", "Стиль Ван Гога", "📸"),
    ArtaModel("f_dev", "F-Dev", "F-Dev Generation", "📸"),
    ArtaModel("low_poly", "Low Poly", "Низкополигональный стиль", "📸"),
    ArtaModel("dreamshaper_xl", "Dreamshaper XL", "Dreamshaper XL Generation", "📸"),
    ArtaModel("anima_pencil_xl", "Anima Pencil", "Карандашный стиль Anima", "📸"),
    ArtaModel("biomech", "Biomech", "Биомеханический стиль", "📸"),
    ArtaModel("trash_polka", "Trash Polka", "Стиль Trash Polka", "📸"),
    ArtaModel("no_style", "No Style", "Без стилизации", "📸"),
    ArtaModel("cheyenne_xl", "Cheyenne XL", "Cheyenne XL Generation", "📸"),
    ArtaModel("chicano", "Chicano", "Стиль Chicano", "📸"),
    ArtaModel("embroidery_tattoo", "Embroidery", "Вышивка тату", "📸"),
    ArtaModel("red_and_black", "Red & Black", "Красно-черный стиль", "📸"),
    ArtaModel("fantasy_art", "Fantasy Art", "Фэнтези арт", "📸"),
    ArtaModel("watercolor", "Watercolor", "Акварельный стиль", "📸"),
    ArtaModel("dotwork", "Dotwork", "Точечный стиль", "📸"),
    ArtaModel("old_school_colored", "Old School Color", "Олдскул цветной", "📸"),
    ArtaModel("realistic_tattoo", "Realistic Tattoo", "Реалистичное тату", "📸"),
    ArtaModel("japanese_2", "Japanese", "Японский стиль", "📸"),
    ArtaModel("realistic_stock_xl", "Stock XL", "Реалистичный сток", "📸"),
    ArtaModel("f_pro", "F-Pro", "F-Pro Generation", "��"),
    ArtaModel("reanimated", "Reanimated", "Reanimated Generation", "📸"),
    ArtaModel("katayama_mix_xl", "Katayama Mix", "Katayama Mix XL", "📸"),
    ArtaModel("sdxl_l", "SDXL-L", "SDXL-L Generation", "📸"),
    ArtaModel("cor_epica_xl", "Cor Epica", "Cor Epica XL", "📸"),
    ArtaModel("anime_tattoo", "Anime Tattoo", "Аниме тату", "📸"),
    ArtaModel("new_school", "New School", "Нью скул", "📸"),
    ArtaModel("death_metal", "Death Metal", "Дэт-метал стиль", "📸"),
    ArtaModel("old_school", "Old School", "Олдскул", "📸"),
    ArtaModel("juggernaut_xl", "Juggernaut", "Juggernaut XL", "📸"),
    ArtaModel("photographic", "Photographic", "Фотографический", "📸"),
    ArtaModel("sdxl_1_0", "SDXL 1.0", "SDXL 1.0 Generation", "📸"),
    ArtaModel("graffiti", "Graffiti", "Граффити", "📸"),
    ArtaModel("mini_tattoo", "Mini Tattoo", "Мини тату", "📸"),
    ArtaModel("surrealism", "Surrealism", "Сюрреализм", "📸"),
    ArtaModel("neo_traditional", "Neo Traditional", "Нео традишнл", "📸"),
    ArtaModel("on_limbs_black", "On Limbs Black", "On Limbs Black стиль", "📸"),
    ArtaModel("yamers_realistic_xl", "Yamers Realistic", "Yamers Realistic XL", "📸")
]

MODELS_DICT = {model.id: model for model in ARTA_MODELS}

def get_models_keyboard() -> InlineKeyboardMarkup:
    """Создает компактную клавиатуру с кнопками выбора модели"""
    buttons = []
    row = []
    for model in ARTA_MODELS:
        row.append(InlineKeyboardButton(
            text=f"{model.emoji} {model.name}",
            callback_data=f"model_{model.id}"
        ))
        if len(row) == 3:  # По 3 кнопки в ряд
            buttons.append(row)
            row = []
    if row:  # Добавляем оставшиеся кнопки
        buttons.append(row)
    
    # Добавляем кнопку отмены отдельной строкой
    buttons.append([
        InlineKeyboardButton(
            text="❌ Отменить выбор",
            callback_data="model_cancel"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_models_list_keyboard() -> InlineKeyboardMarkup:
    """Инлайн-кнопки для списка моделей с выбором"""
    buttons = []
    
    # Категории стилей
    categories = {
        "🎨 Художественные": ["vincent_van_gogh", "watercolor", "fantasy_art", "surrealism"],
        "📸 Реалистичные": ["realistic", "photographic", "realistic_stock_xl", "yamers_realistic_xl"],
        "🎬 Кино и анимация": ["cinematic_art", "disney", "anime", "manga"],
        "🎮 Специальные": ["pixel_art", "low_poly", "medieval", "creative"],
        "✨ AI Models": ["flux", "f_dev", "f_pro", "dreamshaper_xl", "sdxl_l", "sdxl_1_0"],
        "💉 Тату стили": [
            "biomech", "trash_polka", "chicano", "embroidery_tattoo",
            "dotwork", "old_school", "new_school", "realistic_tattoo",
            "anime_tattoo", "mini_tattoo", "neo_traditional"
        ],
        "🔧 Утилиты": ["enhance", "no_style"]
    }
    
    # Добавляем кнопки по категориям
    for category, model_ids in categories.items():
        buttons.append([InlineKeyboardButton(
            text=category,
            callback_data=f"category_{category}"  # Для будущего расширения функционала
        )])
        
        row = []
        for model_id in model_ids:
            model = next((m for m in ARTA_MODELS if m.id == model_id), None)
            if model:
                row.append(InlineKeyboardButton(
                    text=f"{model.emoji} {model.name}",
                    callback_data=f"models_info_{model.id}"
                ))
                if len(row) == 2:  # По 2 кнопки в ряд
                    buttons.append(row)
                    row = []
        if row:  # Добавляем оставшиеся кнопки
            buttons.append(row)
        
        # Добавляем разделитель между категориями
        buttons.append([InlineKeyboardButton(text="➖" * 20, callback_data="separator")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Привет, Тотоньйо. Че хочешь ?\n"
        "Используй команду /generate с описанием желаемого изображения.\n\n"
        "Примеры команд:\n"
        "• /generate закат над городом\n"
        "• /generate anime девушка с мечом\n"
        "• /generate realistic портрет человека\n\n"
        "📚 Список всех стилей: /models\n"
        "🆘 Помощь: /help"
    )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "🆘 Справка по использованию бота:\n\n"
        "1. Для начала работы введите /generate [ваш запрос]\n"
        "2. Выберите стиль из предложенных вариантов\n"
        "3. Дождитесь генерации изображения (обычно 10-30 секунд)\n\n"
        "🖼️ Можно сразу указать стиль в команде:\n"
        "Пример: /generate anime лесной эльф\n\n"
        "📚 Список всех стилей: /models\n"
        "⏳ История генераций: /history (скоро)"
    )

@dp.message(Command("generate"))
async def generate_prompt(message: Message):
    text = message.text.replace("/generate", "").strip()
    
    if not text:
        await message.answer("❌ Пожалуйста, укажите описание изображения после команды")
        return
    
    first_word = text.split()[0].lower()
    selected_model = None
    prompt = text
    
    for model in ARTA_MODELS:
        if first_word in [model.id.lower(), model.name.lower()]:
            selected_model = model
            prompt = " ".join(text.split()[1:])
            break
    
    if selected_model:
        await generate_image(message, selected_model.id, prompt)
    else:
        user_prompts[message.from_user.id] = text
        await message.answer(
            "🎨 Выберите стиль генерации (нажмите для описания):",
            reply_markup=get_models_keyboard()
        )

@dp.callback_query(lambda c: c.data.startswith('model_'))
async def process_model_selection(callback_query: CallbackQuery):
    model_id = callback_query.data.replace('model_', '')
    
    if model_id == "cancel":
        user_id = callback_query.from_user.id
        if user_id in user_prompts:
            del user_prompts[user_id]
        await callback_query.message.delete()
        await callback_query.answer("❌ Выбор отменен")
        return
    
    model = MODELS_DICT.get(model_id)
    if not model:
        await callback_query.answer("⚠️ Модель не найдена")
        return
    
    await callback_query.answer(f"🎨 {model.description}")
    
    prompt = user_prompts.get(callback_query.from_user.id)
    if not prompt:
        await callback_query.message.answer("🚫 Время выбора истекло, начните заново")
        await callback_query.answer()
        return
    
    await callback_query.message.delete()
    await generate_image(callback_query.message, model_id, prompt)
    
    if callback_query.from_user.id in user_prompts:
        del user_prompts[callback_query.from_user.id]

async def generate_image(message: Message, model_id: str, prompt: str):
    try:
        processing_msg = await message.answer(f"⏳ Генерация в стиле {MODELS_DICT[model_id].name}...")
        
        response = await asyncio.to_thread(
            client.images.generate,
            model=model_id,
            prompt=prompt,
            response_format="url"
        )
        
        await message.answer_photo(
            photo=response.data[0].url,
            caption=f"🎨 Стиль: {MODELS_DICT[model_id].emoji} {MODELS_DICT[model_id].name}\n✍️ Запрос: {prompt}"
        )
        
        await processing_msg.delete()
        
    except Exception as e:
        logging.error(f"Ошибка генерации: {e}")
        await message.answer("⚠️ Произошла ошибка при генерации. Попробуйте другой запрос.")

@dp.message(Command("models"))
async def show_models(message: Message):
    await message.answer(
        "🖼️ Выберите стиль, чтобы узнать подробнее:\n\n"
        "🎨 Каталог стилей генерации изображений\n"
        "Для генерации используйте команду:\n"
        "/generate [стиль] [описание]\n\n"
        "Например: /generate anime красивая девушка с катаной",
        reply_markup=get_models_list_keyboard()
    )

@dp.callback_query(lambda c: c.data == "separator")
async def process_separator(callback_query: CallbackQuery):
    # Просто игнорируем нажатие на разделитель
    await callback_query.answer()

@dp.callback_query(lambda c: c.data.startswith('models_info_'))
async def model_info_callback(callback_query: CallbackQuery):
    model_id = callback_query.data.replace('models_info_', '')
    model = MODELS_DICT.get(model_id)
    if not model:
        await callback_query.answer("Модель не найдена")
        return
    text = (
        f"{model.emoji} <b>{model.name}</b> (<code>{model.id}</code>)\n"
        f"{model.description}\n\n"
        "Используйте в команде:\n"
        f"/generate {model.id} [ваш запрос]"
    )
    await callback_query.answer()  # Погасить "часики"
    await callback_query.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_models_list_keyboard()
    )

async def get_openrouter_response(prompt: str) -> dict:
    """
    Получает ответ от OpenRouter API
    
    Args:
        prompt (str): Текст запроса пользователя
        
    Returns:
        dict: Ответ от API или строка с сообщением об ошибке
    """
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "HTTP-Referer": "https://github.com/xtekky/gpt4free",
        "X-Title": "gpt4free",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 2000  # Ограничиваем количество токенов
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(OPENROUTER_API_URL, headers=headers, json=data) as response:
                response_json = await response.json()
                logging.info(f"OpenRouter API response: {response_json}")
                
                if response.status == 200:
                    return response_json
                elif response.status == 402:
                    error_msg = response_json.get('error', {}).get('message', 'Недостаточно кредитов')
                    logging.error(f"OpenRouter API credit error: {error_msg}")
                    return "⚠️ Извините, у бота закончились кредиты. Пожалуйста, сообщите администратору."
                else:
                    error_msg = response_json.get('error', {}).get('message', 'Неизвестная ошибка')
                    logging.error(f"OpenRouter API error: Status {response.status}, Message: {error_msg}")
                    return f"Ошибка при получении ответа от API: {error_msg}"
    except Exception as e:
        logging.error(f"Error calling OpenRouter API: {str(e)}")
        return f"Произошла ошибка при обращении к API: {str(e)}"

@dp.message(lambda message: re.match(YOUTUBE_REGEX, message.text))
async def youtube_link_handler(message: types.Message):
    """Обрабатывает сообщения содержащие YouTube ссылки"""
    url = message.text
    await process_youtube_url(message, url)

@dp.message(Command(commands=['start', 'help']))
async def send_welcome(message: types.Message):
    """
    Обработчик команд /start и /help
    """
    welcome_text = (
        "Привет, Тотоньйо. Че хочешь ?\n\n"
        "1️⃣ Отвечать на ваши вопросы с помощью AI\n"
        "2️⃣ Генерировать изображения\n"
        "3️⃣ Скачивать аудио с YouTube\n\n"
        "Команды:\n"
        "/help - показать это сообщение\n"
        "/generate - генерировать изображение\n"
        "/mp3 [youtube_url] - скачать аудио с YouTube\n\n"
        "Просто отправьте мне сообщение для общения с AI или ссылку на YouTube видео! 🚀"
    )
    await message.reply(welcome_text)

@dp.message(Command('mp3'))
async def download_audio(message: types.Message):
    """
    Обработчик команды /mp3 для скачивания аудио с YouTube
    """
    try:
        # Получаем URL из сообщения
        command_parts = message.text.split()
        if len(command_parts) != 2:
            await message.reply("❌ Пожалуйста, укажите URL YouTube видео после команды /mp3")
            return
        
        url = command_parts[1]
        if not re.match(YOUTUBE_REGEX, url):
            await message.reply("❌ Пожалуйста, укажите корректную ссылку на YouTube видео")
            return
        
        # Отправляем сообщение о начале загрузки
        status_message = await message.reply("⏳ Начинаю загрузку аудио...")
        
        # Создаем временную директорию для загрузки
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Загружаем видео
                yt = YouTube(url)
                audio_stream = yt.streams.filter(only_audio=True).first()
                
                if not audio_stream:
                    await status_message.edit_text("❌ Не удалось найти аудио поток в этом видео")
                    return
                
                # Загружаем аудио
                audio_file = audio_stream.download(output_path=temp_dir)
                
                # Конвертируем в MP3
                base, _ = os.path.splitext(audio_file)
                mp3_file = base + '.mp3'
                
                # Проверяем наличие ffmpeg
                if not HAS_FFMPEG:
                    await status_message.edit_text("❌ Для конвертации аудио требуется ffmpeg")
                    return
                
                # Конвертируем в MP3
                subprocess.run(['ffmpeg', '-i', audio_file, '-codec:a', 'libmp3lame', '-qscale:a', '2', mp3_file])
                
                # Отправляем файл
                with open(mp3_file, 'rb') as audio:
                    await message.reply_audio(
                        audio,
                        title=yt.title,
                        performer=yt.author,
                        caption=f"🎵 {yt.title}\n👤 {yt.author}"
                    )
                
                await status_message.delete()
                
            except Exception as e:
                logging.error(f"Ошибка при загрузке аудио: {str(e)}")
                await status_message.edit_text("❌ Произошла ошибка при загрузке аудио")
                
    except Exception as e:
        logging.error(f"Ошибка в обработчике /mp3: {str(e)}")
        await message.reply("❌ Произошла ошибка при обработке команды")

@dp.message()
async def handle_message(message: types.Message):
    """
    Обработчик текстовых сообщений для общения с OpenRouter API
    """
    try:
        # Проверяем, является ли сообщение YouTube ссылкой
        if re.match(YOUTUBE_REGEX, message.text):
            await process_youtube_url(message, message.text)
            return

        # Отправляем индикатор набора текста
        await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
        
        # Получаем ответ от OpenRouter API
        response = await get_openrouter_response(message.text)
        
        if isinstance(response, str):  # Если получили строку с ошибкой
            await message.reply(response)
            return
            
        # Извлекаем текст ответа из response
        try:
            if 'choices' in response and len(response['choices']) > 0:
                answer = response['choices'][0]['message']['content']
                await message.reply(answer)
            elif 'error' in response:
                error_msg = response['error'].get('message', 'Неизвестная ошибка')
                logging.error(f"API error response: {error_msg}")
                await message.reply(f"⚠️ Ошибка API: {error_msg}")
            else:
                logging.error(f"Unexpected API response structure: {response}")
                await message.reply("Извините, получен некорректный ответ от API.")
                
        except (KeyError, IndexError) as e:
            logging.error(f"Error extracting response content: {str(e)}, Response: {response}")
            await message.reply("Извините, произошла ошибка при обработке ответа.")
            
    except Exception as e:
        logging.error(f"Error in message handler: {str(e)}")
        await message.reply("Извините, произошла ошибка при обработке вашего сообщения.")

@dp.callback_query()
async def process_download_callback(callback_query: types.CallbackQuery):
    """Обрабатывает нажатие на кнопку 'Скачать MP3'"""
    if not callback_query.data.startswith('download:'):
        return
        
    await callback_query.answer()
    
    # Извлекаем URL из callback_data
    youtube_url = callback_query.data.replace('download:', '')
    
    # Удаляем inline клавиатуру
    await callback_query.message.edit_reply_markup(reply_markup=None)
    
    # Обрабатываем URL
    await process_youtube_url(callback_query.message, youtube_url)

async def download_audio(url: str) -> str:
    """
    Загружает аудио с YouTube видео.
    
    Args:
        url (str): URL YouTube видео
        
    Returns:
        str: Путь к загруженному аудио файлу
    """
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': '%(title)s.%(ext)s',
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return f"{info['title']}.mp3"
    except Exception as e:
        logging.error(f"Ошибка при загрузке аудио: {str(e)}")
        raise

async def process_youtube_url(message: types.Message, url: str):
    """
    Обрабатывает YouTube ссылку: загружает аудио и отправляет его пользователю.
    
    Args:
        message (types.Message): Сообщение от пользователя
        url (str): YouTube URL для обработки
    """
    try:
        # Отправляем сообщение о начале загрузки
        status_message = await message.reply("⏳ Загружаю аудио...")
        
        # Загружаем аудио
        audio_path = await download_audio(url)
        
        # Отправляем аудио файл
        with open(audio_path, 'rb') as audio:
            await message.reply_audio(audio)
            
        # Удаляем статусное сообщение и временные файлы
        await status_message.delete()
        os.remove(audio_path)
        
    except Exception as e:
        error_message = f"❌ Произошла ошибка при обработке видео: {str(e)}"
        if 'status_message' in locals():
            await status_message.edit_text(error_message)
        else:
            await message.reply(error_message)

async def main():
    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main()) 