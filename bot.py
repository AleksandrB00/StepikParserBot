from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext

import logging
import glob
import asyncio
from datetime import datetime, timezone, timedelta

from settings import bot_settings
from bot_menu import menu
from database import orm
from request_report import request, create_report


logging.basicConfig(
    level=logging.INFO,
    filename = "botlog.log",
    filemode='a',
    format = "%(asctime)s - %(module)s - %(levelname)s - %(funcName)s: %(lineno)d - %(message)s",
    datefmt='%H:%M:%S',
    )

bot = Bot(token=bot_settings.BOT_TOKEN)
storage = MemoryStorage() 
dp = Dispatcher(bot, storage=storage)

'''Состояния'''

class ChatOpenLink(StatesGroup):
    waiting_link = State()

class ParsingActive(StatesGroup):
    waiting_link = State()
    last_activity = State()

class ParsingPhones(StatesGroup):
    waiting_link = State()

class Mailing(StatesGroup):
    text = State()
    entity = State()

class Get_id_premium(StatesGroup):
    user_id = State()

class Get_id_admin(StatesGroup):
    user_id = State()

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
async def get_filter_activity(message: types.Message, state: FSMContext):
    await state.update_data(waiting_link=message.text)
    inline_markup = await menu.last_active_menu()
    text = 'За какой промежуток времени пользователи должны были быть онлайн?'
    await message.answer(text, reply_markup=inline_markup, parse_mode='Markdown')
    await ParsingActive.last_activity.set()

'''Кнопка моб. телефоны'''

@dp.callback_query_handler(lambda call: 'phones' in call.data)
async def parsing_phones(callback_query: types.CallbackQuery):
    text = 'Отправьте ссылку на чат'
    await bot.send_message(callback_query.from_user.id, text, parse_mode='Markdown')
    await ParsingPhones.waiting_link.set()

'''Прасинг открытого чата'''

@dp.message_handler(state=ChatOpenLink.waiting_link)
async def get_open_report(message: types.Message, state: FSMContext):
    await state.update_data(waiting_link=message.text)
    state_data = await state.get_data()
    link = state_data.get('waiting_link')
    ALL_PARTICIPANTS = await request.open_chat_request(link, message.chat.id)
    await create_report.create_open_chat_report(ALL_PARTICIPANTS, 'users')
    await state.finish()
    text = 'Для парсинга следующего чата выберите необходимое действие👇'
    inline_markup = await menu.main_menu()
    target = '*.txt'
    file = glob.glob(target)[0]
    await message.reply_document(open(file, 'rb'))
    await message.answer(text, reply_markup=inline_markup, parse_mode='Markdown')

'''Парсинг по последней активности'''

@dp.callback_query_handler(state=ParsingActive.last_activity)
async def parsing_activity_start(callback_query: types.CallbackQuery, state: FSMContext):
    await state.update_data(last_activity=callback_query.data)
    state_data = await state.get_data()
    link = state_data.get('waiting_link')
    online = state_data.get('last_activity').split('_')[1]
    ALL_PARTICIPANTS = await request.activity_request(link, callback_query.from_user.id, online)
    await create_report.create_open_chat_report(ALL_PARTICIPANTS, 'users') 
    await state.finish()
    target = '*.txt'
    file = glob.glob(target)[0]
    text = 'Для парсинга следующего чата выберите необходимое действие👇'
    inline_markup = await menu.main_menu()
    await bot.send_document(callback_query.from_user.id, open(file, 'rb'))
    await bot.send_message(callback_query.from_user.id, text, reply_markup=inline_markup)
    
'''Прасинг телефонов'''

@dp.message_handler(state=ParsingPhones.waiting_link)
async def get_phone_numbers(message: types.Message, state: FSMContext):
    await state.update_data(waiting_link=message.text)
    state_data = await state.get_data()
    link = state_data.get('waiting_link')
    ALL_PARTICIPANTS = await request.open_chat_request(link, message.chat.id)
    await create_report.create_open_chat_report(ALL_PARTICIPANTS, 'phones')
    target = '*.txt'
    file = glob.glob(target)[0] 
    await state.finish()
    text = 'Для парсинга следующего чата выберите необходимое действие👇'
    inline_markup = await menu.main_menu()
    await message.reply_document(open(file, 'rb'))
    await message.answer(text, reply_markup=inline_markup, parse_mode='Markdown')          

'''Вызов меню администратора'''                                   

@dp.message_handler(lambda message: orm.check_admin(message.from_user.id) == 1 and message.text == '/admin')
async def get_admin_menu(message: types.Message):
    text = 'Выберите необходимое действие'
    inline_markup = await menu.admin_menu()
    await message.answer(text, reply_markup=inline_markup)

'''Кнопка рассылки'''

