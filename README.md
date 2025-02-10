Нужна версия python 3.11.0

В requirements.txt указаны все нужные зависимости и конкретные версии некоторых, так как со всеми свежими версиям не работает

Чтобы установить библиотеки из requirements.txt - pip install requirements.txt

Чтобы получить TELEGRAM_CHAT_ID нужно воспользоваться Telegram ботом @getmyid_bot

DB_NAME не трогаем

!!! Нужно поменять все collections на collections.abc в env/lib/wordpress_xmlrpc/base.py