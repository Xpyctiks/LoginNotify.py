#!/usr/bin/env python3

import os
import sys
import subprocess
import json
import logging
import logging.handlers
import requests
import mysql.connector
from ipwhois import IPWhois
from datetime import datetime

"Start of global variables and function settings"
CONFIG_FILE = os.path.abspath(os.path.dirname(__file__))+"/login-notify.conf"
TELEGRAM_TOKEN = ""
TELEGRAM_CHATID = ""
DB_HOST = ""
DB_USER = ""
DB_PASS = ""
DB_NAME = ""
DB_PORT = ""
DB_SOCKET = ""
CONNECT_VIA = ""

def load_config():
    error = 0
    "Check if config file exists. If not - generate the new one."
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r',encoding='utf8') as file:
            config = json.load(file)
        "Check if all parameters are set. If not - shows the error message"
        for id,key in enumerate(config.keys()):
            if not config.get(key):
                print(f"Parameter {key} is not defined!")
                error+=1
        if error != 0:
            print(f"Some variables are not set in config file. Please fix it then run the program again.")
            quit()
        global TELEGRAM_TOKEN
        global TELEGRAM_CHATID
        global DB_HOST
        global DB_USER
        global DB_PASS
        global DB_NAME
        global DB_PORT
        global DB_SOCKET
        global CONNECT_VIA
        DB_HOST = config.get('dbHost')
        DB_USER = config.get('dbUser')
        DB_PASS = config.get('dbPass')
        DB_NAME = config.get('dbName')
        DB_PORT = config.get('dbPort')
        DB_SOCKET = config.get('socket')
        CONNECT_VIA = config.get('connectVia')
        TELEGRAM_TOKEN = config.get('telegramToken')
        TELEGRAM_CHATID = config.get('telegramChat')       
        return config
    else:
        generate_default_config()

def generate_default_config():
    config = {
        "dbUser": "LoginNotify",
        "dbPass": "",
        "dbName": "LoginNotify",
        "dbHost": "127.0.0.1",
        "dbPort": "3306",
        "socket": "/var/run/mysql.sock",
        "telegramToken": "",
        "telegramChat": "",
        "connectVia": "port",
    }
    with open(CONFIG_FILE, 'w',encoding='utf8') as file:
        json.dump(config, file, indent=4)
    os.chmod(CONFIG_FILE, 0o600)
    send_to_log(f"info",f"First launch. New config file {CONFIG_FILE} generated and needs to be configured.Then you will be able to autocreate MySQL tables for this program.")
    print(f"First launch. New config file {CONFIG_FILE} generated and needs to be configured.Then you will be able to autocreate MySQL tables for this program.")
    quit()

def show_help():
    print(f"Usage:\n\t./<this_script_name> initDB <mysql_root_pwd> ")
    print(f"\t<mysql_root_pwd> - password of mysql root account to create everything we need.All settings for creation will be taken from config file!")
    print(f"\tIf the root password is not set - this script will try to make all settings using DB/User/Pass from config file.\n")
    print(f"\t./<this_script_name> addIP <IP> <Comment>")
    print(f"\t<IP> - IP address to be added\n\t<Comment> - comment for IP. Should be not large.\n")
    print(f"\t./<this_script_name> delIP <IP>")
    print(f"\t<IP> - IP address to be removed")
    quit()

def send_to_log(type,logData):
    logger = logging.getLogger('logger')
    fhandle = logging.handlers.SysLogHandler(address='/dev/log')
    logger.addHandler(fhandle)
    if type == "error":
        logger.setLevel(logging.ERROR)
        logger.error(f"Login-Notify: {logData}")
    else:
        logger.setLevel(logging.INFO)
        logger.info(f"Login-Notify: {logData}")

def send_to_telegram(subject,message):
    headers = {
        'Content-Type': 'application/json',
    }
    data = {
        "chat_id": f"{TELEGRAM_CHATID}",
        "text": f"{subject}\n{message}",
    }
    response = requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", timeout=10, headers=headers, json=data)
    print(response.status_code)
    if response.status_code != 200:
        err = response.json()
        send_to_log(f"error",f"Telegram bot error! Data: {err}")

