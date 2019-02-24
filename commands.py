#-*- coding: utf-8 -*-

import math
import subprocess
from telegram.ext import Updater
import random

# database
import datetime
import sqlite3
from sqlite3 import Error

# global variable
run_prefix = '/home/primestone/'
database = run_prefix + 'bot/history.db'
admin_user = '....'
old_core = run_prefix + 'old/primestone-cli'
new_core = run_prefix + 'new/primestone-cli'
explorer_url = 'http://primestone-explorer.com/'

def create_connection(db_file=database):
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(e)

    return None

def insert_withdraw(conn, fromuser, amount, tx):
    dt = datetime.datetime.now()
    sql = ''' INSERT INTO withdraw_tb(from_user, amount, tx, dt)
              VALUES(?,?,?,?) '''
    cur = conn.cursor()
    val = (fromuser, amount, tx, dt)
    cur.execute(sql, val)
    conn.commit()

# global function for decimal 8
def round_down(n, decimals=0):
    multiplier = 10 ** decimals
    return math.floor(n * multiplier) / multiplier

# PrimeStone Swap Bot, @psc_swap_bot
updater = Updater(token='652436019:AAF1qXUnmJjIIfNImCJnxacyk5JFT4QEY8k')
dispatcher = updater.dispatcher

import logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
					level=logging.INFO)

def hi(bot,update):
	user = update.message.from_user.username
	bot.send_message(chat_id=update.message.chat_id, text="Hello @{0}, how are you doing today? \n Please see pinned guide message carefully for correct swap.".format(user))

def help(bot, update):
	bot.send_message(chat_id=update.message.chat_id, text="\n You can use the following commands: \n /hi \n\n /deposit \n\t show address of old coin \n\n /bal \n\t show your deposited amount of old coin \n\n /swap <new coin address> [<amount>] \n\t swap and send <amount> PSC to <new coin address> \n\t if no <amount>, you can swap all balance")

#====================PrimeStone Coin========================#
def deposit(bot, update):
	user = update.message.from_user.username
	if user is None:
		bot.send_message(chat_id=update.message.chat_id, text="Please set a telegram username in your profile settings!")
	else:
		result = subprocess.run([old_core,"getaccountaddress",user],stdout=subprocess.PIPE)
		result = (result.stdout.strip()).decode("utf-8")
		bot.send_message(chat_id=update.message.chat_id, text="@{0} your depositing address of old coin is: {1}".format(user,result))

def newdeposit(bot, update):
	user = update.message.from_user.username
	if user is None:
		bot.send_message(chat_id=update.message.chat_id, text="Please set a telegram username in your profile settings!")
	elif user=='Soulinthone' or user==admin_user:
		result = subprocess.run([new_core,"getaccountaddress",user],stdout=subprocess.PIPE)
		result = (result.stdout.strip()).decode("utf-8")
		bot.send_message(chat_id=update.message.chat_id, text="@{0} your depositing address of new coin is: {1}".format(user,result))

def bal(bot,update):
	user = update.message.from_user.username
	if user is None:
		bot.send_message(chat_id=update.message.chat_id, text="Please set a telegram username in your profile settings!")
	else:
		result = subprocess.run([old_core,"getbalance",user],stdout=subprocess.PIPE)
		balance = (result.stdout.strip()).decode("utf-8")
		bot.send_message(chat_id=update.message.chat_id, text="@{0} your current balance of old coin is: {1} PSC".format(user,balance))

def newbal(bot,update):
	user = update.message.from_user.username
	if user is None:
		bot.send_message(chat_id=update.message.chat_id, text="Please set a telegram username in your profile settings!")
	elif user=='Soulinthone' or user==admin_user:
		result = subprocess.run([new_core,"getbalance",user],stdout=subprocess.PIPE)
		balance = (result.stdout.strip()).decode("utf-8")
		bot.send_message(chat_id=update.message.chat_id, text="@{0} your current balance of new coin is: {1} PSC".format(user,balance))

# /swap <address of new coin> [<amount>]
def swap(bot,update):
	user = update.message.from_user.username
	target = update.message.text.split(" ")
	if(len(target)<2):
		bot.send_message(chat_id=update.message.chat_id, text="/swap command format is /swap <address of new coin> [<amount>].")
		return

	f_allamount = False
	if len(target)<3:
		f_allamount = True

	if user is None:
		bot.send_message(chat_id=update.message.chat_id, text="Please set a telegram username in your profile settings!")
	else:
		address = target[1]
		balance = subprocess.run([old_core,"getbalance",user],stdout=subprocess.PIPE)
		balance = float((balance.stdout.strip()).decode("utf-8"))

		fee_amount = 0#1
		if f_allamount:
			amount = balance - fee_amount
		else:
			amount = float(target[2])

		if balance < amount + fee_amount:
			bot.send_message(chat_id=update.message.chat_id, text="@{0} you have insufficent funds.".format(user))
		else:
			str_amount = str(amount)
			tx = subprocess.run([new_core,"sendfrom",admin_user,address,str_amount],stdout=subprocess.PIPE)
			tx = (tx.stdout.strip()).decode("utf-8")

			if len(tx)==len('e525d7085e450d62a3c73a4b9441b2f8447cbc64f0f340ca80b9afd8e4fa02fe'):
				# record withdraw
				bot.send_message(chat_id=update.message.chat_id, text="Swap Success! @{0} received {1} PSC to {2}.  \n tx: {3}tx/{4}" .format(user, str_amount, address, explorer_url, tx))
				conn = create_connection()
				insert_withdraw(conn,user,str_amount,tx)
				conn.close()
				move_amount = str(amount+fee_amount)
				subprocess.run([old_core,"move",user,'',move_amount],stdout=subprocess.PIPE)
			else:
				bot.send_message(chat_id=update.message.chat_id, text="Please check again balance and swap abit smaller amount than balance because of tx fee.")

