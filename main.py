#!/usr/bin/env python3
"""
Капри — упрощённый голосовой ассистент для Android (Kivy)
Офлайн STT (Vosk) + системный TTS + базовые команды.
"""

import json
import os
import re
import threading
import time
import urllib.parse
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.lang import Builder
from kivy.properties import StringProperty, BooleanProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.utils import platform

# ---------- пути ----------
BASE = Path(__file__).parent
MODEL_PATH = BASE / "data" / "vosk-model-small-ru-0.22"

# ---------- команды (упрощённые) ----------
APPS = {
    "youtube": "com.google.android.youtube",
    "ютуб": "com.google.android.youtube",
    "телеграм": "org.telegram.messenger",
    "telegram": "org.telegram.messenger",
    "хром": "com.android.chrome",
    "chrome": "com.android.chrome",
    "браузер": "com.android.chrome",
    "настройки": "com.android.settings",
    "музыка": "com.google.android.apps.youtube.music",
    "спотифай": "com.spotify.music",
    "spotify": "com.spotify.music",
    "камера": "com.sec.android.app.camera",
    "галерея": "com.sec.android.gallery3d",
}


def norm(s: str) -> str:
    s = s.lower().replace("ё", "е")
    s = re.sub(r"[^\w\s\.\-:/]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def speak(text: str):
    """TTS через plyer (на Android использует системный движок)."""
    if not text:
        return
    try:
        from plyer import tts
        tts.speak(text)
    except Exception as e:
        print("TTS error:", e)


def open_url(url: str):
    try:
        from plyer import browser
        browser.open(url)
    except Exception:
        # fallback через intent
        if platform == "android":
            try:
                from jnius import autoclass
                Intent = autoclass("android.content.Intent")
                Uri = autoclass("android.net.Uri")
                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
                PythonActivity.mActivity.startActivity(intent)
            except Exception as e:
                print("open_url error:", e)


def open_app(package: str):
    if platform != "android":
        print(f"[desktop] open app {package}")
        return
    try:
        from jnius import autoclass
        Intent = autoclass("android.content.Intent")
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        pm = PythonActivity.mActivity.getPackageManager()
        intent = pm.getLaunchIntentForPackage(package)
        if intent:
            PythonActivity.mActivity.startActivity(intent)
        else:
            speak("Приложение не найдено")
    except Exception as e:
        print("open_app error:", e)
        speak("Не удалось открыть")


def media_key(keycode: int):
    """Симуляция медиа-кнопок (play/pause/next...)."""
    if platform != "android":
        return
    try:
        from jnius import autoclass
        Intent = autoclass("android.content.Intent")
        KeyEvent = autoclass("android.view.KeyEvent")
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        # Broadcast media button
        intent = Intent(Intent.ACTION_MEDIA_BUTTON)
        # Проще через AudioManager
        Context = autoclass("android.content.Context")
        AudioManager = autoclass("android.media.AudioManager")
        am = PythonActivity.mActivity.getSystemService(Context.AUDIO_SERVICE)
        am.dispatchMediaKeyEvent(KeyEvent(KeyEvent.ACTION_DOWN, keycode))
        am.dispatchMediaKeyEvent(KeyEvent(KeyEvent.ACTION_UP, keycode))
    except Exception as e:
        print("media_key error:", e)


def set_volume_direction(direction: str):
    if platform != "android":
        return
    try:
        from jnius import autoclass
        Context = autoclass("android.content.Context")
        AudioManager = autoclass("android.media.AudioManager")
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        am = PythonActivity.mActivity.getSystemService(Context.AUDIO_SERVICE)
        stream = AudioManager.STREAM_MUSIC
        if direction == "up":
            am.adjustStreamVolume(stream, AudioManager.ADJUST_RAISE, AudioManager.FLAG_SHOW_UI)
        elif direction == "down":
            am.adjustStreamVolume(stream, AudioManager.ADJUST_LOWER, AudioManager.FLAG_SHOW_UI)
        elif direction == "mute":
            am.adjustStreamVolume(stream, AudioManager.ADJUST_MUTE, AudioManager.FLAG_SHOW_UI)
    except Exception as e:
        print("volume error:", e)


def handle_command(text: str) -> str:
    """Обработать команду, вернуть текст ответа."""
    c = norm(text)
    if not c:
        return ""

    # громкость
    if re.search(r"громче|увелич\w* громк", c):
        set_volume_direction("up")
        return "Громче"
    if re.search(r"тише|уменьш\w* громк", c):
        set_volume_direction("down")
        return "Тише"
    if re.search(r"(выключ|отключ|убери|замуть)\w* звук|без звука", c):
        set_volume_direction("mute")
        return "Звук выключен"

    # медиа
    if re.search(r"пауз\w*|останови|стопни", c):
        media_key(85)  # KEYCODE_MEDIA_PLAY_PAUSE
        return "Пауза"
    if re.search(r"продолж\w*|играй|сними (с )?пауз", c):
        media_key(85)
        return "Играю"
    if re.search(r"следующ\w*|дальше", c):
        media_key(87)  # NEXT
        return "Следующий"
    if re.search(r"предыдущ\w*|назад", c):
        media_key(88)  # PREVIOUS
        return "Предыдущий"

    # приложения
    for name, pkg in APPS.items():
        if re.search(rf"(открой|запусти|включи)\w*.*{name}", c) or re.fullmatch(rf"(открой |запусти )?{name}", c):
            open_app(pkg)
            return f"Открываю {name}"

    # YouTube
    m = re.search(r"(открой |найди |включи |поставь )?(на )?ютуб[е]? (.+)", c)
    if m and m.group(3):
        q = m.group(3).strip()
        open_url("https://www.youtube.com/results?search_query=" + urllib.parse.quote(q))
        return f"Ищу на ютубе {q}"
    if re.search(r"(открой|запусти) (ютуб|youtube)", c):
        open_app(APPS["youtube"])
        return "Открываю ютуб"

    # поиск
    m = re.search(r"(найди|поиск|поищи|гугл|загугли)\w* (.+)", c)
    if m:
        q = m.group(2).strip()
        open_url("https://www.google.com/search?q=" + urllib.parse.quote(q))
        return f"Ищу {q}"

    # время
    if re.search(r"который час|сколько времени|время", c):
        return "Сейчас " + time.strftime("%H:%M")
    if re.search(r"какое (сегодня )?число|какая (сегодня )?дата", c):
        return "Сегодня " + time.strftime("%d.%m.%Y")

    if re.search(r"что ты (умеешь|можешь)|помощь|список команд", c):
        return ("Я умею: громче/тише, пауза, следующий трек, "
                "открыть ютуб/телеграм/хром, найти что-нибудь, сказать время. "
                "Говори «Капри» и команду.")

    # fallback — поиск
    if len(c) > 3:
        open_url("https://www.google.com/search?q=" + urllib.parse.quote(c))
        return "Ищу в интернете"

    return ""


# ---------- Kivy UI ----------
KV = """
<RootWidget>:
    orientation: "vertical"
    padding: dp(16)
    spacing: dp(12)
    canvas.before:
        Color:
            rgba: 0.04, 0.02, 0.08, 1
        Rectangle:
            pos: self.pos
            size: self.size

    Label:
        text: "КАПРИ"
        font_size: "28sp"
        bold: True
        color: 0.0, 0.94, 1, 1
        size_hint_y: None
        height: dp(40)

    Label:
        text: root.status
        font_size: "16sp"
        color: 0.7, 0.7, 0.85, 1
        size_hint_y: None
        height: dp(30)

    ScrollView:
        size_hint_y: 0.45
        Label:
            text: root.log_text
            font_size: "14sp"
            color: 0.85, 0.85, 0.95, 1
            text_size: self.width, None
            size_hint_y: None
            height: self.texture_size[1]
            padding: dp(8), dp(8)
            halign: "left"
            valign: "top"

    BoxLayout:
        size_hint_y: None
        height: dp(70)
        spacing: dp(12)

        Button:
            text: "СЛУШАТЬ" if not root.listening else "СТОП"
            font_size: "18sp"
            bold: True
            background_color: (0.0, 0.75, 0.85, 1) if not root.listening else (0.85, 0.2, 0.35, 1)
            on_press: root.toggle_listen()

        Button:
            text: "ОЧИСТИТЬ"
            font_size: "16sp"
            background_color: 0.25, 0.2, 0.4, 1
            on_press: root.clear_log()

    Label:
        text: "Скажи «Капри» + команду\\nили нажми СЛУШАТЬ"
        font_size: "13sp"
        color: 0.5, 0.5, 0.65, 1
        size_hint_y: None
        height: dp(40)
        halign: "center"
"""


class RootWidget(BoxLayout):
    status = StringProperty("Готова")
    log_text = StringProperty("— лог команд —\n")
    listening = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._listen_thread = None
        self._stop_event = threading.Event()
        self.model = None
        self.rec = None

    def add_log(self, text: str):
        self.log_text += text + "\n"
        # ограничиваем длину
        lines = self.log_text.splitlines()
        if len(lines) > 40:
            self.log_text = "\n".join(lines[-35:]) + "\n"

    def clear_log(self):
        self.log_text = "— лог команд —\n"

    def toggle_listen(self):
        if self.listening:
            self.stop_listening()
        else:
            self.start_listening()

    def start_listening(self):
        if platform == "android":
            self._request_permissions()
        self.listening = True
        self.status = "Слушаю..."
        self._stop_event.clear()
        self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._listen_thread.start()

    def stop_listening(self):
        self.listening = False
        self.status = "Остановлено"
        self._stop_event.set()

    def _request_permissions(self):
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.RECORD_AUDIO, Permission.INTERNET])
        except Exception as e:
            print("permissions:", e)

    def _listen_loop(self):
        try:
            import vosk
            import sounddevice as sd

            if not MODEL_PATH.is_dir():
                self._ui_status("Модель Vosk не найдена")
                self.listening = False
                return

            vosk.SetLogLevel(-1)
            if self.model is None:
                self.model = vosk.Model(str(MODEL_PATH))
            self.rec = vosk.KaldiRecognizer(self.model, 16000)

            def callback(indata, frames, time_info, status):
                if self._stop_event.is_set():
                    raise sd.CallbackStop()
                data = bytes(indata)
                if self.rec.AcceptWaveform(data):
                    result = json.loads(self.rec.Result())
                    text = result.get("text", "").strip()
                    if text:
                        self._on_text(text)

            with sd.RawInputStream(samplerate=16000, blocksize=8000,
                                   dtype="int16", channels=1, callback=callback):
                while not self._stop_event.is_set():
                    time.sleep(0.05)

        except Exception as e:
            self._ui_status(f"Ошибка: {e}")
            print("listen error:", e)
        finally:
            self.listening = False
            self._ui_status("Готова")

    @mainthread
    def _ui_status(self, text):
        self.status = text

    @mainthread
    def _on_text(self, text: str):
        self.add_log(f"Услышала: {text}")
        t = norm(text)
        wake = any(w in t for w in ("капри", "каприкорн"))
        if wake:
            for w in ("каприкорн", "капри"):
                t = t.replace(w, " ")
            t = re.sub(r"\s+", " ", t).strip()
            if not t:
                speak("Слушаю")
                self.add_log("→ Слушаю")
                return
            reply = handle_command(t)
            if reply:
                self.add_log(f"→ {reply}")
                speak(reply)
        else:
            # без wake-word тоже обрабатываем, если пользователь нажал кнопку
            reply = handle_command(t)
            if reply:
                self.add_log(f"→ {reply}")
                speak(reply)


class CapriApp(App):
    def build(self):
        self.title = "Капри"
        Builder.load_string(KV)
        return RootWidget()

    def on_start(self):
        if platform == "android":
            try:
                from android.permissions import request_permissions, Permission
                request_permissions([Permission.RECORD_AUDIO, Permission.INTERNET])
            except Exception:
                pass


if __name__ == "__main__":
    CapriApp().run()
