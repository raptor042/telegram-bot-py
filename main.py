import os
from dotenv import load_dotenv

from enum import Enum

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters
)

from services.db import connect_db, get_user, set_user, update_user, delete_user
from services.payment import init_payment, verify_payment, get_sub, cancel

from controllers.cryptic import _encrypt
from controllers.keys import loadKeyPair

import logging
import requests

logging.basicConfig(format="%(asctime)s -%(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

class State(Enum):
    INACTIVE = 0
    ACTIVE = 1
SETUP , PAYMENT, SETTINGS, END = range(4)
db = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    logger.info("User %s started the conversation.", user.username)

    _query = { "username" : user.username }
    _user = get_user(db=db, query=_query)
    print(_user)

    if _user:
        reply_msg = "Hello <b>{}</b>, Seems you already have an account with us, hence you cannot start this conversation again. if you are having any issues, Enter the command <b>'/help'</b> and contact us.".format(user.username)
        await update.message.reply_html(text=reply_msg)

        return SETUP
    else:
        keyboard = [
            [InlineKeyboardButton("Begin Setup", callback_data="setup")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "Hello <b>{}</b>\n\n<b>OddZ</b> <i>is an <b>AI</b> platform which uses cutting-edge technology to create bots which automate users betting process. Oddz is solely designed to improve your betting odds via automated betting</i> \n\n<strong>Oddz is avaliable in only SportyBet for now but will soon support other betting platforms</strong>\n\n<i>OddZ is only available in Nigeria</i>".format(user.username)

        await update.message.reply_html(text=reply_msg, reply_markup=reply_markup)

        _user = set_user(db=db, value={"username" : user.username, "active" : State.INACTIVE.value})
        print(_user)

        return SETUP

async def setup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Enter Account Details", callback_data="account")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    reply_msg = "<strong>Enter the details of your SportyBet account; This includes your phone number and password.</strong>\n\n<i>Make sure your account details are correct else your Bot will be inactive.</i>\n\n<strong>Please also enter your email address; This is used for payment purposes.</strong>\n\n<i>If you encounter any issues or need more clarification, Enter the command <b>'/help'</b>, We would gladly help you through the process</i>"

    await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)

    return SETUP

async def account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    await query.message.reply_text("Enter your email address")

    return SETUP

async def email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Enter your phone number")

    query = { "username" : update.message.from_user.username }
    value = {"$set" : {"email" : update.message.text}}
    user = update_user(db=db, query=query , value=value)
    print(user)

    return SETUP

async def phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_msg = "<b>Enter your Password</b>\n\n<i>When entering your password, please enter the password using the format : <b>'Password:AFSFDHDzxcv1234@#$'</b>. Note, Replace these characters with your actual password and No whitespaces between the characters</i>"
    await update.message.reply_html(text=reply_msg)

    key = loadKeyPair()
    phone_number = _encrypt(text=update.message.text, key=key[0])
    query = { "username" : update.message.from_user.username }
    value = {"$set" : {"phone" : phone_number}}
    user = update_user(db=db, query=query , value=value)
    print(user)

    return SETUP

async def password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_msg = "<i>Your Bot Setup is almost finished</i>\n\n<b>Enter the amount you would like to allocate for betting. Minimum is 10 Naira</b>\n\n<i>Please make sure your betting account is funded.</i>"
    await update.message.reply_html(text=reply_msg)

    key = loadKeyPair()
    pass_word = _encrypt(text=update.message.text.split(":", 1)[1], key=key[0])
    query = { "username" : update.message.from_user.username }
    value = {"$set" : {"password" : pass_word}}
    user = update_user(db=db, query=query , value=value)
    print(user)

    return SETUP

async def wager(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        [
            InlineKeyboardButton("Singles", callback_data="sys:singles"),
            InlineKeyboardButton("Multiple", callback_data="sys:multiple")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    reply_msg = "<i>Your Bot Setup is almost finished</i>\n\n<b>Select your favorite betting system</b>\n\n<i>This system would be used for every bet placed by your bot</i>"
    
    await update.message.reply_html(text=reply_msg, reply_markup=reply_markup)

    query = { "username" : update.message.from_user.username }
    value = {"$set" : {"wager" : update.message.text}}
    user = update_user(db=db, query=query , value=value)
    print(user)

    return SETUP

async def system(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Begin Payment", callback_data="payment")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    reply_msg = "<i>Your Bot is now ready</i>\n\n<b>To activate the Bot you have to make a payment based on your chosen subscription</b>"
    
    await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)

    _query = { "username" : query.from_user.username}
    value = {"$set" : {"system" : query.data.split(":", 1)[1]}}
    user = update_user(db=db, query=_query , value=value)
    print(user)

    return PAYMENT

async def payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Monthly", callback_data="sub-monthly")],
        [InlineKeyboardButton("Quaterly", callback_data="sub-quarterly")],
        [InlineKeyboardButton("BiAnnually", callback_data="sub-biannually")],
        [InlineKeyboardButton("Annually", callback_data="sub-annually")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    reply_msg = "<b>Tis is a subscription based payment, thus you will be charged monthly(Every month), quarterly(Every 3 months), biannually(Every 6 months) or annually(Every year).</b>\n\n<b>Here are the prices(Naira) per subscription basis:</b>\n<i>Monthly - <s>30,000</s> 15,000</i>\n<i>Quarterly - <s>90,000</s> 60,000</i>\n<i>BiAnnually - <s>180,000</s> 120,000</i>\n<i>Annually - <s>360,000</s> 240,000</i>\n\n<i>Click any button below to choose your subscription basis</i>"
    await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)

    return PAYMENT

async def subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    _query = { "username" : query.from_user.username }
    user = get_user(db=db, query=_query)
    print(user)

    payment = init_payment(email=user["email"], plan=query.data.split("-", 1)[1])
    print(payment)

    ref = payment["ref"]
    uri = payment["uri"]

    keyboard = [
        [InlineKeyboardButton("Paid", callback_data=f"paid:{ref}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    reply_msg = "<i>Click the link below, you will be redirected to the payment portal where you will make the payment</i>\n\n<i>Link : {}</i>\n\n<b>Once you have completed payment you will be redirected back to this chat. Click the button below to confirm payment</b>".format(uri)
    await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)

    return PAYMENT

async def paid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    payment = verify_payment(ref=query.data.split(":", 1)[1])
    print(payment)

    if payment == "Success":
        _query = { "username" : query.from_user.username }
        value = {"$set" : {"active" : State.ACTIVE.value}}
        user = update_user(db=db, query=_query , value=value)
        print(user)

        keyboard = [
            [InlineKeyboardButton("End", callback_data="end")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<i>Congratulations your Bot is now active</i>\n\n<b>May the OddZ always be in your favour</b>\n\n<i>You can always change the settings for your bot, just Enter the command <b>'/settings'</b> to edit your bot settings.</i>\n\n<i>If you need any help through the process, Enter the command <b>'/help'</b></i>\n\n<b>Click the button below to end our conversation</b>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)
    else:
        keyboard = [
            [InlineKeyboardButton("Begin Payment", callback_data="payment")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>Payment not Successful</b>\n\n<i>Kindly repeat the payment procedure to activate your Bot</i>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)

    return PAYMENT

async def end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    await query.message.reply_html("See you next time.")

    return ConversationHandler.END

async def mention(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    code = update.channel_post.text.split("\n\n")[1]
    print(code)

    requests.get("http://127.0.0.1:5000/bets/{}".format(code))

    await update.channel_post.reply_text("Success")

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("Edit Account", callback_data="edit")],
        [InlineKeyboardButton("Cancel Subscription", callback_data="cancel")],
        [InlineKeyboardButton("Delete Account", callback_data="delete")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    reply_msg = "<b>You can make changes to initals settings like email, phone number, password and betting allocation, system or SportyInsure by clicking th button below.</b>\n\n<i>Make sure you made those changes at SportyBet also.</i>\n\n<b>You can also delete your account by clicking the button below.</b>"
    await update.message.reply_html(text=reply_msg, reply_markup=reply_markup)

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    reply_msg = "<i>Seems you help with something</i>\n\n<b>These are some instructions that you should follow to avoid any issue and successfully complete the process of creating your bot:</b>\n<i>1. Firstly to start the bot conversation, enter the command <b>'/start'</b></i>\n<i>2. During the process of setting up your bot, instructions are given on how to enter your password. Make sure you follow those instructions</i>\n<i>3. During the process of editing your bot account settings, instructions are given on how to enter your new email or phone number or passord</i>\n<i>4. To ensure that your bot is fully functional and places bets for you, make the sportybet account details entered during the bot setup are correct. If you made any mistakes go to settings by entering the command <b>'/settings'</b> and edit your account details</i>\n<i>5. When you are asked to select, please click only one button to choose that option</i>\n<i>6. Make sure your account is funded.</i>\n\n<b>For more guidance and support:</b>\n<i>Call : 09151984731</i>\n<i>Email : chromiumtechstudios@gmail.com</i>"
    await update.message.reply_html(text=reply_msg)

async def edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Edit Email", callback_data="edit_email")],
        [InlineKeyboardButton("Edit Phone Number", callback_data="edit_phone")],
        [InlineKeyboardButton("Edit Password", callback_data="edit_password")],
        [InlineKeyboardButton("Edit Betting Amount", callback_data="edit_wager")],
        [InlineKeyboardButton("Edit Betting System", callback_data="edit_system")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    reply_msg = "<b>You can make changes to following settings by clicking the buttons below.</b>\n\n<i>When entering your new credentials, please enter the credentials using the format : <b>'New:ADGGHNGRGJK'</b>. Note, Replace these characters with your actual credentials and No whitespaces between the characters</i>"
    await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)

async def edits(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == "edit_email": 
        reply_msg = "<i>Enter your new email address using the following format:</i>\n\n<b>Must begin with 'New-Email:', followed by your new email address and no whitespaces</b>"
        await query.message.reply_html(text=reply_msg)
    elif query.data == "edit_phone":
        reply_msg = "<i>Enter your new phone number using the following format:</i>\n\n<b>Must begin with 'New-PhoneNumber:', followed by your new phone number and no whitespaces</b>"
        await query.message.reply_html(text=reply_msg)
    elif query.data == "edit_password":
        reply_msg = "<i>Enter your new password using the following format:</i>\n\n<b>Must begin with 'New-Password:', followed by your new password and no whitespaces</b>"
        await query.message.reply_html(text=reply_msg)
    elif query.data == "edit_wager":
        reply_msg = "<i>Enter your new betting amount allocation using the following format:</i>\n\n<b>Must begin with 'New-Wager:', followed by your new betting amount allocation and no whitespaces</b>"
        await query.message.reply_html(text=reply_msg)
    elif query.data == "edit_system":
        keyboard = [
            [
                InlineKeyboardButton("Singles", callback_data="new-sys:singles"),
                InlineKeyboardButton("Multiple", callback_data="new-sys:multiple")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("Select your new betting system", reply_markup=reply_markup)    

async def edit_account_1(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if "New-Email:" in update.message.text:
        query = { "username" : update.message.from_user.username }
        value = {"$set" : {"email" : update.message.text.split(":", 1)[1]}}
        user = update_user(db=db, query=query , value=value)
        print(user)

        await update.message.reply_text("Your email address have been changed")
    elif "New-PhoneNumber:" in update.message.text:
        key = loadKeyPair()
        phone_number = _encrypt(text=update.message.text.split(":", 1)[1], key=key[0])
        query = { "username" : update.message.from_user.username }
        value = {"$set" : {"phone" : phone_number}}
        user = update_user(db=db, query=query , value=value)
        print(user)

        await update.message.reply_text("Your phone number have been changed")
    elif "New-Password:" in update.message.text:
        key = loadKeyPair()
        pass_word = _encrypt(text=update.message.text.split(":", 1)[1], key=key[0])
        query = { "username" : update.message.from_user.username }
        value = {"$set" : {"password" : pass_word}}
        user = update_user(db=db, query=query , value=value)
        print(user)

        await update.message.reply_text("Your password have been changed")
    elif "New-Wager:" in update.message.text:
        query = { "username" : update.message.from_user.username }
        value = {"$set" : {"wager" : update.message.text.split(":", 1)[1]}}
        user = update_user(db=db, query=query , value=value)
        print(user)

        await update.message.reply_text("Your betting amount allocation have been changed")

async def edit_account_2(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if "new-sys" in query.data:
        _query = { "username" : query.from_user.username}
        value = {"$set" : {"system" : query.data.split(":", 1)[1]}}
        user = update_user(db=db, query=_query , value=value)
        print(user)

        await query.message.reply_text("Your betting system have been changed")

async def cancel_sub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    keyboard = [
        [
            InlineKeyboardButton("Yes", callback_data="sub:yes"),
            InlineKeyboardButton("No", callback_data="sub:no")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("This action is permanent, Are you sure?", reply_markup=reply_markup)

async def cancel_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == "sub:yes":
        _query = { "username" : query.from_user.username}
        value = {"$set" : {"active" : State.INACTIVE.value}}
        user = update_user(db=db, query=_query , value=value)
        _user = get_user(db=db, query=_query)
        print(user, _user)

        sub = get_sub(_user["email"])
        print(sub)
        code = sub["sub_code"]
        token = sub["email_token"]

        cancel(code=code, token=token)
        await query.message.reply_text("Subscription canceled. If you want to reactivate your bot, please contact us.")
    elif query.data == "sub:no":
        await query.message.reply_text("No action has been taken.")

async def del_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    keyboard = [
        [
            InlineKeyboardButton("Yes", callback_data="del:yes"),
            InlineKeyboardButton("No", callback_data="del:no")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("This action is permanent, Are you sure?", reply_markup=reply_markup)

async def delete_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == "del:yes":
        _query = { "username" : query.from_user.username }
        user = delete_user(db=db, query=_query)
        print(user)

        await query.message.reply_text("Account deleted permanently.")
    elif query.data == "del:no":
        await query.message.reply_text("No action has been taken.")

def main() -> None:
    global db
    db = connect_db(uri=MONGO_URI)

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SETUP: [
                CallbackQueryHandler(setup, pattern="^setup$"),
                CallbackQueryHandler(account, pattern="^account$"),
                MessageHandler(filters.Regex(".com$"), email),
                MessageHandler(filters.Regex("^0(7|8|9)\d{9}"), phone),
                MessageHandler(filters.Regex("^Password:"), password),
                MessageHandler(filters.Regex("[10-1000000000]"), wager),
                CallbackQueryHandler(system, pattern="^sys:"),
            ],
            PAYMENT: [
                CallbackQueryHandler(payment, pattern="^payment$"),
                CallbackQueryHandler(subscription, pattern="^sub-"),
                CallbackQueryHandler(paid, pattern="^paid:")
            ]
        },
        fallbacks=[CallbackQueryHandler(end, pattern="^end$")]
    )
    msg_handler = MessageHandler(filters.Entity("mention"), mention)
    settings_handler = CommandHandler("settings", settings)
    help_handler = CommandHandler("help", help)
    edit_handler = CallbackQueryHandler(edit, pattern="^edit$")
    edits_handler = CallbackQueryHandler(edits, pattern="^edit_")
    edit_account_handler_1 = MessageHandler(filters.Regex("^New-"), edit_account_1)
    edit_account_handler_2 = CallbackQueryHandler(edit_account_2, pattern="^new-")
    del_handler = CallbackQueryHandler(del_account, pattern="^delete$")
    delete_handler = CallbackQueryHandler(delete_account, pattern="^del:")
    cancel_handler = CallbackQueryHandler(cancel_sub, pattern="^cancel$")
    cancel_sub_handler = CallbackQueryHandler(cancel_subscription, pattern="^sub:")

    app.add_handler(conv_handler)
    app.add_handler(msg_handler)
    app.add_handler(settings_handler)
    app.add_handler(help_handler)
    app.add_handler(edit_handler)
    app.add_handler(edits_handler)
    app.add_handler(edit_account_handler_1)
    app.add_handler(edit_account_handler_2)
    app.add_handler(delete_handler)
    app.add_handler(del_handler)
    app.add_handler(cancel_handler)
    app.add_handler(cancel_sub_handler)

    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()