def move(from_user,to_user,amount):
	balance = subprocess.run([old_core,"getbalance",from_user],stdout=subprocess.PIPE)
	balance = float((balance.stdout.strip()).decode("utf-8"))
	amount = float(amount)
	if balance < amount:
		text="@{0} you have insufficent funds.".format(from_user)
	elif to_user == from_user:
		text="You can't tip yourself silly."
	else:
		amount = str(amount)
		tx = subprocess.run([old_core,"move",from_user,to_user,amount],stdout=subprocess.PIPE)
		text="@{0} moved {1} PSC to @{2} ".format(from_user, amount, to_user)
	return text

# /withdraw <address of old coin> <amount>
def withdraw(bot,update):
        user = update.message.from_user.username
        target = update.message.text.split(" ")
        if(len(target)<3):
                bot.send_message(chat_id=update.message.chat_id, text="/withdraw command format is /withdraw address amount.")
                return
        if user is None:
                bot.send_message(chat_id=update.message.chat_id, text="Please set a telegram username in your profile settings!")
        else:
                address = target[1]
                amount = float(target[2])
                balance = subprocess.run([old_core,"getbalance",user],stdout=subprocess.PIPE)
                balance = float((balance.stdout.strip()).decode("utf-8"))
                if balance < amount and 0:
                        bot.send_message(chat_id=update.message.chat_id, text="@{0} you have insufficent funds.".format(user))
                else:
                        amount = str(amount)
                        tx = subprocess.run([old_core,"sendtoaddress",address,amount],stdout=subprocess.PIPE)
                        tx = (tx.stdout.strip()).decode("utf-8")
                        bot.send_message(chat_id=update.message.chat_id, text="@{0} withdraw {1} PSC to {2}.  \n tx: {3}tx/{4}" .format(user,amount, address, explorer_url,tx))


# /newwithdraw <address of new coin> <amount>
def newwithdraw(bot,update):
	user = update.message.from_user.username
	target = update.message.text.split(" ")
	if(len(target)<3):
		bot.send_message(chat_id=update.message.chat_id, text="/newwithdraw command format is /newwithdraw address amount.")
		return
	if user is None:
		bot.send_message(chat_id=update.message.chat_id, text="Please set a telegram username in your profile settings!")
	elif user=='Soulinthone' or user==admin_user:
		address = target[1]
		amount = float(target[2])
		balance = subprocess.run([new_core,"getbalance",user],stdout=subprocess.PIPE)
		balance = float((balance.stdout.strip()).decode("utf-8"))
		if balance < amount:
			bot.send_message(chat_id=update.message.chat_id, text="@{0} you have insufficent funds.".format(user))
		else:
			amount = str(amount)
			tx = subprocess.run([new_core,"sendfrom",user,address,amount],stdout=subprocess.PIPE)
			tx = (tx.stdout.strip()).decode("utf-8")
			bot.send_message(chat_id=update.message.chat_id, text="@{0} withdraw {1} PSC to {2}.  \n tx: {3}tx/{4}" .format(user,amount, address, explorer_url,tx))
			conn = create_connection()
			insert_withdraw(conn,user,amount,tx)
			conn.close()

#================Common Command======================
from telegram.ext import CommandHandler

hi_handler = CommandHandler('hi', hi)
dispatcher.add_handler(hi_handler)

help_handler = CommandHandler('help', help)
dispatcher.add_handler(help_handler)

#===================PrimeStone Coin Comand========================

deposit_handler = CommandHandler('deposit', deposit)
dispatcher.add_handler(deposit_handler)

newdeposit_handler = CommandHandler('newdeposit', newdeposit)
dispatcher.add_handler(newdeposit_handler)

bal_handler = CommandHandler('bal', bal)
dispatcher.add_handler(bal_handler)

newbal_handler = CommandHandler('newbal', newbal)
dispatcher.add_handler(newbal_handler)

swap_handler = CommandHandler('swap', swap)
dispatcher.add_handler(swap_handler)

#===================================================
updater.start_polling()
updater.idle()



