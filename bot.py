from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from telethon.sync import TelegramClient
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsSearch

import logging
import glob

from settings import bot_settings
from bot_menu import menu
from database import orm


logging.basicConfig(
    level=logging.INFO,
    filename = "botlog.log",
    filemode='a',
    format = "%(asctime)s - %(module)s - %(levelname)s - %(funcName)s: %(lineno)d - %(message)s",
    datefmt='%H:%M:%S',
    )

client = TelegramClient(bot_settings.SESSION_NAME, bot_settings.API_ID, bot_settings.API_HASH)
client.start()

bot = Bot(token=bot_settings.BOT_TOKEN)
storage = MemoryStorage() 
dp = Dispatcher(bot, storage=storage)

'''Состояния'''

class ChatOpenLink(StatesGroup):
    waiting_link = State()

class ParsingActive(StatesGroup):
    waiting_link = State()
    last_activity = State()

class ParsingInChat(StatesGroup):
    waiting_link = State()
    date = State()

'''Команды'''

async def set_default_commands(dp):
    await dp.bot.set_my_commands(
        [
            types.BotCommand('start', 'Перезапустить бота'),
        ]
    )

'''Главное меню'''

@dp.message_handler(commands=['start'])
async def start_message(message: types.Message):
    text = f'Привет *{message.from_user.first_name}*!\nВаш ID: {message.from_user.id}\nЯ могу спарсить любой чат\nВыбери необходимое действие👇'
    inline_markup = await menu.main_menu()
    response = orm.add_user(message.from_user.id, message.from_user.username)
    inline_markup = await menu.main_menu()
    username = message.from_user.username
    if response == 1:
        users = orm.get_admins()
        for user in users:
                if message.from_user.username == None:
                    await bot.send_message(user.tg_id, text=f'Пользователь <a href="tg://user?id={message.from_user.id}">@{message.from_user.first_name}</a> присоединился', parse_mode='HTML')
                elif message.from_user.username != None:
                    await bot.send_message(user.tg_id, text=f'Пользователь <a href="tg://user?id={message.from_user.id}">@{username}</a> присоединился', parse_mode='HTML')
                else:
                   await bot.send_message(user.tg_id, text=f'Пользователь <a href="tg://user?id={message.from_user.id}">@{username}</a> присоединился', parse_mode='HTML') 
    await message.answer(text, reply_markup=inline_markup, parse_mode='Markdown')
    await set_default_commands(dp)

'''Вызов главного меню'''

@dp.callback_query_handler(lambda call: 'main_menu' in call.data)
async def get_main_menu(callback_query: types.CallbackQuery):
    text = f'Привет *{callback_query.from_user.first_name}*!\nВаш ID: {callback_query.from_user.id}\nЯ могу спарсить любой чат\nВыбери необходимое действие👇'
    inline_markup = await menu.main_menu()
    await callback_query.message.edit_text(text, reply_markup=inline_markup, parse_mode='Markdown')

'''Вызов премиум меню'''

@dp.callback_query_handler(lambda call: 'premium_menu' in call.data)
async def get_premium_menu(callback_query: types.CallbackQuery):
    if orm.check_premium(callback_query.from_user.id) == 1:
        text = 'Выберите необходимый вариант из списка'
        inline_markup = await menu.premium_parsing_menu()
        await callback_query.message.edit_text(text, reply_markup=inline_markup, parse_mode='Markdown')
    else:
        text = 'Данная функция доступна только премиум пользователям'
        await bot.send_message(callback_query.from_user.id, text, parse_mode='Markdown')

'''Кнопка для открытого парсинга'''

@dp.callback_query_handler(lambda call: 'parsing_open_start' in call.data)
async def parsing_open_start(callback_query: types.CallbackQuery):
    text = 'Отправьте ссылку на ваш чат в формате *t.mе/durоv* или *@durоv*'
    await bot.send_message(callback_query.from_user.id, text, parse_mode='Markdown')
    await ChatOpenLink.waiting_link.set()

