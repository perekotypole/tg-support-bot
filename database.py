from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017/')
db = client['telegram_support_chatting']
collection = db['connections']


def get_support_chat(user_chat):
    connection = collection.find_one({'user_chat': user_chat})
    return connection['support_chat'] if connection and 'support_chat' in connection else None


def get_user_chat(support_chat):
    connection = collection.find_one({'support_chat': support_chat})
    return int(connection['user_chat']) if connection else None


def get_chat(user_chat):
    connection = collection.find_one({'user_chat': user_chat})
    return connection


def create_user_chat(user_chat, start_param = None):
    exists = collection.find_one({'user_chat': user_chat})
    if not exists:
        collection.insert_one({'user_chat': user_chat, 'start_param': start_param})
    else:
        collection.update_one({'user_chat': user_chat}, {"$set": {'start_param': start_param}})


def create_support_chat(user_chat, support_chat):
    exists = collection.find_one({'user_chat': user_chat})
    if not exists:
        collection.insert_one({'user_chat': user_chat, 'support_chat': support_chat})
    else:
        collection.update_one({'user_chat': user_chat}, {"$set": {'support_chat': support_chat}})
    return True


def chat_type(chat):
    support_chat = collection.find_one({'support_chat': chat})
    if support_chat:
        return 'support_chat'

    return 'user_chat'


def add_chat_lang(user_chat, lang):
    exists = collection.find_one({'user_chat': user_chat})
    if not exists:
        collection.insert_one({'user_chat': user_chat, 'lang': lang})
    else:
        collection.update_one({'user_chat': user_chat}, {"$set": {'lang': lang}})
    return True


def get_chat_lang(user_chat):
    try:
        connection = collection.find_one({'user_chat': user_chat})
        if 'lang' in connection:
            return connection['lang']
    except:
        return None
    

def reset_chat_lang(user_chat):
    collection.update_one({'user_chat': user_chat}, {"$set": {'lang': None}})
