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

with open("unappropriated_content.txt", "r", encoding="utf-8") as f:
    bad_words = [line.strip() for line in f]

print(bad_words)
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
                    bot.send_message(message.from_user.id,
                                     """"Напиши /start что бы попробовать еще раз""",
                                     reply_markup=get_main_keyboard())
                case _:
                    return func(message)
        return wrapper
    return decorator



def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3, one_time_keyboard=False)

    button_send = types.KeyboardButton("\U0001F4F0 Подать объявление")
    markup.add(button_send)
    return markup



def cancel_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3, one_time_keyboard=False)
    button_cancel = types.KeyboardButton("\U0000274C Отменить объявление")
    markup.row(button_cancel)
    return markup


def cancel_and_skip_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3, one_time_keyboard=False)
    button_skip = types.KeyboardButton("\U000023ED Пропустить шаг")
    button_cancel = types.KeyboardButton("\U0000274C Отменить объявление")
    markup.row(button_skip, button_cancel)
    return markup

def send_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3, one_time_keyboard=False)
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
    if any(bad_word in message.text for bad_word in bad_words if bad_word):
        print("Bad word triggered:", next((bad_word for bad_word in bad_words if bad_word in message.text), None))
        bot.send_message(message.from_user.id, "\U000026D4 В названии есть неприемлемые слова. Отменяем подачу заявки. Если у вас остались вопросы - обратитесь к администратору канала - \U0001F4EE @JohnCrawford7520")
        bot.send_message(message.from_user.id, "\U0000274C Отправка заявки отменена", reply_markup=get_main_keyboard())
    elif not message.text:
        bot.send_message(message.from_user.id, "Текст пустой, попробуем еще раз", reply_markup=cancel_keyboard())
        bot.register_next_step_handler(message, channel_name)
    elif len(message.text) > 60:
        bot.send_message(message.from_user.id, "Введено более 60 символов. Это точно название? Давай попробуем еще раз", reply_markup=cancel_keyboard())
        bot.register_next_step_handler(message, channel_name)
    else:
        buf_user.channel_name = message.text
        bot.send_message(message.from_user.id, "Теперь напиши ссылку на твой канал", reply_markup=cancel_keyboard())
        bot.register_next_step_handler(message, channel_link)


@check_command_or_menu(bot)
def channel_link(message):
    if not is_telegram_channel_link(message.text.strip()):
        bot.send_message(message.from_user.id, """Не похоже на ссылку на telegram канал. Ссылка должна выглядеть примерно так https://t.me/channelname. Напиши еще раз""",
                         reply_markup=cancel_keyboard())
        bot.register_next_step_handler(message, channel_link)
    else:
        buf_user.channel_url = message.text
        bot.send_message(message.from_user.id, """Теперь укажи тематику своего канала. Напиши краткое описание тематики (не более 80 символов)""",
                         reply_markup=cancel_keyboard())
        bot.register_next_step_handler(message, channel_theme)


