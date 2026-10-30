#!/bin/zsh
cd "$(dirname "$0")" || exit 1
PY=""
for c in python3.13 python3.12 python3.11 python3.10 /opt/homebrew/bin/python3 /usr/local/bin/python3 python3; do
  if command -v "$c" >/dev/null 2>&1; then
    if "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then PY="$c"; break; fi
  fi
done
if [[ -z "$PY" ]]; then
  echo "Cần Python 3.10+."
  if command -v brew >/dev/null 2>&1; then
    read "ans?Cài python@3.12 bằng Homebrew? [y/N] "
    [[ "$ans" == [yY] ]] && brew install python@3.12 && PY="$(brew --prefix)/bin/python3.12"
  else
    echo "Cài từ https://www.python.org/downloads/ rồi chạy lại."
  fi
  [[ -z "$PY" ]] && { read "?Enter để thoát"; exit 1; }
fi
if [[ ! -x .venv/bin/python ]]; then
  echo "Tạo môi trường .venv bằng $PY ..."
  "$PY" -m venv .venv || { read "?Lỗi tạo venv. Enter để thoát"; exit 1; }
fi
STAMP=.venv/.req_stamp
if [[ ! -f $STAMP ]] || ! cmp -s requirements.txt $STAMP; then
  echo "Cài thư viện (lần đầu ~2-5 phút) ..."
  .venv/bin/python -m pip install -U pip -q
  .venv/bin/python -m pip install -r requirements.txt || { read "?Lỗi cài thư viện. Enter để thoát"; exit 1; }
  cp requirements.txt $STAMP
fi
echo "Mở http://127.0.0.1:7860 — đóng cửa sổ này để tắt tool."
.venv/bin/python app.py
