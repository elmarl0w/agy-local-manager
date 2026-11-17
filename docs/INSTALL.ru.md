# Установка и эксплуатация

## Предварительная проверка

Система: Arch Linux / EndeavourOS / производные с `paru`, Linux x86_64. Не устанавливайте с `sudo ./install.sh`.

```bash
uname -m
command -v agy
pacman -Q antigravity-cli
node --version
npm --version
python3 --version
curl -fsS http://127.0.0.1:11434/api/version
ollama list
```

Если последняя команда не отвечает, запустите Ollama (`sudo systemctl start ollama`) и проверьте её журнал. Минимум Node.js 18. Убедитесь, что скачана совместимая GGUF-модель.

## Установка

Скачайте репозиторий, прочитайте `install.sh`, выполните `./install.sh`, откройте новый терминал и убедитесь, что:

```bash
command -v agy
# ожидается /home/<user>/.local/bin/agy
agy doctor
```

Если `command -v agy` выдаёт `/usr/bin/agy`, ваш PATH ставит системный путь раньше пользовательского. Добавьте в начало `~/.zshrc`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Выполните `exec zsh` и повторите проверку.

## Настройка Gemma

`agy setup-model` запускает мастер адаптера; `agy models list` показывает добавленные модели. Не путайте Ollama ID (`f6dc...`) с именем модели: используйте точное имя из `ollama list`. Если модель добавлена ранее, конфигурация хранится вне менеджера и должна сохраниться.

## Ежедневное использование

```bash
cd ~/some-project
agy
```

`agy doctor` полезен после обновлений через `paru -Syu`. Для восстановления `agy repair`; команда завершится ошибкой, если экспериментальный бинарник используется другим процессом.

## Как выглядит успешный результат

Проверьте не только текстовый ответ агента, но и файл через `cat`. Если `Read` показывает `additional properties 'AbsolutePath'`, значит, вы запустили глобальный адаптер, а не исправленную копию, или он обновился. Выполните `agy doctor`, затем `agy repair`.

## Зависимости и версии

- Системный `agy`: ставится отдельно из AUR, не хранится в Git.
- `free-antigravity-cli@1.1.5`: устанавливается из npm в `~/.local/share/agy-local-manager/npm`.
- Python-патчер: скачивается в `~/.local/share/agy-local-manager/eligibility-patcher` с GitHub; обновление только вручную.
- Ollama и модель: отдельно, менеджер не скачивает многогигабайтные веса.

Не редактируйте систему через `sudo npm install -g` для этого проекта: изолированная установка управляется менеджером.
