# Капри — голосовой ассистент для Android (Kivy + Buildozer)

Упрощённая версия оригинальной «Капри» под Android.

## Что умеет

- Офлайн-распознавание речи (Vosk, русский)
- Команды: громкость, пауза/следующий трек, открытие приложений (YouTube, Telegram, Chrome…), поиск, время
- Простой тёмный интерфейс
- Системный TTS Android

## Важно

Это **не готовый APK**. Это **исходный проект**, из которого можно собрать APK.

Сборка Android-приложений из Python — сложный процесс.  
Самый простой способ для человека без опыта — **собрать через GitHub Actions** (облачный компьютер).

---

## Способ 1. Сборка через GitHub Actions (рекомендуется)

1. Создайте аккаунт на [GitHub.com](https://github.com) (если нет).

2. Создайте **новый репозиторий** (New repository), назовите например `capri-android`.

3. Загрузите в него **все файлы** из этой папки `capri_kivy`  
   (main.py, buildozer.spec, папку data/ с моделью и этот README).

4. В репозитории создайте файл  
   `.github/workflows/build.yml`  
   со следующим содержимым:

```yaml
name: Build APK

on:
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install system dependencies
        run: |
          sudo apt update
          sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev

      - name: Install Buildozer
        run: |
          pip install buildozer cython

      - name: Build with Buildozer
        run: |
          buildozer android debug
        timeout-minutes: 90

      - name: Upload APK
        uses: actions/upload-artifact@v4
        with:
          name: capri-apk
          path: bin/*.apk
```

5. Нажмите **Actions** → **Build APK** → **Run workflow**.

6. Дождитесь окончания (обычно 20–50 минут).  
   В конце появится артефакт `capri-apk` — скачайте ZIP и внутри будет `.apk`.

7. Установите APK на телефон (разрешите установку из неизвестных источников).

> Если сборка упадёт — пришлите лог ошибки, постараюсь подсказать правку.

---

## Способ 2. Сборка на своём компьютере (Linux / WSL)

Нужен Ubuntu 22.04 / 24.04 или WSL2.

```bash
# 1. Системные пакеты
sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool \
  pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake \
  libffi-dev libssl-dev

# 2. Buildozer
pip3 install --user buildozer cython
export PATH=$PATH:~/.local/bin

# 3. Перейти в папку проекта
cd capri_kivy

# 4. Собрать
buildozer android debug
```

Первый запуск скачает Android SDK/NDK (несколько гигабайт) и займёт много времени.  
Готовый APK появится в папке `bin/`.

---

## Возможные проблемы при сборке

| Проблема | Что делать |
|---------|------------|
| Не хватает места / памяти | Собирайте через GitHub Actions |
| Ошибка с vosk / sounddevice | Vosk и sounddevice на Android иногда требуют дополнительных рецептов. Можно временно убрать `sounddevice` из requirements и использовать только кнопочный режим + тестовый ввод |
| APK слишком большой | Модель Vosk весит ~50–80 МБ — это нормально |
| Не слышит микрофон | Проверьте разрешения RECORD_AUDIO в настройках телефона |
| Нет русского голоса | Настройки Android → Язык и ввод → Синтез речи → скачать русский голос |

---

## Структура проекта

```
capri_kivy/
├── main.py              ← основной код + интерфейс
├── buildozer.spec       ← настройки сборки
├── data/
│   └── vosk-model-small-ru-0.22/   ← офлайн-модель распознавания
└── README.md
```

---

## Что дальше

После того как получите рабочий APK, можно:

- Добавить иконку и splash-экран
- Улучшить обработку аудио (более стабильный захват микрофона)
- Добавить больше команд
- Сделать автозапуск / работу в фоне (сложнее)

Если сборка через GitHub Actions прошла успешно — напишите, помогу доработать функционал.
