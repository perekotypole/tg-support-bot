from telethon import TelegramClient, functions, Button
from telethon.sync import events
import json

import database
import auth


def get_configs():
    with open("configs.json", "r", encoding='utf-8') as file:
        return json.load(file)


bot_data = get_configs()["bot"]

api_id = bot_data["api_id"]
api_hash = bot_data["api_hash"]
bot_token = bot_data["bot_token"]

bot_id = int(bot_token.split(':')[0])

bot = TelegramClient('session_bot', api_id, api_hash).start(bot_token=bot_token)
index = 0

profiles_authorization = {}


def get_support():
    configs = get_configs()
    support = configs["support"]
    support.append(bot_id)
    return support


async def choose_lang(event):
    from_chat = await event.get_chat()
    database.reset_chat_lang(from_chat.id)

    configs = get_configs()
    default_messages = configs["default_messages"]
    langs_codes = list(default_messages.keys())

    buttons = []
    for code in langs_codes:
        button = Button.text(default_messages[code]["name"])
        button.resize = 0
        buttons.append(button)

    await event.respond(configs["lang_msg"], buttons=buttons, parse_mode='html')


async def set_lang(event):
    from_chat = await event.get_chat()
    message = event.message

    configs = get_configs()
    default_messages = configs["default_messages"]
    langs_codes = list(default_messages.keys())

    lang = None
    for code in langs_codes:
        if default_messages[code]["name"] == message.message:
            lang = code
            break
    
    if not lang or lang not in default_messages:
        await choose_lang(event)
        return

    database.add_chat_lang(from_chat.id, lang)

    data = default_messages[lang]
    button = Button.text(data['buttons']['faq'])
    button.resize = 0
    await event.respond(data["message"], buttons=[button], parse_mode='html')


async def send_msg_to_user(from_chat, message):
    user_chat_id = database.get_user_chat(from_chat.id)
    await bot(functions.messages.ForwardMessagesRequest(
        from_peer=bot_id,
        id=[message.id],
        to_peer=user_chat_id,
        drop_author=True,
        noforwards=True
    ))


async def create_chat(from_chat, sender):
    try:
        configs = get_configs()
        profiles = configs["profiles"]

        global index
        
        profile_data = profiles[index]
        profile = TelegramClient(
            f'sessions/profile-{profile_data["phone"]}',
            profile_data["api_id"],
            profile_data["api_hash"]
        )

        index = index + 1 if index + 1 < len(profiles) else 0

        await profile.connect()
        if not (await profile.is_user_authorized()):
            try:
                if profile_data["phone"] not in profiles_authorization \
                        or profiles_authorization[profile_data["phone"]]:
                    await bot.send_message(
                        bot_data["notification_chat"],
                        f'Profile {profile_data["phone"]} is unauthorized'
                    )
                    profiles_authorization[profile_data["phone"]] = False
            except:
                pass
            raise

    except Exception as e:
        print(e)
        if profile.is_connected():
            await profile.disconnect()
        return await create_chat()

    try:
        bot_entity = await bot.get_entity('me')
        bot_username = bot_entity.username
        await profile.get_entity(bot_username)

        profiles_authorization[profile_data["phone"]] = True
        chat = await profile(functions.messages.CreateChatRequest(
            title=f'{sender.first_name} [support chat]',
            users=get_support()
        ))

        chat_id = chat.updates[1].participants.chat_id
        support_chat = await profile.get_entity(chat_id)

        await profile(functions.messages.EditChatAdminRequest(chat_id, bot_id, True))
        
        database.create_support_chat(from_chat.id, support_chat.id)
    finally:
        await profile.disconnect()
    
    return chat_id


async def send_user_data(event):
    from_chat = await event.get_chat()
    sender = await event.get_sender()
    user = await bot.get_entity(sender.id)

    chat_data = database.get_chat(from_chat.id)

    user_data = {
        "id": user.id,
        "username": f'@{user.username}' if user.username else None,
        "name": f'{user.first_name} {user.last_name}' if user.last_name else user.first_name,
        "referal": chat_data["start_param"] if "start_param" in chat_data else None,
        "lang": chat_data["lang"],
    }

    await bot.send_message(-1 * chat_data['support_chat'], f'ID: {user_data["id"]}\nUsername: {user_data["username"]}\nName: {user_data["name"]}\nReferal: {user_data["referal"]}\nLanguage: {user_data["lang"]}\n')


@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    from_chat = await event.get_chat()
    sender = await event.get_sender()

    if sender.id == bot_id or database.chat_type(from_chat.id) == 'support_chat':
        return

    raw_text = event.raw_text
    params = raw_text.split(' ')
    start_param = None
    if len(params) > 1 and 'start' in params[0]:
        start_param = params[1]

    database.create_user_chat(from_chat.id, start_param)
    await choose_lang(event)


@bot.on(events.NewMessage)
async def handle_new_message(event):
    message = event.message
    if "/start" in message.message:
        return
    
    from_chat = await event.get_chat()
    sender = await event.get_sender()

    if sender.id == bot_id:
        return

    if database.chat_type(from_chat.id) == 'support_chat':
        await send_msg_to_user(from_chat, message)
        return
    
    lang = database.get_chat_lang(from_chat.id)
    if not lang:
        await set_lang(event)
        return
    
    support_chat_id = database.get_support_chat(from_chat.id)
    try:
        support_chat = await bot.get_entity(support_chat_id)
    except:
        support_chat = None
    
    configs = get_configs()
    default_messages = configs["default_messages"]
    data = default_messages[lang]
    buttons = data["buttons"]
    for button_type in list(buttons.keys()):
        if buttons[button_type] == message.message:
            if button_type == 'faq':
                await event.respond(data['faq'], buttons=[Button.url(data['faq_url']['title'], data['faq_url']['url'])], parse_mode='html')
                
                keyboard_buttons = []
                for button_type in list(buttons.keys()):
                    button = Button.text(buttons[button_type])
                    button.resize = 0
                    keyboard_buttons.append(button)
                await event.respond(data["pre_manager"], buttons=keyboard_buttons, parse_mode='html')
            
            elif button_type == 'manager':
                if not support_chat or support_chat.deactivated:
                    await create_chat(from_chat, sender)
                await event.respond(data['manager'], parse_mode='html')
                await send_user_data(event)
                
            return
        
    if not support_chat or support_chat.deactivated:
        support_chat_id = await create_chat(from_chat, sender)
        if not support_chat_id:
            return
        await send_user_data(event)

    await bot.forward_messages(support_chat_id, message)


bot.run_until_disconnected()