@dp.callback_query_handler(lambda call: 'create_mailing' in call.data)
async def create_mailing(callback_query: types.CallbackQuery):
    text = 'Введите текст, который хотите разослать'
    await bot.send_message(callback_query.from_user.id, text, parse_mode='Markdown')
    await Mailing.text.set()

'''Рассылка'''

@dp.message_handler(state=Mailing.text)
async def mailing(message: types.Message, state: FSMContext):
    await state.update_data(text=message.text, entity=message.entities)
    state_data = await state.get_data()
    text = state_data.get('text')
    entity = state_data.get('entity')
    users = orm.get_all_users()
    await message.answer('Начинаю рассылку', parse_mode='Markdown')
    count = 0
    count_of_banned = 0
    for user in users:
        try:
            await bot.send_message(user.tg_id, text=text, entities=entity, disable_web_page_preview=True)
            count += 1
            if count == 15:
                asyncio.sleep(5)
                count = 0
        except:
            count_of_banned += 1
    answer = f'Отправка рыссылки завершена\nВсего пользователей: {len(users)}\nОтправлено успешно: {len(users)-count_of_banned}\nУдалили чат с ботом: {count_of_banned}'
    orm.add_blocked(count_of_banned)
    await message.answer(answer, parse_mode='Markdown')
    await state.finish()

'''Кнопка выдачи премиум статуса'''

@dp.callback_query_handler(lambda call: 'set_premium' in call.data)
async def button_premium(callback_query: types.CallbackQuery):
    text = 'Введите id пользователя'
    await bot.send_message(callback_query.from_user.id, text, parse_mode='Markdown')
    await Get_id_premium.user_id.set()

'''Создание премиум пользователя'''

@dp.message_handler(state=Get_id_premium.user_id)
async def create_premium(message: types.Message, state: FSMContext):
    await state.update_data(user_id=message.text)
    state_data = await state.get_data()
    user_id = state_data.get('user_id')
    current_time_utc =  datetime.now(timezone.utc)
    target_time = current_time_utc + timedelta(hours=240, minutes=0)
    orm.get_premium(user_id, current_time_utc, target_time)
    await state.finish()
    await bot.send_message(int(user_id), 'Вам выдан премиум-статус на 10 дней', parse_mode='Markdown')
    inline_markup = await menu.admin_menu()
    await message.answer('Премиум статус выдан успешно', reply_markup=inline_markup)

'''Кнопка дать права администратора'''

@dp.callback_query_handler(lambda call: 'set_admin_previlegies' in call.data)
async def button_admin(callback_query: types.CallbackQuery):
    text = 'Введите id пользователя'
    await bot.send_message(callback_query.from_user.id, text, parse_mode='Markdown')
    await Get_id_admin.user_id.set()

'''Создание администратора'''

@dp.message_handler(state=Get_id_admin.user_id)
async def create_admin(message: types.Message, state: FSMContext):
    await state.update_data(user_id=message.text)
    state_data = await state.get_data()
    user_id = state_data.get('user_id')
    orm.get_admin(user_id)
    await state.finish()
    inline_markup = await menu.admin_menu()
    await message.answer('Права администратора выданы успешно', reply_markup=inline_markup)

'''Кнопка статистика'''

@dp.callback_query_handler(lambda call: 'stat' in call.data)
async def get_stat(callback_query: types.CallbackQuery):
    stat = orm.stat()
    text = f'Всего пользователей: {stat[0]}\nУдалили чат с ботом: {stat[1]}\n*Количество удаливших чат с ботом обновляется после рассылки*'
    await bot.send_message(callback_query.from_user.id, text, parse_mode='Markdown')

'''Кнопка купить премиум'''

@dp.callback_query_handler(lambda call: 'buy_premium' in call.data)
async def button_buy(callback_query: types.CallbackQuery):
    await bot.send_invoice(
    callback_query.from_user.id,
    title='Покупка премиум статуса',
    description='Покупка премиум статуса на 10 дней',
    provider_token=bot_settings.PAYMENT_TOKEN,
    currency='rub',
    photo_url=bot_settings.IMAGE_URL,
    photo_height=512, 
    photo_width=512,
    photo_size=512,
    is_flexible=False, 
    prices=[bot_settings.PRICE],
    start_parameter='10-days-premium',
    payload='something'
)

'''Валидация платёжных данных'''

@dp.pre_checkout_query_handler(lambda query: True)
async def process_pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

'''Успешная оплата'''

@dp.message_handler(content_types=types.ContentType.SUCCESSFUL_PAYMENT)
async def process_successful_payment(message: types.Message):
    pmnt = message.successful_payment.to_python()
    await bot.send_message(message.chat.id,'Оплата прошла успешно')

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
    