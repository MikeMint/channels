import re
import yaml
import telebot
import requests
import datetime
import schedule
import time
from telebot import types
from journal import logger
from functools import wraps
from utils import Follower
from threading import Thread

log = logger("main")
# Replace 'YOUR_BOT_TOKEN' with your actual bot token
with open('config.yaml', 'r') as stream:
    try:
        config = yaml.safe_load(stream)
        TOKEN = config['telegram']['token']
        group_id = config['telegram']['group_id']
    except yaml.YAMLError as exc:
        log.error(exc)
        exit()

bot = telebot.TeleBot(TOKEN)

data = []
buf_user = None  # Define a global variable to store user data temporarily
photo_requested = False
request_buf = {}
second_time = False
global users
users = {}

def is_telegram_channel_link(link):
    # Regular expression pattern for Telegram channel link
    pattern = r'https?://(?:www\.)?(?:t(?:elegram)?\.me|telegram\.org)/[a-zA-Z0-9_-]+/?'

    # Check if the link matches the pattern
    if re.match(pattern, link):
        return True
    else:
        return False


def check_command_or_menu(bot):
    def decorator(func):
        @wraps(func)
        def wrapper(message):
            match message.text:
                case "/start":
                    return start(message)
                case "\U0000274C Отменить объявление":
                    bot.send_message(message.from_user.id, """Отменяю объявление. Возврат в меню""",
                                     reply_markup=get_main_keyboard())
                case _:
                    return func(message)
        return wrapper
    return decorator



def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)

    button_send = types.KeyboardButton("\U0001F4F0 Подать объявление")
    markup.add(button_send)
    return markup



def cancel_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    button_cancel = types.KeyboardButton("\U0000274C Отменить объявление")
    markup.row(button_cancel)
    return markup


def cancel_and_skip_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    button_skip = types.KeyboardButton("\U000023ED Пропустить шаг")
    button_cancel = types.KeyboardButton("\U0000274C Отменить объявление")
    markup.row(button_skip, button_cancel)
    return markup

def send_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    button_send = types.KeyboardButton("\U0001F4E3 Отправить объявление")
    button_cancel = types.KeyboardButton("\U0000274C Отменить объявление")
    markup.row(button_send, button_cancel)
    return markup

def hide_keyboard():
    markup = types.ReplyKeyboardRemove(selective=False)
    return markup



@bot.message_handler(commands=['start'])
@bot.message_handler(func=lambda message: message.text == "\U0001F4F0 Подать объявление")
def start(message):
    global buf_user
    buf_user = Follower()
    buf_user.telegram_id = message.from_user.id
    if message.from_user.username:
        buf_user.telegram_nick = f"@{message.from_user.username}"
    else:
        buf_user.telegram_nick = f"@{message.from_user.id}"
    if message.text == "/start":
        bot.send_message(buf_user.telegram_id, """Начнем заполнение""", reply_markup=cancel_keyboard())
    bot.send_message(buf_user.telegram_id, """Напиши название своего канала""", reply_markup=cancel_keyboard())
    bot.register_next_step_handler(message, channel_name)


@check_command_or_menu(bot)
def channel_name(message):
    if not message.text:
        bot.send_message(message.from_user.id, """Текст пустой, попробуем еще раз""",
                         reply_markup=cancel_keyboard())
        bot.register_next_step_handler(message, start)
    elif len(message.text) > 30:
        bot.send_message(message.from_user.id, """Введено более 30 символов. Это точно название? Давай попробуем еще раз""",
                         reply_markup=cancel_keyboard())
        bot.register_next_step_handler(message, start)
    else:
        buf_user.channel_name = message.text
        bot.send_message(message.from_user.id, """Теперь напиши ссылку на твой канал""",
                     reply_markup=cancel_keyboard())
        bot.register_next_step_handler(message, channel_link)


@check_command_or_menu(bot)
def channel_link(message):
    if not is_telegram_channel_link(message.text.strip()):
        bot.send_message(message.from_user.id, """Не похоже на ссылку на telegram канал. Ссылка должна выглядеть примерно так https://t.me/channelname. Напиши еще раз""",
                         reply_markup=cancel_keyboard())
        bot.register_next_step_handler(message, channel_link)
    else:
        buf_user.channel_url = message.text
        bot.send_message(message.from_user.id, """Теперь укажи тематику своего канала. Напиши краткое описание тематики (не более 50 символов)""",
                         reply_markup=cancel_keyboard())
        bot.register_next_step_handler(message, channel_theme)


