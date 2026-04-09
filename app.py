import flet as ft
import pyperclip
import threading
import time
import re
import jaconv

def main(page: ft.Page):
    # --- ページ設定 ---
    page.title = "モジ・サッパリ Pro"
    page.window_width = 450
    page.window_height = 700
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 25

    # --- 状態管理 ---
    is_running = False
    accumulated_text = ""
    text_lock = threading.Lock() # スレッド間のデータ競合を防ぐためのロックを導入

    # --- 整形ロジック (変更なし) ---
    def process_text(text):
        if not text: return ""
        if sw_pdf.value:
            text = text.replace('\r\n', '\n').replace('\r', '\n').replace('\n', ' ')
            text = re.sub(r'[ \t]+', ' ', text)
        if sw_zenhan.value:
            text = jaconv.z2h(text, kana=False, ascii=True, digit=True)
        if sw_space.value:
            text = text.replace(" ", "").replace("　", "").replace("\t", "")
        if sw_quote.value:
            text = "\n".join([f"> {line}" for line in text.split('\n') if line.strip()])
        return text.strip()

    # --- 監視スレッド ---
    def monitor_clipboard():
        nonlocal is_running, accumulated_text
        try:
            recent_value = pyperclip.paste()
        except Exception:
            recent_value = ""

        while is_running:
            try:
                current_value = pyperclip.paste()
                if current_value != recent_value and current_value != "":
                    processed = process_text(current_value)
                    
                    if sw_stack.value:
                        # 複数スレッドからアクセスされる変数をロックして安全に更新
                        with text_lock:
                            accumulated_text = (accumulated_text + "\n" + processed).strip()
                            current_len = len(accumulated_text)
                        pyperclip.copy(accumulated_text)
                        log_text.value = f"📦 蓄積中: {current_len}文字"
                    else:
                        pyperclip.copy(processed)
                        log_text.value = f"✅ 整形完了: {time.strftime('%H:%M:%S')}"
                    
                    recent_value = pyperclip.paste()
                    page.update()
                    
            # 具体的なエラーを捕捉してUIに通知
            except pyperclip.PyperclipException:
                log_text.value = "⚠️ クリップボードアクセス拒否"
                page.update()
            except Exception as e:
                log_text.value = f"⚠️ エラー: {str(e)[:15]}..."
                page.update()
                time.sleep(1) # エラーの無限ループを防ぐための待機
            
            # クロスプラットフォーム対応のためポーリングを採用
            time.sleep(0.5) 

    # --- ハンドラ ---
    def toggle_master(e):
        nonlocal is_running
        is_running = e.control.value
        if is_running:
            status_label.value = "⚡ 監視中"
            status_label.color = "blue"
            threading.Thread(target=monitor_clipboard, daemon=True).start()
        else:
            status_label.value = "💤 停止中"
            status_label.color = "red"
        page.update()

    def check_accumulation(e):
        # 読み込み時もロックをかけて安全性を担保
        with text_lock:
            preview = accumulated_text if accumulated_text else "空っぽです"
        dlg = ft.AlertDialog(
            title=ft.Text("蓄積内容"),
            content=ft.Text(preview, size=12),
            actions=[ft.TextButton("閉じる", on_click=lambda _: page.close(dlg))]
        )
        page.open(dlg)

    def reset_accumulation(e):
        nonlocal accumulated_text
        # 書き込み時のロック
        with text_lock:
            accumulated_text = ""
        pyperclip.copy("")
        log_text.value = "♻️ リセット完了"
        page.update()

    # --- UI部品構築  ---
    header = ft.Text("モジ・サッパリ Pro", size=30, weight="bold")
    sw_pdf    = ft.Switch(label="PDF改行連結", value=True)
    sw_zenhan = ft.Switch(label="英数半角化", value=False)
    sw_space  = ft.Switch(label="空白全削除", value=False)
    sw_quote  = ft.Switch(label="引用(>)付与", value=False)
    sw_stack  = ft.Switch(label="蓄積モード", value=False)
    status_label = ft.Text("💤 停止中", color="red", weight="bold")
    log_text = ft.Text("開始してください", size=12)

    page.add(
        header, ft.Text("コピーを自動整形します"), ft.Divider(),
        sw_pdf, sw_zenhan, sw_space, sw_quote, ft.Divider(),
        sw_stack,
        ft.Row([ft.ElevatedButton("内容確認", on_click=check_accumulation),
                ft.ElevatedButton("リセット", on_click=reset_accumulation)], alignment="center"),
        ft.Divider(),
        ft.Row([ft.CupertinoSwitch(on_change=toggle_master)], alignment="center"),
        ft.Row([status_label], alignment="center"),
        ft.Row([log_text], alignment="center"),
    )

if __name__ == "__main__":
    ft.app(target=main)