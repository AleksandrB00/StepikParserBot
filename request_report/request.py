from telethon.sync import TelegramClient
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsSearch
from telethon.tl.functions.users import GetUsersRequest
import telethon

from settings import bot_settings
from bot import bot

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