@check_command_or_menu(bot)
def channel_theme(message):

    if not message.text:
        bot.send_message(message.from_user.id, """Текст пустой, попробуем еще раз""",
                         reply_markup=cancel_keyboard())
        bot.register_next_step_handler(message, channel_theme)
    elif len(message.text) > 50:
        bot.send_message(message.from_user.id, """Введено более 50 символов. Это точно название? Давай попробуем еще раз""",
                         reply_markup=cancel_keyboard())
        bot.register_next_step_handler(message, channel_theme)
    else:
        buf_user.channel_theme = message.text
        bot.send_message(message.from_user.id, """Сколько у тебя подписчиков на канале? Введи число""",
                         reply_markup=cancel_keyboard())
        bot.register_next_step_handler(message, channel_members)

@check_command_or_menu(bot)
def channel_members(message):
    if not message.text.strip().isdigit():
        bot.send_message(message.from_user.id, """"Это не число, попробуем еще раз""",
                         reply_markup=cancel_keyboard())
        bot.register_next_step_handler(message, channel_members)
    elif len(message.text.strip()) > 10:
        bot.send_message(message.from_user.id, """"Введено более 10 символов. Давай еще раз""",
                         reply_markup=cancel_keyboard())
        bot.register_next_step_handler(message, channel_members)
    else:
        buf_user.channel_members = message.text
        bot.send_message(message.from_user.id, """Теперь напиши текст объявления о взаимной рекламе. Это может быть короткое сообщение о том, что ты предлагаешь и какие критерии рекламы у тебя есть, например реклама на каналах только определенной тематики. Если хочешь пропустить этот шаг нажми на кнопку пропустить""",
                         reply_markup=cancel_and_skip_keyboard())
        bot.register_next_step_handler(message, channel_description)

@check_command_or_menu(bot)
def channel_description(message):
    if message.text == "\U000023ED Пропустить шаг":
        buf_user.channel_description = ""
    else:
        buf_user.channel_description = message.text
    bot.send_message(message.from_user.id, """Отлично, сейчас я покажу как будет выглядеть твой текст""",
                     reply_markup=cancel_and_skip_keyboard())
    if buf_user.telegram_nick:
        contact_text = f"{buf_user.telegram_nick}"
    else:
        contact_text = f"{buf_user.telegram_id}"
    global message_text
    message_text = f"""<b>\U0001F4C3 Канал: {buf_user.channel_name}:</b>
<b> </b>        
<b>Ссылка на канал:</b> {buf_user.channel_url}
<b>Количество подписчиков:</b> {buf_user.channel_members}
<b>Тематика:</b> {buf_user.channel_theme}
<b>Контакты:</b> {contact_text}
{"<b>Описание: </b>" + buf_user.channel_description if buf_user.channel_description else ""}"""
    bot.send_message(message.from_user.id, message_text, reply_markup=send_keyboard(), parse_mode='HTML')
    bot.register_next_step_handler(message, send_or_no)


@check_command_or_menu(bot)
def send_or_no(message):
    if message.text == "\U0000274C Отменить объявление":
        bot.send_message(message.from_user.id, """"Окей, как нибудь в другой раз""",
                         reply_markup=get_main_keyboard())
    elif message.text == "\U0001F4E3 Отправить объявление":
        if buf_user.telegram_id not in users.keys():
            buf_user.num = 1
            users[buf_user.telegram_id] = buf_user
            log.info(users)
            bot.send_message(message.from_user.id, """"Отлично! Твое объявление о взаимной рекламе опубликовано на канале [Репост За Репост](https://t.me/RepForRep), зайди и найди партнера для взаимной рекламы Телеграм каналов и обмена аудиторией.""",
                             reply_markup=get_main_keyboard())
            bot.send_message(group_id, message_text, parse_mode='HTML')
        elif users[buf_user.telegram_id].num < 3:
            # for key in users.keys():
            #     if key:
            #         log.info(users[key].__dict__)
            bot.send_message(message.from_user.id, """"Отлично! Твое объявление о взаимной рекламе опубликовано на канале [Репост За Репост] (https://t.me/RepForRep), зайди и найди партнера для взаимной рекламы Телеграм каналов и обмена аудиторией.""",
                             reply_markup=get_main_keyboard())
            bot.send_message(group_id, message_text, parse_mode='HTML')
            users[buf_user.telegram_id].num += 1
        else:
            bot.send_message(message.from_user.id, """На сегодня лимит объявлений исчерпан (""",
                             reply_markup=get_main_keyboard())

def fetch_last_message_except_one():
    token = TOKEN
    response = requests.get(f"https://api.telegram.org/bot{token}/getUpdates")
    data = response.json()
    if data["ok"]:
        if data["result"]:
            latest_update = data["result"][-1]
            bot.process_new_updates([telebot.types.Update.de_json(latest_update)])

def clear_users():
    log.info("Cleaning users")
    users = {}
    log.info(users)

def main():
    schedule.every().day.at("00:00").do(clear_users)
    log.info("Starting bot")
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    log.info("Starting bot")
    fetch_last_message_except_one()
    Thread(target=main).start()
    bot.polling(none_stop=True)