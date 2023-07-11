import platform
import socket
from datetime import datetime

import psutil
from pyrogram import Client, types

from .. import __version__, loader, utils


def byter(num: float, suffix: str = "B") -> str:
    for unit in ["B", "K", "M", "G", "T", "P", "E", "Z"]:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0

    return "%.1f%s%s" % (num, "Yi", suffix)

@loader.module(name="UserBot")
class AboutMod(loader.Module):
    """Узнайте что такое юзербот, или информацию о вашем 🈂️seika"""
    
    async def info_cmd(self, app: Client, message: types.Message):
        """информацию о вашем 🈂️seika."""
        await utils.answer(message, "☕")
        me: types.User = await app.get_me()
        psutil_winerr = False

        try:
            boot = psutil.boot_time()
            bt = datetime.fromtimestamp(boot)
        except:
            psutil_winerr = True

        await utils.answer(
            message,
            f"""
`🈂️ seika | UserBot`

`💻 UserBot`
<b>Владелец</b>: `{me.username}`
<b>Версия</b>: `v{__version__}`
""" + (f"""
`🧠 Процессор`
<b>Использование</b>: `{int(psutil.cpu_percent())}%`
<b>Ядер</b>: `{psutil.cpu_count()}`

`🗃 ОЗУ`
<b>Использование</b>: `{byter(psutil.virtual_memory().used)}`/`{byter(psutil.virtual_memory().total)}`

`💾 ПЗУ`
[/] | <b>Использование</b>: `{byter(psutil.disk_usage("/").used)}`/`{byter(psutil.disk_usage("/").total)}` (`{psutil.disk_usage("/").percent}%`)

`🖥️ Хост`
<b>Система</b>: `{platform.uname().system}`
<b>Узел</b>: `{platform.uname().node}`
<b>Релиз</b>: `{platform.uname().release}`
<b>Версия</b>: `{platform.uname().version}`
<b>Архитектура</b>: `{platform.machine()}`
<b>Процессор</b>: `{platform.processor()}`
<b>Имя хоста</b>: `{socket.gethostname()}`
<b>Работает с</b>: `{bt.year}/{bt.month}/{bt.day} {bt.hour}:{bt.minute}:{bt.second}`""" if not psutil_winerr else ""))
        
    async def ubinfo_cmd(self, app: Client, message: types.Message, args: str):
        """информация о UserBot"""
        await utils.answer(message, "☕")
        await utils.answer(message, '''🤔 <b>Что такое юзербот?</b>
        
📚 <b>Юзербот это</b> - <b>Сборник разных програм</b> для взаймодeйствия с Telegarm API
А с помощью взаймодействия с Telegarm API <b>можно написать разныe скрипты</b> для автоматизаций некоторых действий со стороны пользователя такие как: <b>Присоединение к каналам, отправление сообщений, и т.д</b>

🤔 <b>Чем отличается юзербот от обычного бота?</b>

🤭 <b>Юзербот может выполняться на аккаунте обычного пользователя</b>
Например: @pavel_durov А бот может выполняться только на специальных бот аккаунтах например: @examplebot
<b>Юзерботы довольно гибкие</b> в плане настройки, у них больше функций.

🛑 <b>Поддерживаются ли оффициально юзерботы телеграмом?</b>

🚫 <b>Нет.</b> Они оффициально не поддерживаются, но вас не заблокируют за использование юзерботов.
Но <b>могут заблокировать в случае выполнения вредоносного кода или за злоупотребление Telegarm API</b> на вашем аккаунте, так что владельцу юзербота надо тщательно проверять что выполняется на вашем аккаунте.''')