def initDB():
    global DB_HOST
    global DB_USER
    global DB_PASS
    global DB_NAME
    global DB_PORT
    global DB_SOCKET
    global CONNECT_VIA
    DB_ROOT_PWD = ""
    DB_ROOT_USER = ""
    if len(sys.argv) >= 3:
        "If mysql root password is set - prepare everything to create from zero."
        DB_ROOT_PWD = sys.argv[2]
        DB_ROOT_USER = "root"
        DB = f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;"
        USR = f"CREATE USER IF NOT EXISTS '{DB_USER}'@'%' IDENTIFIED BY '{DB_PASS}';"
        GRN = f"GRANT ALL ON {DB_NAME}.* to '{DB_USER}'@'%';"
        FLS = f"FLUSH PRIVILEGES;"
    else:
        "If mysql root password is not set - almost done. Just create table."
        DB_ROOT_PWD = DB_PASS
        DB_ROOT_USER = DB_USER
        DB = ""
        USR = ""
        GRN = ""
        FLS = ""
    try:
        if CONNECT_VIA == "port":
            connection = mysql.connector.connect(
                host=DB_HOST,
                user=DB_ROOT_USER,
                password=DB_ROOT_PWD,
                port=DB_PORT,
                charset="utf8mb4",
                collation="utf8mb4_bin",
            )
        elif CONNECT_VIA == "socket":
            connection = mysql.connector.connect(
                host=DB_HOST,
                user=DB_ROOT_USER,
                password=DB_ROOT_PWD,
                unix_socket=DB_SOCKET,
                charset="utf8mb4",
                collation="utf8mb4_bin",
            )
        query = [
            f"{DB}",
            f"USE `{DB_NAME}`;",
            f"CREATE TABLE `tIPs` (`Id` int(10) UNSIGNED NOT NULL,`IP` varchar(18) COLLATE utf8mb4_bin NOT NULL,`Created` datetime NOT NULL DEFAULT current_timestamp(),`Comment` varchar(500) COLLATE utf8mb4_bin DEFAULT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;",
            f"ALTER TABLE `tIPs` ADD PRIMARY KEY (`Id`), ADD UNIQUE KEY `IP` (`IP`);",
            f"ALTER TABLE `tIPs` MODIFY `Id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=1;",
            f"{USR}",
            f"{GRN}",
            f"{FLS}",
        ]
        cursor = connection.cursor(buffered=True)
        for command in query:
            cursor.execute(command)
        connection.commit()
        cursor.close()
        connection.close()
        print(f"Database initialized successfully!")
        print(f"Finally you need to add to the end of /etc/pam.d/sshd next string: \"session optional pam_exec.so [{os.path.abspath(__file__)}]\"")
        print(f"If you want to log TTYs logins, not only SSH: add to the end of /etc/pam.d/login the string above too")
        send_to_log(f"info",f"MySQL database initialized successfully!")
    except Exception as msg:
        print(f"MySQL Error! {msg}")
        send_to_log(f"error",{msg})
        quit()

def addIP():
    if len(sys.argv) < 4:
        print(f"Not enough parameters! Usage: ./<this_script_name> addIP <IP_address> <comment>")
        quit()
    try:
        if CONNECT_VIA == "port":
            connection = mysql.connector.connect(
                host=DB_HOST,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASS,
                port=DB_PORT,
                charset="utf8mb4",
                collation="utf8mb4_bin",
            )
        elif CONNECT_VIA == "socket":
            connection = mysql.connector.connect(
                host=DB_HOST,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASS,
                unix_socket=DB_SOCKET,
                charset="utf8mb4",
                collation="utf8mb4_bin",
            )
        query = (f"INSERT INTO `tIPs` (`IP`, `Comment`) VALUES ('{sys.argv[2]}', '{sys.argv[3]}');")
        cursor = connection.cursor(buffered=True)
        cursor.execute(query)
        connection.commit()
        cursor.close()
        connection.close()
        print(f"IP: \"{sys.argv[2]}\" with comment: \"{sys.argv[3]}\" successfully added!")
        send_to_log(f"info",f"IP: \"{sys.argv[2]}\" with comment: \"{sys.argv[3]}\" successfully added!")
    except Exception as msg:
        print(f"MySQL Error! {msg}")
        send_to_log(f"error",{msg})
        quit()

