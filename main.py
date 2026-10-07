# Copyright (C) 2026 <DaiKaiCheng>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses />.
# -*- coding: utf-8 -*-
import sys
import re
import os
import ctypes
import requests
from PyQt5.QtWidgets import (QApplication, QWidget, QHBoxLayout, QVBoxLayout,
                             QPlainTextEdit, QLabel, QFrame, QTextEdit,
                             QSystemTrayIcon, QMenu, QAction, QStyle)
from PyQt5.QtCore import QTimer, QEvent, pyqtSignal, Qt, QSettings, QThread, QObject
from PyQt5.QtGui import QKeyEvent, QMouseEvent, QIcon, QFont, QFontDatabase
try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False
try:
    from pypinyin import pinyin as _pypinyin, Style as _PyStyle
    PYPINYIN_AVAILABLE = True
except ImportError:
    PYPINYIN_AVAILABLE = False
CJK_RE = re.compile(r'[\u4e00-\u9fff]')
EN_WORD_RE = re.compile(r"^[A-Za-z][A-Za-z'\-]{0,39}$")
# 中文句子结束标记，用于统计句子数量
SENTENCE_END_RE = re.compile(r'[。！？]')
POS_ABBR = {
    'noun': 'n.', 'verb': 'v.', 'adjective': 'adj.', 'adverb': 'adv.',
    'pronoun': 'pron.', 'preposition': 'prep.', 'conjunction': 'conj.',
    'interjection': 'int.', 'determiner': 'det.', 'numeral': 'num.',
    'article': 'art.', 'auxiliary verb': 'aux. v.', 'proper noun': 'n.',
    'abbreviation': 'abbr.',
}
def has_cjk(text):
    return bool(CJK_RE.search(text or ''))
def _clean_def(s):
    return re.sub(r'\s+', ' ', s).strip() if s else ''
def count_chinese_sentences(text: str) -> int:
    """统计中文句子数量，按。！？分割"""
    if not text:
        return 0
    parts = SENTENCE_END_RE.split(text)
    valid = [p for p in parts if p.strip()]
    return len(valid)
def get_pinyin(text):
    text = (text or '').strip()
    if not text or not PYPINYIN_AVAILABLE:
        return ''
    try:
        result = _pypinyin(text, style=_PyStyle.TONE)
        return ' '.join(item[0] for item in result if item and item[0])
    except Exception as e:
        print(f"pypinyin error: {e}")
        return ''
def fetch_english_info(word):
    word = (word or '').strip().lower()
    if not word or not EN_WORD_RE.match(word):
        return None
    info = {'phonetic': '', 'pos': []}
    ok = False
    try:
        resp = requests.get(
            f"https://api.dictionaryapi.dev/api/v2/entries/en/{requests.utils.quote(word)}",
            timeout=8,
        )
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and data:
                entry = data[0]
                ok = True
                phonetic = entry.get('phonetic') or ''
                if not phonetic:
                    for p in (entry.get('phonetics') or []):
                        if p.get('text'):
                            phonetic = p['text']
                            break
                info['phonetic'] = phonetic
                for meaning in (entry.get('meanings') or []):
                    pos = (meaning.get('partOfSpeech') or '').lower().strip()
                    defs = [_clean_def(d.get('definition'))
                            for d in (meaning.get('definitions') or [])[:2]]
                    defs = [d for d in defs if d]
                    if pos:
                        info['pos'].append((pos, defs))
    except Exception as e:
        print(f"fetch_english_info network error: {e}")
    return info if ok else None
def format_english_note(info):
    if not info:
        return ''
    lines = []
    head = []
    if info.get('phonetic'):
        head.append(info['phonetic'])
    if info.get('pos'):
        abbrs, seen = [], set()
        for pos, _defs in info['pos']:
            abbr = POS_ABBR.get(pos, pos)
            if abbr not in seen:
                seen.add(abbr)
                abbrs.append(abbr)
        if abbrs:
            head.append(' '.join(abbrs))
    if head:
        lines.append('  '.join(head))
    for pos, defs in info['pos']:
        if defs:
            lines.append(f"{POS_ABBR.get(pos, pos)} {defs[0][:70]}")
            break
    return '\n'.join(lines)
def build_note(text, skip_pinyin: bool = False):
    """
    :param text: 输入文本
    :param skip_pinyin: 如果True，中文不输出拼音（用于长文3句以上）
    """
    text = (text or '').strip()
    if not text:
        return ''
    if has_cjk(text):
        if skip_pinyin:
            return ''
        py = get_pinyin(text)
        return f"拼音：{py}" if py else ''
    if EN_WORD_RE.match(text):
        info = fetch_english_info(text)
        return format_english_note(info)
    return ''