'''Кнопка по дате последнего посещения'''

@dp.callback_query_handler(lambda call: 'parsing_activity' in call.data)
async def parsing_activity_start(callback_query: types.CallbackQuery):
    text = 'Отправьте ссылку на чат'
    await bot.send_message(callback_query.from_user.id, text, parse_mode='Markdown')
    await ParsingActive.waiting_link.set()

'''Запрос фильтра по активности'''

@dp.message_handler(state=ParsingActive.waiting_link)
async def get_private_report(message: types.Message, state: FSMContext):
    await state.update_data(waiting_link=message.text)
    inline_markup = await menu.active_menu()
    text = 'За какой промежуток времени пользователи должны были быть онлайн?'
    await message.answer(text, reply_markup=inline_markup, parse_mode='Markdown')
    await ParsingActive.last_activity.set()

'''Кнопка писавшие в чат'''

@dp.callback_query_handler(lambda call: 'parsing_in_chat' in call.data)
async def parsing_in_chat_start(callback_query: types.CallbackQuery):
    text = 'Отправьте ссылку на чат'
    await bot.send_message(callback_query.from_user.id, text, parse_mode='Markdown')
    await ParsingInChat.waiting_link.set()

'''Прасинг открытого чата'''

@dp.message_handler(state=ChatOpenLink.waiting_link)
async def get_open_report(message: types.Message, state: FSMContext):
    await state.update_data(waiting_link=message.text)
    state_data = await state.get_data()
    link = state_data.get('waiting_link')
    channel = await client.get_entity(link)
    await bot.send_message(message.chat.id, text='Начинаю парсинг, это может занять от 10 до 15 минут⏱')
    upload_message = await bot.send_message(message.chat.id, text='Идёт парсинг: 0% [..........]')
    ALL_PARTICIPANTS = []
    for key in bot_settings.QUERY:
        progress = (bot_settings.QUERY.index(key)+1)*100/len(bot_settings.QUERY)
        completion_percentage = float('{:.2f}'.format(progress))
        await upload_message.edit_text(text=f'Идёт парсинг: {completion_percentage}% [{"*"*(int(progress)//10)}{"."*(10-int(progress)//10)}]')
        OFFSET_USER = 0
        while True:
            participants = await client(GetParticipantsRequest(channel, ChannelParticipantsSearch(key), OFFSET_USER, bot_settings.LIMIT_USER, hash=0))
            if not participants.users:
                break
            ALL_PARTICIPANTS.extend(participants.users)
            OFFSET_USER += len(participants.users)
    target = '*.txt'
    file = glob.glob(target)[0] 
    with open(file, "w", encoding="utf-8") as write_file:
        for participant in ALL_PARTICIPANTS[0:100]:
            if participant.username != None and participant.bot == False and participant.fake == False:
                write_file.writelines(f"@{participant.username}\n")
    uniqlines = set(open(file,'r', encoding='utf-8').readlines())
    open(file,'w', encoding='utf-8').writelines(set(uniqlines))
    await state.finish()
    text = 'Для парсинга следующего чата выберите необходимое действие👇'
    inline_markup = await menu.main_menu()
    await message.reply_document(open(file, 'rb'))
    await message.answer(text, reply_markup=inline_markup, parse_mode='Markdown')

'''Парсинг писавших в чат'''

@dp.callback_query_handler(state=ParsingInChat.waiting_link)
async def parsing_in_chat_start(callback_query: types.CallbackQuery, state: FSMContext): 
    await state.update_data(last_activity=callback_query.data)
    state_data = await state.get_data()
    link = state_data.get('waiting_link')
    date = state_data.get('last_activity').split('_')[1]
    if date == 'all':
        hours = 0
    else:
        hours = int(date)
    await bot.send_message(callback_query.from_user.id, text='Начинаю парсинг, это может занять от 10 до 15 минут⏱', parse_mode='Markdown')
    upload_message = await bot.send_message(callback_query.from_user.id, text='Идёт парсинг')

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
    