from telethon.sync import TelegramClient
from telethon.tl.functions.account import UpdateUsernameRequest
from telethon.errors import SessionPasswordNeededError
import json


def start_auth():
    with open("configs.json", "r", encoding='utf-8') as file:
        configs = json.load(file)
        profiles = configs["profiles"]

    for profile in profiles:
        client = TelegramClient(f'sessions/profile-{profile["phone"]}', profile["api_id"], profile["api_hash"])
        client.connect()

        if not client.is_user_authorized():
            try:
                client.send_code_request(profile["phone"])
                client.sign_in(profile["phone"], input(f'Enter the verification code [{profile["phone"]}]: '))
            except SessionPasswordNeededError:
                client.sign_in(password=profile["password"])

        print(f'Profile {profile["phone"]} is authorized.')
        client.disconnect()


start_auth()