def translate_text(text):
    word_count = len(text.split())
    first, second = ('mymemory', 'deepl') if word_count > 4 else ('deepl', 'mymemory')
    errors = []
    def try_deepl():
        api_key = os.environ.get('DEEPL_API_KEY')
        if not api_key:
            raise RuntimeError("DeepL API Key 未设置")
        url = os.environ.get('DEEPL_API_URL', 'https://api-free.deepl.com/v2/translate')
        target_lang = 'ZH' if not CJK_RE.search(text) else 'EN'
        headers = {'Authorization': f'DeepL-Auth-Key {api_key.strip()}',
                   'Content-Type': 'application/x-www-form-urlencoded'}
        resp = requests.post(url, data={'text': text, 'target_lang': target_lang},
                             headers=headers, timeout=12)
        resp.raise_for_status()
        result = resp.json()
        if 'translations' in result and result['translations']:
            t = result['translations'][0]
            return t['text'], t.get('detected_source_language', 'auto').lower(), target_lang.lower()
        raise RuntimeError("DeepL 返回无效结果")
    def try_mymemory():
        src, dest = ('zh-CN', 'en') if CJK_RE.search(text) else ('en', 'zh-CN')
        url = f"http://api.mymemory.translated.net/get?q={requests.utils.quote(text)}&langpair={src}|{dest}"
        resp = requests.get(url, timeout=8)
        data = resp.json()
        if data.get('responseStatus') == 200:
            translated = data.get('responseData', {}).get('translatedText')
            if translated:
                return translated, src, dest
        raise RuntimeError("MyMemory 返回空结果或错误")
    for api in (first, second):
        try:
            return (try_deepl() if api == 'deepl' else try_mymemory()) + (api.capitalize(),)
        except Exception as e:
            errors.append(f"{api.capitalize()}: {e}")
    raise RuntimeError(f"所有翻译服务均不可用: {'; '.join(errors)}")
class TranslateThread(QThread):
    finished = pyqtSignal(dict)
    def __init__(self, text):
        super().__init__()
        self.text = text
    def run(self):
        result = {'original': self.text, 'translated': '', 'error': '',
                  'api': '', 'translated_note': '', 'source_note': ''}
        try:
            translated, _, _, api = translate_text(self.text)
            result['translated'] = translated
            result['api'] = api
        except Exception as e:
            result['error'] = str(e)
            self.finished.emit(result)
            return
        # 判断原文句子数量 >=3，跳过原文拼音
        sentence_cnt = count_chinese_sentences(self.text)
        skip_src_pinyin = sentence_cnt >= 3
        # 分开捕获异常，防止一个注释失败导致另一个丢失
        try:
            result['source_note'] = build_note(self.text, skip_pinyin=skip_src_pinyin)
        except Exception as e:
            print(f"source note build err: {e}")
            result['source_note'] = ''
        try:
            result['translated_note'] = build_note(translated)
        except Exception as e:
            print(f"translated note build err: {e}")
            result['translated_note'] = ''
        self.finished.emit(result)