@check_command_or_menu(bot)
def channel_theme(message):
    if any(bad_word in message.text for bad_word in bad_words if bad_word):
        print("Bad word triggered:", next((bad_word for bad_word in bad_words if bad_word in message.text), None))
        bot.send_message(message.from_user.id, "\U000026D4 В описании есть неприемлемые слова. Отменяем подачу заявки. Если у вас остались вопросы - обратитесь к администратору канала - \U0001F4EE @JohnCrawford7520")
        bot.send_message(message.from_user.id, """\U0000274C Отправка заявки отменена""",
                         reply_markup=get_main_keyboard())
    elif not message.text:
        bot.send_message(message.from_user.id, """Текст пустой, попробуем еще раз""",
                         reply_markup=cancel_keyboard())
        bot.register_next_step_handler(message, channel_theme)
    elif len(message.text) > 80:
        bot.send_message(message.from_user.id, """Введено более 80 символов. Давай попробуем еще раз""",
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
        bot.send_message(message.from_user.id, """Теперь напиши текст объявления о взаимной рекламе. Это может быть короткое сообщение о том, что ты предлагаешь и какие критерии рекламы у тебя есть, например реклама на каналах только определенной тематики. Если хочешь пропустить этот шаг нажми на кнопку пропустить (максимально 150 символов)""",
                         reply_markup=cancel_and_skip_keyboard())
        bot.register_next_step_handler(message, channel_description)

@check_command_or_menu(bot)
def channel_description(message):
    if any(bad_word in message.text for bad_word in bad_words if bad_word):
        bot.send_message(message.from_user.id, "\U000026D4 В тексте есть неприемлемые слова. Отменяем подачу заявки. Если у вас остались вопросы - обратитесь к администратору канала - \U0001F4EE @JohnCrawford7520")
        bot.send_message(message.from_user.id, """\U0000274C Отправка заявки отменена""",
                         reply_markup=get_main_keyboard())
    elif len(message.text) > 150:
        bot.send_message(message.from_user.id, """Введено более 150 символов. Давай попробуем еще раз""",
                         reply_markup=cancel_keyboard())
        bot.register_next_step_handler(message, channel_theme)
    else:
        if message.text == "\U000023ED Пропустить шаг":
            buf_user.channel_description = ""
        else:
            buf_user.channel_description = message.text
        bot.send_message(message.from_user.id, """Отлично, сейчас я покажу как будет выглядеть твой текст""",
                     reply_markup=hide_keyboard())
        markup = types.InlineKeyboardMarkup()
        yes_button = types.InlineKeyboardButton("\U0001F4E3 Отправить", callback_data='send_to_group')
        no_button = types.InlineKeyboardButton("\U0000274C Отменить", callback_data='cancel_send')
        markup.row(yes_button, no_button)
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
        bot.send_message(message.from_user.id, message_text, reply_markup=markup, parse_mode='HTML')
            # bot.send_message(message.from_user.id,
            #                  """\U0001F53D Нажми кнопку отправки или отмены ниже \U0001F53D""", reply_markup=send_keyboard())
        # bot.register_next_step_handler(message, send_or_no)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "cancel_send":
        bot.answer_callback_query(call.id, "Окей, как нибудь в другой раз", show_alert=False)
        bot.send_message(call.from_user.id, """Переходим в основное меню""",
                         reply_markup=get_main_keyboard())
    elif call.data == "send_to_group":
        if buf_user.telegram_id not in users.keys():
            buf_user.num = 1
            users[buf_user.telegram_id] = buf_user
            log.info(users)
            bot.answer_callback_query(call.id, "Объявление отправлено", show_alert=False)
            bot.send_message(call.from_user.id, """"Отлично! Твое объявление о взаимной рекламе опубликовано на канале [Репост За Репост](https://t.me/RepForRep), зайди и найди партнера для взаимной рекламы Телеграм каналов и обмена аудиторией""",
                             reply_markup=get_main_keyboard())
            bot.send_message(group_id, message_text, parse_mode='HTML')
        elif users[buf_user.telegram_id].num < 3:
            # for key in users.keys():
            #     if key:
            #         log.info(users[key].__dict__)
            bot.answer_callback_query(call.id, "Объявление отправлено", show_alert=False)
            bot.send_message(call.from_user.id, """"Отлично! Твое объявление о взаимной рекламе опубликовано на канале [Репост За Репост] (https://t.me/RepForRep), зайди и найди партнера для взаимной рекламы Телеграм каналов и обмена аудиторией.""",
                             reply_markup=get_main_keyboard())
            bot.send_message(group_id, message_text, parse_mode='HTML')
            users[buf_user.telegram_id].num += 1
        else:
            bot.answer_callback_query(call.id, "На сегодня лимит объявлений исчерпан (", show_alert=True)
            bot.send_message(call.from_user.id, """Переходим в меню""",
                             reply_markup=get_main_keyboard())
    bot.edit_message_reply_markup(call.from_user.id, call.message.message_id)


@check_command_or_menu(bot)
def send_or_no(message):
    if message.text == "\U0000274C Отменить объявление":
        bot.send_message(message.from_user.id, """"Окей, как нибудь в другой раз""",
                         reply_markup=get_main_keyboard())
        bot.send_message(message.from_user.id,
                         """"Напиши /start что бы попробовать еще раз""",
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
    else:
        bot.send_message(message.from_user.id,
                         """"Кнопки отправки ниже, выбери из них""", reply_markup=send_keyboard())
        bot.register_next_step_handler(message, send_or_no)

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