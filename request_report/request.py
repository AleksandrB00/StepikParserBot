from telethon.sync import TelegramClient
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsSearch
from telethon.tl.functions.users import GetUsersRequest
import telethon
from pyrogram import Client

from settings import bot_settings
from bot import bot

app = Client(name="my_account", api_hash=bot_settings.API_HASH, api_id=bot_settings.API_ID)
app.start()

client = TelegramClient(bot_settings.SESSION_NAME, bot_settings.API_ID, bot_settings.API_HASH)
client.start()

'''Запрос пользователей'''

async def open_chat_request(link, id):
    await bot.send_message(id, text='Начинаю парсинг, это может занять от 10 до 15 минут⏱')
    upload_message = await bot.send_message(id, text='Идёт парсинг: 0% [..........]')
    channel = await client.get_entity(link)
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
    return ALL_PARTICIPANTS

'''Запрос пользователей по последней активности'''

async def activity_request(link, id, online):
    await bot.send_message(id, text='Начинаю парсинг, это может занять от 10 до 15 минут⏱')
    upload_message = await bot.send_message(id, text='Идёт парсинг: 0% [..........]')
    channel = await client.get_entity(link)
    id_list = []
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
    for user in ALL_PARTICIPANTS:
        id_list.append(user.id)
    OFFSET_USER = 0
    users_list = []
    while True:
        users = await client(GetUsersRequest(id_list[OFFSET_USER:]))
        if len(users) == 0:
            break
        users_list.extend(users)
        OFFSET_USER += len(users)
    for user in users_list:
        if user.status.__class__ == telethon.tl.types.UserStatusRecently:
            continue
        elif user.status.__class__ == telethon.tl.types.UserStatusOnline:
            continue
        elif user.status.__class__ == telethon.tl.types.UserStatusLastWeek and online == 'week':
            continue
        else:
            users_list.remove(user)
    return users_list

'''Запрос пользователей приватного чата'''

async def private_chat_request(link, id):
    await check_join(link)
    chat = await app.get_chat(link)
    await bot.send_message(id, text='Начинаю парсинг, это может занять от 10 до 15 минут⏱')
    upload_message = await bot.send_message(id, text='Идёт парсинг: 0% [..........]')
    ALL_PARTICIPANTS = []
    count = await app.get_chat_members_count(chat.id)
    percent = 10
    async for participant in app.get_chat_members(chat.id):
        ALL_PARTICIPANTS.append(participant.user)
        progress = len(ALL_PARTICIPANTS) * 100 // count
        if progress == percent:
            await upload_message.edit_text(text=f'Идёт парсинг: {progress}% [{"*"*(int(progress)//10)}{"."*(10-int(progress)//10)}]')
            percent += 10
    await upload_message.edit_text(text='Идёт парсинг: 100% [**********]')
    return ALL_PARTICIPANTS

async def check_join(link):
    try:
        await app.join_chat(link)
        return 
    except:
        return 

'''Парсинг по сообщениям'''

async def chat_messages_request(link, id, current_time, count):
    await check_join(link)
    chat = await app.get_chat(link)
    await bot.send_message(id, text='Начинаю парсинг, это может занять от 10 до 15 минут⏱')
    upload_message = await bot.send_message(id, text='Идёт парсинг:')
    ALL_PARTICIPANTS = []
    current_message = 1
    percent = 10
    async for message in app.get_chat_history(chat.id, offset_date=current_time, limit=count):
        ALL_PARTICIPANTS.append(message.from_user)
        progress = current_message * 100 / count
        if progress == percent:
            await upload_message.edit_text(text=f'Идёт парсинг: {progress}% [{"*"*(int(progress)//10)}{"."*(10-int(progress)//10)}]')
            percent += 10
        current_message += 1
    return ALL_PARTICIPANTS
    