NOTE_STYLE = "QLabel { color: #3a3a3a; font-size: 11px; padding: 4px 8px; background-color: rgba(255, 255, 255, 0.55); border-radius: 8px; }"
NOTE_STYLE_EMPTY = "QLabel { background-color: transparent; }"
HELP_TEXT = """快捷键（标准模式）：
回车      进入输入模式
h         显示此帮助
x         复制译文并清空
v         复制译文
p         粘贴剪贴板到输入框
y         复制输入内容
u         循环翻译（用译文再译）
e+a       输入模式（追加）
e+g       输入模式（开头编辑）
e+e       清空并输入
1～8      移动窗口至屏幕边缘（顺序转一圈）
9         移动窗口至屏幕中心
0         切换鼠标拖动（可拖动/锁定）
Esc       关闭窗口
输入模式：
回车      翻译并返回
Shift+回车 换行
Esc       返回标准模式（不翻译）
说明：
· 英文框下方显示音标 / 词性(n. v.)
· 中文框下方显示拼音（需安装 pypinyin；3句及以上长文不显示拼音）"""
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.mode = 'standard'
        self.translated_text = ""
        self.source_text = ""
        self._acrylic_applied = False
        self.draggable = False
        self.dragging = False
        self.drag_pos = None
        self.setWindowTitle("Translator")
        self.setFixedSize(420, 560)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.StrongFocus)
        self.settings = QSettings('TranslatorApp', 'Translator')
        pos = self.settings.value('window/pos')
        if pos is not None:
            self.move(pos)
        else:
            screen = QApplication.primaryScreen().availableGeometry()
            self.move((screen.width() - self.width()) // 2,
                      (screen.height() - self.height()) // 2)
        self.setStyleSheet("""
            QWidget#MainWindow { background-color: rgba(248, 249, 250, 0.8); border-radius: 16px; }
            QPlainTextEdit { background-color: rgba(255, 255, 255, 0.6); border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 10px; font-size: 14px; padding: 8px; selection-background-color: #0078D4; color: #000000; }
            QPlainTextEdit:focus { border: 2px solid #0078D4; background-color: rgba(255, 255, 255, 0.85); }
            QPlainTextEdit[readOnly="true"] { background-color: rgba(240, 240, 240, 0.4); color: #1c1c1c; }
        """)
        self.setObjectName("MainWindow")
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(6)
        content = QHBoxLayout()
        content.setSpacing(10)
        self.input_edit = QPlainTextEdit()
        self.input_edit.setPlaceholderText("输入...")
        self.input_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.input_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.input_edit.setFixedWidth(130)
        self.input_edit.setFocusPolicy(Qt.NoFocus)
        self.input_edit.installEventFilter(self)
        content.addWidget(self.input_edit)
        right = QVBoxLayout()
        right.setSpacing(8)
        self.translated_edit = self._create_readonly_edit("译文", 200)
        right.addWidget(self.translated_edit)
        self.translated_note = self._create_note_label()
        right.addWidget(self.translated_note)
        self.source_edit = self._create_readonly_edit("原文", 170)
        right.addWidget(self.source_edit)
        self.source_note = self._create_note_label()
        right.addWidget(self.source_note)
        content.addLayout(right)
        root.addLayout(content)
        bottom = QHBoxLayout()
        bottom.setSpacing(8)
        self.api_label = QLabel("")
        self.api_label.setStyleSheet("color: #00CED1; font-size: 10px; font-weight: normal;")
        self.api_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        bottom.addWidget(self.api_label)
        bottom.addStretch(1)
        self.status_label = QLabel("标准")
        self.status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.status_label.setStyleSheet("color: #0078D4; font-weight: bold; font-size: 11px;")
        bottom.addWidget(self.status_label)
        root.addLayout(bottom)
        self.e_timer = QTimer()
        self.e_timer.setSingleShot(True)
        self.e_timer.timeout.connect(self._cancel_e_pending)
        self.help_overlay = QFrame(self)
        self.help_overlay.setGeometry(0, 0, self.width(), self.height())
        self.help_overlay.setStyleSheet("""
            QFrame { background-color: rgba(0, 0, 0, 0.6); border-radius: 16px; }
            QTextEdit { background-color: rgba(255, 255, 255, 0.95); border: 2px solid #0078D4;
                border-radius: 12px; font-size: 13px; padding: 16px; color: #1c1c1c; }
        """)
        self.help_overlay.hide()
        help_text_edit = QTextEdit(self.help_overlay)
        help_text_edit.setReadOnly(True)
        help_text_edit.setPlainText(HELP_TEXT)
        help_text_edit.setFrameShape(QTextEdit.NoFrame)
        layout = QVBoxLayout(self.help_overlay)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.addWidget(help_text_edit)
        self.help_text_edit = help_text_edit
        self.help_overlay.installEventFilter(self)
        self.hide()
    def _create_readonly_edit(self, placeholder, height):
        edit = QPlainTextEdit()
        edit.setReadOnly(True)
        edit.setPlaceholderText(placeholder)
        edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        edit.setFixedHeight(height)
        return edit
    def _create_note_label(self):
        label = QLabel("")
        label.setFixedHeight(54)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        label.setStyleSheet(NOTE_STYLE_EMPTY)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        return label
    # ---------- 注释标签 ----------
    def _set_note(self, label, text):
        if text:
            label.setText(text)
            label.setStyleSheet(NOTE_STYLE)
        else:
            label.setText("")
            label.setStyleSheet(NOTE_STYLE_EMPTY)
    def _clear_notes(self):
        self._set_note(self.translated_note, "")
        self._set_note(self.source_note, "")
    # ---------- Win11 亚克力毛玻璃 ----------
    def apply_win11_acrylic(self):
        if self._acrylic_applied:
            return
        try:
            hwnd = int(self.winId())
            if hwnd == 0:
                return
            dwmapi = ctypes.windll.dwmapi
            DWMWA_WINDOW_CORNER_PREFERENCE = 33
            DWMWA_SYSTEMBACKDROP_TYPE = 38
            DWMSBT_ACRYLIC = 3
            DWMWCP_ROUND = 2
            dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_WINDOW_CORNER_PREFERENCE,
                                         ctypes.byref(ctypes.c_int(DWMWCP_ROUND)),
                                         ctypes.sizeof(ctypes.c_int))
            dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_SYSTEMBACKDROP_TYPE,
                                         ctypes.byref(ctypes.c_int(DWMSBT_ACRYLIC)),
                                         ctypes.sizeof(ctypes.c_int))
            self._acrylic_applied = True
        except Exception:
            pass
    def showEvent(self, event):
        self.apply_win11_acrylic()
        pos = self.settings.value('window/pos')
        if pos is not None:
            screen_geo = QApplication.primaryScreen().availableGeometry()
            if not screen_geo.contains(self.frameGeometry()):
                self.move((screen_geo.width() - self.width()) // 2,
                          (screen_geo.height() - self.height()) // 2)
            else:
                self.move(pos)
        super().showEvent(event)
    def hideEvent(self, event):
        self.settings.setValue('window/pos', self.pos())
        super().hideEvent(event)
    def closeEvent(self, event):
        self.hide()
        event.ignore()
    def force_activate(self):
        """修复快捷键呼出焦点丢失，方案A：Windows原生SetForegroundWindow + 加长延时"""
        self.show()
        self.raise_()
        hwnd = int(self.winId())
        try:
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception:
            pass
        def _post_activate():
            self.activateWindow()
            self.setFocus()
        QTimer.singleShot(80, _post_activate)
    # ---------- 事件处理 ----------
    def keyPressEvent(self, event: QKeyEvent):
        if self.mode == 'standard':
            self._handle_standard_key(event)
        elif self.mode == 'help':
            self._handle_help_key(event)
        elif self.mode == 'e-pending':
            self._handle_e_pending_key(event)
        else:
            super().keyPressEvent(event)
    def _handle_standard_key(self, event):
        key = event.key()
        if Qt.Key_1 <= key <= Qt.Key_9:
            self._move_window_to_position(key - Qt.Key_1 + 1)
            return
        if key == Qt.Key_0:
            self._toggle_draggable()
            return
        if key in (Qt.Key_Return, Qt.Key_Enter):
            self._enter_editing_mode()
            return
        if key == Qt.Key_Escape:
            self.hide()
            return
        if Qt.Key_A <= key <= Qt.Key_Z:
            ch = event.text().lower()
            if ch == 'h':
                self._show_help()
            elif ch == 'x':
                self._copy_translated_and_clear()
            elif ch == 'v':
                self._copy_translated()
            elif ch == 'p':
                self._paste_to_input()
            elif ch == 'y':
                self._copy_input_to_clipboard()
            elif ch == 'u':
                self._translate_again()
            elif ch == 'e':
                self.mode = 'e-pending'
                self.status_label.setText("e-等待")
                self.e_timer.start(1000)
    def _handle_help_key(self, event):
        if event.key() == Qt.Key_Escape:
            self._close_help()
    def _handle_e_pending_key(self, event):
        self.e_timer.stop()
        ch = event.text().lower()
        if ch == 'a':
            self._enter_editing_mode(append=True)
        elif ch == 'g':
            self._enter_editing_mode(front=True)
        elif ch == 'e':
            self.input_edit.clear()
            self._enter_editing_mode()
        else:
            self.mode = 'standard'
            self.status_label.setText("标准")
            self.status_label.setStyleSheet("color: #0078D4; font-weight: bold; font-size: 11px;")
            self.api_label.setText("")
    def _cancel_e_pending(self):
        self.mode = 'standard'
        self.status_label.setText("标准")
        self.status_label.setStyleSheet("color: #0078D4; font-weight: bold; font-size: 11px;")
        self.api_label.setText("")
    def _enter_editing_mode(self, append=False, front=False):
        self.input_edit.setFocusPolicy(Qt.StrongFocus)
        self.input_edit.setFocus()
        if append:
            cursor = self.input_edit.textCursor()
            cursor.movePosition(cursor.End)
            self.input_edit.setTextCursor(cursor)
        elif front:
            cursor = self.input_edit.textCursor()
            cursor.movePosition(cursor.Start)
            self.input_edit.setTextCursor(cursor)
        self.mode = 'editing'
        self.status_label.setText("输入中...")
        self.status_label.setStyleSheet("color: #E97451; font-weight: bold; font-size: 11px;")
        self.api_label.setText("")
    def _exit_editing_mode(self):
        self.input_edit.clearFocus()
        self.input_edit.setFocusPolicy(Qt.NoFocus)
        self.mode = 'standard'
        self.status_label.setText("标准")
        self.status_label.setStyleSheet("color: #0078D4; font-weight: bold; font-size: 11px;")
        self.setFocus()
    # ---------- 翻译 ----------
    def _perform_translation(self):
        text = self.input_edit.toPlainText().strip()
        if not text:
            return
        self.status_label.setText("翻译中...")
        self.status_label.setStyleSheet("color: #FFA500; font-size: 11px;")
        self.api_label.setText("")
        self._clear_notes()
        self.thread = TranslateThread(text)
        self.thread.finished.connect(self._on_translation_done)
        self.thread.start()
    def _on_translation_done(self, result):
        if result.get('error'):
            self.translated_edit.setPlainText(f"错误: {result['error']}")
            self.api_label.setText("(Error)")
            self.api_label.setStyleSheet("color: #FF6347; font-size: 10px; font-weight: normal;")
            self._clear_notes()
        else:
            translated = result.get('translated', '')
            original = result.get('original', '')
            self.translated_edit.setPlainText(translated)
            self.source_edit.setPlainText(original)
            self.translated_text = translated
            self.source_text = original
            self._set_note(self.translated_note, result.get('translated_note', ''))
            self._set_note(self.source_note, result.get('source_note', ''))
            api = result.get('api', '')
            if api:
                self.api_label.setText(f"({api})")
                self.api_label.setStyleSheet("color: #00CED1; font-size: 10px; font-weight: normal;")
            else:
                self.api_label.setText("")
        self._exit_editing_mode()
    # ---------- 复制 / 粘贴 ----------
    def _copy_translated_and_clear(self):
        QApplication.clipboard().setText(self.translated_edit.toPlainText())
        self.input_edit.clear()
        self.translated_edit.clear()
        self.source_edit.clear()
        self.translated_text = ""
        self.source_text = ""
        self.api_label.setText("")
        self._clear_notes()
        self._show_temporary_status("已复制译文并清空", "#28a745")
    def _copy_translated(self):
        QApplication.clipboard().setText(self.translated_edit.toPlainText())
        self._show_temporary_status("已复制译文", "#28a745")
    def _paste_to_input(self):
        self.input_edit.setPlainText(QApplication.clipboard().text())
        self._show_temporary_status("已粘贴剪贴板到输入框", "#28a745")
    def _copy_input_to_clipboard(self):
        QApplication.clipboard().setText(self.input_edit.toPlainText())
        self._show_temporary_status("已复制待译文", "#28a745")
    def _translate_again(self):
        text = self.translated_edit.toPlainText()
        if text:
            self.input_edit.setPlainText(text)
            self._perform_translation()
    def _show_temporary_status(self, text, color):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 11px;")
        QTimer.singleShot(1500, self._restore_status)
    def _restore_status(self):
        if self.mode == 'standard':
            self.status_label.setText("标准")
            self.status_label.setStyleSheet("color: #0078D4; font-weight: bold; font-size: 11px;")
    # ---------- 帮助覆盖层 ----------
    def _show_help(self):
        self.mode = 'help'
        self.help_overlay.show()
        self.help_overlay.setFocus()
        self.status_label.setText("帮助")
        self.api_label.setText("")
    def _close_help(self):
        self.mode = 'standard'
        self.help_overlay.hide()
        self.status_label.setText("标准")
        self.status_label.setStyleSheet("color: #0078D4; font-weight: bold; font-size: 11px;")
        self.api_label.setText("")
        self.setFocus()
    # ---------- 窗口位置 ----------
    def _move_window_to_position(self, idx):
        screen = QApplication.primaryScreen().availableGeometry()
        w, h = self.width(), self.height()
        positions = {
            1: (0, 0),
            2: ((screen.width() - w) // 2, 0),
            3: (screen.width() - w, 0),
            4: (0, (screen.height() - h) // 2),
            5: (screen.width() - w, (screen.height() - h) // 2),
            6: (0, screen.height() - h),
            7: ((screen.width() - w) // 2, screen.height() - h),
            8: (screen.width() - w, screen.height() - h),
            9: ((screen.width() - w) // 2, (screen.height() - h) // 2),
        }
        if idx in positions:
            self.move(positions[idx][0], positions[idx][1])
    # ---------- 鼠标拖动 ----------
    def _toggle_draggable(self):
        self.draggable = not self.draggable
        if self.draggable:
            self.status_label.setText("可拖动")
            self.status_label.setStyleSheet("color: #28a745; font-weight: bold; font-size: 11px;")
        else:
            self.status_label.setText("标准")
            self.status_label.setStyleSheet("color: #0078D4; font-weight: bold; font-size: 11px;")
        self.api_label.setText("")
    def mousePressEvent(self, event):
        if self.draggable and event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            self.grabMouse()
            event.accept()
        else:
            super().mousePressEvent(event)
    def mouseMoveEvent(self, event: QMouseEvent):
        if self.dragging and self.draggable:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.dragging:
            self.dragging = False
            self.releaseMouse()
            event.accept()
        else:
            super().mouseReleaseEvent(event)
    # ---------- 事件过滤器 ----------
    def eventFilter(self, obj, event):
        if hasattr(self, 'help_overlay') and obj == self.help_overlay and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Escape:
                self._close_help()
                return True
        if obj == self.input_edit and self.mode == 'editing' and event.type() == QEvent.KeyPress:
            key = event.key()
            mod = event.modifiers()
            if key in (Qt.Key_Return, Qt.Key_Enter):
                if mod & Qt.ShiftModifier:
                    return False
                self._perform_translation()
                return True
            elif key == Qt.Key_Escape:
                self._exit_editing_mode()
                return True
        return super().eventFilter(obj, event)
# ==========================================================================
#                            命令行模式
# ==========================================================================
def run_cli():
    if len(sys.argv) > 1:
        text = ' '.join(sys.argv[1:])
        try:
            translated, _, _, api = translate_text(text)
            print(f"[{api}] {translated}")
            note = build_note(translated)
            if note:
                print(note)
        except Exception as e:
            print(f"翻译失败: {e}", file=sys.stderr)
            sys.exit(1)
        sys.exit(0)
window = None
class SignalRelay(QObject):
    toggle_signal = pyqtSignal()
def main(nerd_font="0xProto Nerd Font"):
    global window
    run_cli()
    app = QApplication(sys.argv)
    font_family = nerd_font
    available = QFontDatabase().families()
    if font_family in available:
        app.setFont(QFont(font_family))
        print(f"[字体] 已应用 {font_family}")
    else:
        print(f"[字体] {font_family} 未找到，使用系统默认字体")
    if not PYPINYIN_AVAILABLE:
        print("[拼音] 未安装 pypinyin，中文拼音不可用。安装：pip install pypinyin")
    window = MainWindow()
    app.main_window = window
    app.setQuitOnLastWindowClosed(False)
    def toggle():
        if window.isVisible():
            window.hide()
        else:
            window.force_activate()
    tray = QSystemTrayIcon()
    tray.setIcon(QIcon.fromTheme("accessories-text-editor",
                                 QApplication.style().standardIcon(QStyle.SP_ComputerIcon)))
    tray.setToolTip("Translator")
    tray_menu = QMenu()
    show_action = QAction("显示窗口", tray_menu)
    show_action.triggered.connect(toggle)
    quit_action = QAction("退出", tray_menu)
    quit_action.triggered.connect(app.quit)
    tray_menu.addAction(show_action)
    tray_menu.addSeparator()
    tray_menu.addAction(quit_action)
    tray.setContextMenu(tray_menu)
    def tray_activated(reason):
        if reason == QSystemTrayIcon.Trigger:
            toggle()
    tray.activated.connect(tray_activated)
    tray.show()
    relay = SignalRelay()
    relay.toggle_signal.connect(toggle)
    def hotkey_callback():
        relay.toggle_signal.emit()
    if KEYBOARD_AVAILABLE:
        keyboard.add_hotkey('ctrl+alt+p', hotkey_callback)
        app.aboutToQuit.connect(lambda: keyboard.unhook_all())
    else:
        print("热键库未安装，请使用托盘图标切换窗口。")
    def on_exit():
        if KEYBOARD_AVAILABLE:
            keyboard.unhook_all()
        tray.hide()
    app.aboutToQuit.connect(on_exit)
    sys.exit(app.exec_())
if __name__ == '__main__':
    main()