def delIP():
    if len(sys.argv) < 3:
        print(f"Not enough parameters! Usage: ./<this_script_name> delIP <IP_address>")
        quit()
    try:
        if CONNECT_VIA == "port":
            connection = mysql.connector.connect(
                host=DB_HOST,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASS,
                port=DB_PORT,
                charset="utf8mb4",
                collation="utf8mb4_bin",
            )
        elif CONNECT_VIA == "socket":
            connection = mysql.connector.connect(
                host=DB_HOST,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASS,
                unix_socket=DB_SOCKET,
                charset="utf8mb4",
                collation="utf8mb4_bin",
            )
        query = (f"DELETE FROM `tIPs` WHERE IP='{sys.argv[2]}'")
        cursor = connection.cursor(buffered=True)
        cursor.execute(query)
        connection.commit()
        cursor.close()
        connection.close()
        print(f"IP: \"{sys.argv[2]}\" deleted successfully!")
        send_to_log(f"info",f"IP: \"{sys.argv[2]}\" deleted successfully!")
    except Exception as msg:
        print(f"MySQL Error! {msg}")
        send_to_log(f"error",{msg})
        quit()

def mainCheck():
    try:
        if CONNECT_VIA == "port":
            connection = mysql.connector.connect(
                host=DB_HOST,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASS,
                port=DB_PORT,
                charset="utf8mb4",
                collation="utf8mb4_bin",
            )
        elif CONNECT_VIA == "socket":
            connection = mysql.connector.connect(
                host=DB_HOST,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASS,
                unix_socket=DB_SOCKET,
                charset="utf8mb4",
                collation="utf8mb4_bin",
            )
        PAM_RHOST=os.getenv("PAM_RHOST")
        PAM_USER=os.getenv("PAM_USER")
        PAM_SERVICE=os.getenv("PAM_SERVICE")
        PAM_TTY=os.getenv("PAM_TTY")
        PAM_TYPE=os.getenv("PAM_TYPE")
        if PAM_TYPE == "close_session":
            PAM_TYPE="🏁Logout"
        if PAM_TYPE == "open_session":
            PAM_TYPE="🏄Login"
        query = f"SELECT * FROM `tIPs` where IP='{PAM_RHOST}'"
        cursor = connection.cursor(buffered=True)
        cursor.execute(query)
        res = cursor.fetchall()
        time=datetime.now().strftime('%H:%M:%S %d.%m.%Y')
        if len(res) > 0:
            for i in res:
                send_to_log("info",f"Type:{PAM_TYPE} User:{PAM_USER} Service:{PAM_SERVICE} TTY:{PAM_TTY} IP:{PAM_RHOST} Comment:{i[3]}")
                send_to_telegram(f"{PAM_TYPE} to {os.uname().nodename}",f"Service: {PAM_SERVICE} TTY: {PAM_TTY} - {time}\nUser: {PAM_USER}\nIP: {PAM_RHOST}\nComment: {i[3]}")
        else:
            try:
                obj = IPWhois(PAM_RHOST)
                info = obj.lookup_whois()
                COUNTRY=info['asn_country_code']
                CITY=info['nets'][0]['address']
                DESC=info['asn_description']
            except Exception as msg:
                COUNTRY=msg
                CITY=""
                DESC=""
            send_to_log(f"info",f"Type:{PAM_TYPE} User:{PAM_USER} Service:{PAM_SERVICE} TTY:{PAM_TTY} IP:{PAM_RHOST} Info: {COUNTRY},{CITY},{DESC}")
            send_to_telegram(f"{PAM_TYPE} to {os.uname().nodename} from unconfirmed addr",f"Service: {PAM_SERVICE} TTY: {PAM_TTY} - {time}\nUser: {PAM_USER}\nIP: {PAM_RHOST}\nInfo: {COUNTRY},{CITY},{DESC}")
        cursor.close()
        connection.close()
    except Exception as msg:
        print(f"MySQL Error! {msg}")
        send_to_log(f"error",{msg})
        quit()

def main():
    config = load_config()
    if len(sys.argv) >= 2:
        if sys.argv[1] == "--help" or sys.argv[1] == "-h":
            show_help()
        elif sys.argv[1] == "initDB":
            initDB()
        elif sys.argv[1] == "addIP":
            addIP()
        elif sys.argv[1] == "delIP":
            delIP()
    else:
        if not os.getenv("PAM_USER") or not os.getenv("PAM_TTY") or not os.getenv("PAM_RHOST") or not os.getenv("PAM_TYPE") or not os.getenv("PAM_SERVICE"):
            print(f"The script without parameters should be run only by PAM auth proceess to work properly.")
            print(f"Seems you are running the script from console but without any parameters for some actions.")
            show_help()
        mainCheck()

if __name__ == "__main__":
    main()