import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import BOT_TOKEN
from g4f.client import Client
from dataclasses import dataclass
from typing import Dict

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

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
    ArtaModel("f_pro", "F-Pro", "F-Pro Generation", "📸"),
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
        "🎨 Привет! Я бот для генерации изображений.\n"
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

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main()) 