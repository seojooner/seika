import logging
import asyncio

import os
import re
import sys
import time

import atexit
import tempfile

import requests

from typing import List

from git import Repo
from git.exc import GitCommandError

from pyrogram import Client, types
from .. import loader, utils

VALID_URL = r"[-[\]_.~:/?#@!$&'()*+,;%<=>a-zA-Z0-9]+"
VALID_PIP_PACKAGES = re.compile(
    r"^\s*# required:(?: ?)((?:{url} )*(?:{url}))\s*$".format(url=VALID_URL),
    re.MULTILINE,
)
GIT_REGEX = re.compile(
    r"^https?://github\.com((?:/[a-z0-9-]+){2})(?:/tree/([a-z0-9-]+)((?:/[a-z0-9-]+)*))?/?$",
    flags=re.IGNORECASE,
)


async def get_git_raw_link(repo_url: str):
    """Получить raw ссылку на репозиторий"""
    match = GIT_REGEX.search(repo_url)
    if not match:
        return False

    repo_path = match.group(1)
    branch = match.group(2)
    path = match.group(3)

    r = await utils.run_sync(requests.get, f"https://api.github.com/repos{repo_path}")
    if r.status_code != 200:
        return False

    branch = branch or r.json()["default_branch"]

    return f"https://raw.githubusercontent.com{repo_path}/{branch}{path or ''}/"


@loader.module(name="Loader")
class LoaderMod(loader.Module):
    """Загрузчик модулей"""

    async def dlmod_cmd(self, app: Client, message: types.Message, args: str):
        """Загрузить модуль по ссылке. Использование: dlmod <ссылка или all или ничего>"""
        modules_repo = self.db.get(
            "seika.loader", "repo",
            "https://github.com/CodWize/seika-modules"
        )
        api_result = await get_git_raw_link(modules_repo)
        if not api_result:
            return await utils.answer(
                message, "❌ Неверная ссылка на репозиторий.\n"
                        "Поменяй её с помощью команды: dlrepo <ссылка на репозиторий или reset>"
            )

        raw_link = api_result
        modules = await utils.run_sync(requests.get, raw_link + "all.txt")
        if modules.status_code != 200:
            return await utils.answer(
                message, (
                    f"❌ В <a href=\"{modules_repo}\">репозитории</a> не найден файл all.txt\n"
                ), disable_web_page_preview=True
            )

        modules: List[str] = modules.text.splitlines()

        if not args:
            text = (
                f"📥 Список доступных модулей с <a href=\"{modules_repo}\">репозитория</a>:\n\n"
                + "<code>all</code> - загрузит все модули\n"
                + "\n".join(
                    map("<code>{}</code>".format, modules))
            )
            return await utils.answer(
                message, text, disable_web_page_preview=True)

        error_text: str = None
        module_name: str = None
        count = 0

        if args == "all":
            for module in modules:
                module = raw_link + module + ".py"
                try:
                    r = await utils.run_sync(requests.get, module)
                    if r.status_code != 200:
                        raise requests.exceptions.RequestException
                except requests.exceptions.RequestException:
                    continue

                if not (module_name := await self.all_modules.load_module(r.text, r.url)):
                    continue

                self.db.set("seika.loader", "modules",
                            list(set(self.db.get("seika.loader", "modules", []) + [module])))
                count += 1
        else:
            if args in modules:
                args = raw_link + args + ".py"

            try:
                r = await utils.run_sync(requests.get, args)
                if r.status_code != 200:
                    raise requests.exceptions.ConnectionError

                module_name = await self.all_modules.load_module(r.text, r.url)
                if module_name is True:
                    error_text = "✅ Зависимости установлены. Требуется перезагрузка"

                if not module_name:
                    error_text = "❌ Не удалось загрузить модуль. Подробности смотри в логах"
            except requests.exceptions.MissingSchema:
                error_text = "❌ Ссылка указана неверно"
            except requests.exceptions.ConnectionError:
                error_text = "❌ Модуль недоступен по ссылке"
            except requests.exceptions.RequestException:
                error_text = "❌ Произошла непредвиденная ошибка. Подробности смотри в логах"

            if error_text:
                return await utils.answer(message, error_text)

            self.db.set("seika.loader", "modules",
                        list(set(self.db.get("seika.loader", "modules", []) + [args])))

        return await utils.answer(
            message, (
                f"✅ Модуль \"<code>{module_name}</code>\" загружен"
                if args != "all"
                else f"✅ Загружено <b>{count}</b> из <b>{len(modules)}</b> модулей"
            )
        )

    async def loadmod_cmd(self, app: Client, message: types.Message):
        """Загрузить модуль по файлу. Использование: <реплай на файл>"""
        reply = message.reply_to_message
        file = (
            message
            if message.document
            else reply
            if reply and reply.document
            else None
        )

        if not file:
            return await utils.answer(
                message, "❌ Нет реплая на файл")

        temp_file = tempfile.NamedTemporaryFile("w")
        await file.download(temp_file.name)

        try:
            with open(temp_file.name, "r", encoding="utf-8") as file:
                module_source = file.read()
        except UnicodeDecodeError:
            temp_file.close()
            return await utils.answer(
                message, "❌ Неверная кодировка файла")

        module_name = await self.all_modules.load_module(module_source)
        if module_name is True:
            return await utils.answer(
                message, "✅ Зависимости установлены. Требуется перезагрузка")

        if not module_name:
            return await utils.answer(
                message, "❌ Не удалось загрузить модуль. Подробности смотри в логах")

        temp_file.close()
        return await utils.answer(
            message, f"✅ Модуль \"<code>{module_name}</code>\" загружен")

    async def unloadmod_cmd(self, app: Client, message: types.Message, args: str):
        """Выгрузить модуль. Использование: unloadmod <название модуля>"""
        if not (module_name := self.all_modules.unload_module(args)):
            return await utils.answer(
                message, "❌ Неверное название модуля")

        return await utils.answer(
            message, f"✅ Модуль \"<code>{module_name}</code>\" выгружен")

    async def restart_cmd(self, app: Client, message: types.Message, update: bool = False):
        """Перезагрузка юзербота"""
        def restart() -> None:
            """Запускает загрузку юзербота"""
            os.execl(sys.executable, sys.executable, "-m", "seika")

        atexit.register(restart)
        self.db.set(
            "seika.loader", "restart", {
                "msg": f"{message.chat.id}:{message.id}",
                "start": time.time(),
                "type": "restart"
            }
        )

        await utils.answer(message, "🔁 Перезагрузка...")

        logging.info("Перезагрузка...")
        return sys.exit(0)


    async def dlrepo_cmd(self, app: Client, message: types.Message, args: str):
        """Установить репозиторий с модулями. Использование: dlrepo <ссылка на репозиторий или reset>"""
        if not args:
            return await utils.answer(
                message, "❌ Нет аргументов")

        if args == "reset":
            self.db.set(
                "seika.loader", "repo",
                "https://github.com/CodWize/seika-modules"
            )
            return await utils.answer(
                message, "✅ Ссылка на репозиторий была сброшена")

        if not await get_git_raw_link(args):
            return await utils.answer(
                message, "❌ Ссылка указана неверно")

        self.db.set("seika.loader", "repo", args)
        return await utils.answer(
            message, "✅ Ссылка на репозиторий установлена")
