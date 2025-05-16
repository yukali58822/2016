from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, auth, firestore
import re
from datetime import datetime
from flask_cors import CORS
from config import GROQ_API_KEY
from groq import Groq
from playwright.sync_api import Playwright, sync_playwright
import ddddocr
import sys
import contextlib
import uuid
import os
import time
import pytz
from openpyxl import Workbook

from pythonProject.Python應用.backend.測試 import products_type
from 語音驗證碼 import *

app = Flask(__name__)
CORS(app)  # 啟用跨域支援，否則 Flutter Web 會被擋

# 初始化 Firebase
cred = credentials.Certificate('firebase_api.json')
firebase_admin.initialize_app(cred)
taipei = pytz.timezone('Asia/Taipei')
db = firestore.client()

# 密碼長度驗證
def is_valid_password(password):
    return len(password) >= 6

# Email 格式驗證
def is_valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

@app.route('/record_transaction', methods=['POST'])
def record_transaction():
    try:
        data = request.get_json()
        print("Received data:", data)

        required_fields = ['類型', '日期', '類別', '金額', '備註', 'user_id']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"缺少必要欄位: {field}"}), 400

        if not isinstance(data['金額'], (int, float)):
            return jsonify({"error": "金額必須是數字"}), 400

        type_ = data.get('類型')  # 收入 或 支出
        date = data.get('日期')  # 日期（字串格式，如 2025-04-29）
        category = data.get('類別')
        amount = float(data.get('金額'))
        note = data.get('備註')
        user_id = data.get('user_id')


        # 寫入 Firestore
        doc_ref = db.collection('transactions').document()
        doc_ref.set({
            '類型': type_,
            '日期': date,
            '類別': category,
            '金額': amount,
            '備註': note,
            'user_id': user_id,
        })

        return jsonify({'message': '資料儲存成功'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    confirm_password = data.get('confirm_password')

    if not all([name, email, password, confirm_password]):
        return jsonify({'error': '所有欄位皆為必填'}), 400

    if not is_valid_email(email):
        return jsonify({'error': '電子郵件格式錯誤'}), 400

    if password != confirm_password:
        return jsonify({'error': '密碼與確認密碼不一致'}), 400

    if not is_valid_password(password):
        return jsonify({'error': '密碼長度至少需 6 碼'}), 400

    try:
        user = auth.create_user(email=email, password=password)
        uid = user.uid
    except auth.EmailAlreadyExistsError:
        try:
            user = auth.get_user_by_email(email)
            uid = user.uid
        except Exception as e:
            return jsonify({'error': f'無法取得現有帳號資訊: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'註冊時發生錯誤: {str(e)}'}), 500

    try:
        db.collection('users').document(uid).set({
            'name': name,
            'email': email,
            'created_at': datetime.utcnow().isoformat(),
            'user_id': uid
        })
        return jsonify({'message': '註冊成功'}), 200
    except Exception as e:
        return jsonify({'error': f'Firestore 寫入失敗: {str(e)}'}), 500

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({'message': '請填寫所有欄位'}), 400

    try:
        user = auth.get_user_by_email(email)
    except auth.UserNotFoundError:
        return jsonify({'message': '帳號不存在'}), 400
    except Exception as e:
        return jsonify({'message': f'發生錯誤: {str(e)}'}), 500

    return jsonify({'message': '登入成功'}), 200

@app.route('/update_user', methods=['POST'])
def update_user():
    try:
        data = request.json
        uid = data.get('uid')
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')

        auth.update_user(uid, email=email, password=password)
        db.collection('users').document(uid).update({'name': name, 'email': email})

        return jsonify({'message': '使用者資料已更新'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/delete_user', methods=['POST'])
def delete_user():
    try:
        data = request.json
        uid = data.get('uid')

        if not uid:
            return jsonify({'error': '缺少 uid'}), 400

        try:
            auth.delete_user(uid)
        except Exception as e:
            print(f"[警告] 無法刪除 FirebaseAuth 帳戶：{e}")

        try:
            db.collection('users').document(uid).delete()
        except Exception as e:
            print(f"[警告] 無法刪除 Firestore 資料：{e}")

        return jsonify({'message': '使用者帳戶已刪除'}), 200
    except Exception as e:
        print(f"[錯誤] 刪除帳戶失敗: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/save_financial_goal', methods=['POST'])
def save_financial_goal():
    try:
        data = request.get_json()
        print("Received financial goal data:", data)

        required_fields = ['user_id', '日期', '類別', '金額', '時間', '類型']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"缺少必要欄位: {field}"}), 400

        if not isinstance(data['金額'], (int, float)):
            return jsonify({"error": "金額必須是數字"}), 400

        user_id = data.get('user_id')
        date = data.get('日期')
        category = data.get('類別')
        amount = float(data.get('金額'))
        time = data.get('時間')
        type_ = data.get('類型')

        doc_ref = db.collection('financial').document()
        doc_ref.set({
            'user_id': user_id,
            '日期': date,
            '類別': category,
            '金額': amount,
            '時間': time,
            '類型': type_,
        })

        return jsonify({'message': '財務目標儲存成功'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/get_financial_goals', methods=['POST'])
def get_financial_goals():
    try:
        data = request.get_json()
        print("Received get_financial_goals request:", data)
        user_id = data.get('user_id')

        if not user_id:
            print("缺少 user_id，拒絕請求")
            return jsonify({"error": "缺少 user_id"}), 400

        goals_ref = db.collection('financial').where('user_id', '==', user_id).get()
        goals = []
        for goal in goals_ref:
            goal_data = goal.to_dict()
            goal_data['id'] = goal.id
            goals.append(goal_data)

        return jsonify({'goals': goals}), 200

    except Exception as e:
        print(f"獲取目標失敗: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/delete_financial_goal', methods=['POST'])
def delete_financial_goal():
    try:
        data = request.get_json()
        print("Received delete_financial_goal request:", data)
        goal_id = data.get('goal_id')

        if not goal_id:
            print("缺少 goal_id，拒絕請求")
            return jsonify({"error": "缺少 goal_id"}), 400

        db.collection('financial').document(goal_id).delete()
        return jsonify({'message': '目標已刪除'}), 200

    except Exception as e:
        print(f"刪除目標失敗: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/clear_all_expense_goals', methods=['POST'])
def clear_all_expense_goals():
    try:
        data = request.get_json()
        print("Received clear_all_expense_goals request:", data)
        user_id = data.get('user_id')

        if not user_id:
            print("缺少 user_id，拒絕請求")
            return jsonify({"error": "缺少 user_id"}), 400

        # 首先獲取所有文檔以檢查數據
        all_docs = db.collection('financial').where(field_path='user_id', op_string='==', value=user_id).get()
        print(f"找到的所有文檔: {[doc.to_dict() for doc in all_docs]}")

        # 嘗試查詢類型為支出的文檔
        goals_ref = (db.collection('financial')
                     .where(field_path='user_id', op_string='==', value=user_id)
                     .where(field_path='類型', op_string='==', value='支出')
                     .get())
        deleted_count = 0
        for goal in goals_ref:
            print(f"正在刪除支出目標，ID: {goal.id}, 數據: {goal.to_dict()}")
            db.collection('financial').document(goal.id).delete()
            deleted_count += 1

        print(f"所有支出目標已清空，刪除數量: {deleted_count}")
        return jsonify({'message': '所有支出目標已清空'}), 200

    except Exception as e:
        print(f"清空支出目標失敗: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/clear_all_saving_goals', methods=['POST'])
def clear_all_saving_goals():
    try:
        data = request.get_json()
        print("Received clear_all_saving_goals request:", data)
        user_id = data.get('user_id')

        if not user_id:
            print("缺少 user_id，拒絕請求")
            return jsonify({"error": "缺少 user_id"}), 400

        # 首先獲取所有文檔以檢查數據
        all_docs = db.collection('financial').where(field_path='user_id', op_string='==', value=user_id).get()
        print(f"找到的所有文檔: {[doc.to_dict() for doc in all_docs]}")

        # 嘗試查詢類型為儲蓄的文檔
        goals_ref = (db.collection('financial')
                     .where(field_path='user_id', op_string='==', value=user_id)
                     .where(field_path='類型', op_string='==', value='儲蓄')
                     .get())
        deleted_count = 0
        for goal in goals_ref:
            print(f"正在刪除儲蓄目標，ID: {goal.id}, 數據: {goal.to_dict()}")
            db.collection('financial').document(goal.id).delete()
            deleted_count += 1

        print(f"所有儲蓄目標已清空，刪除數量: {deleted_count}")
        return jsonify({'message': '所有儲蓄目標已清空'}), 200

    except Exception as e:
        print(f"清空儲蓄目標失敗: {str(e)}")
        return jsonify({'error': str(e)}), 400

# 初始化 Groq 客戶端
client = Groq(api_key=GROQ_API_KEY)

# 用來記錄對話的列表
conversation_history = []

@app.route('/chat', methods=['POST'])
def chat():
    # 從請求中獲取用戶輸入
    data = request.get_json()  # 獲取 JSON 格式的數據
    user_message = data.get('message')  # 假設傳入的 JSON 結構為 {"message": "問題內容"}
    user_id = data.get('user_id', 'unknown_user')  # 用戶ID，假設從前端傳來

    # 確保消息不是空的
    if not user_message:
        return jsonify({"error": "消息內容不可為空"}), 400

    # 構建對話歷史記錄
    conversation_history = [
        {
            "role": "user",
            "content": "以淺顯易懂的100字內繁體中文" + user_message,
        }
    ]

    # 與模型進行第一次對話
    chat_completion = client.chat.completions.create(
        messages=conversation_history,
        model="llama3-8b-8192",
    )

    # 獲取回應內容
    response_content = chat_completion.choices[0].message.content

    # 將模型的回答添加到對話紀錄
    conversation_history.append({
        "role": "assistant",
        "content": response_content,
    })

    # 第二次與模型對話，要求將上一次的回答轉成中文翻譯
    chat_completion2 = client.chat.completions.create(
        messages=conversation_history + [
            {
                "role": "user",
                "content": f'{response_content} + 用繁體中文回答',
            }
        ],
        model="llama3-8b-8192",
    )

    # 獲取第二次的回應內容
    response_content2 = chat_completion2.choices[0].message.content

    # 將第二次回應添加到對話紀錄
    conversation_history.append({
        "role": "assistant",
        "content": response_content2,
    })

    # 儲存或更新對話紀錄到 Firestore
    user_ref = db.collection('chat').document(user_id)  # 每個用戶有一個獨立的文檔，以 user_id 為識別
    user_ref.set({
        'user_id': user_id,
        'conversation': firestore.ArrayUnion([{
            "timestamp": datetime.now(pytz.timezone('Asia/Taipei')),
            "user_message": user_message,
            "bot_response": response_content2,
        }])
    }, merge=True)  # 使用 merge=True 保證不覆蓋舊的紀錄

    # 返回 JSON 格式的回應
    return jsonify({
        'response': response_content2
    })



@app.route('/process_invoice', methods=['POST'])
def process_invoice():
    try:
        data = request.get_json()  # 接收來自前端的資料
        invoice_number1 = data.get('invoice_number')
        purchase_date1 = data.get('purchase_date')
        random_code1 = data.get('random_code')
        user_id = data.get('user_id', 'unknown_user')
        print(user_id)
        print("發票號碼: "+invoice_number1)

        invoice_detail = []

        uid = str(uuid.uuid4())
        path = uid + "_captcha.png"

        MAX_RETRIES = 20
        RETRY_INTERVAL = 0.0001

        invoice_number = invoice_number1.replace('-','')
        random_code = random_code1
        date_str = purchase_date1
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        full_date_str = date_obj.strftime("%a %b %d %Y")  # e.g., Fri Mar 27 2025

        @contextlib.contextmanager
        def suppress_stdout():
            try:
                original_stdout = sys.stdout
                sys.stdout = open(os.devnull, "w", encoding='utf-8')
                yield
            finally:
                sys.stdout.close()
                sys.stdout = original_stdout

        def solve_captcha_with_ocr(page) -> bool:
            try:
                captcha_image = page.locator('img[alt="圖形驗證碼"]')
                captcha_image.wait_for(state="visible", timeout=5000)

                box = captcha_image.bounding_box()
                if not box:
                    print("無法獲得驗證碼圖片尺寸")
                    return False

                width = box['width']
                height = box['height']
                if abs(width - 150) > 10 or abs(height - 40) > 10:
                    print(f"圖形驗證碼尺寸異常：{width:.0f}x{height:.0f}")
                    return False

                captcha_image.screenshot(path=path)
                print(f"驗證碼圖片擷取成功：{width:.0f}x{height:.0f}，檔名 {path}")
                return True

            except Exception as e:
                print("擷取驗證碼圖片失敗：", e)
                return False

        def out_result() -> str:
            with suppress_stdout():
                ocr = ddddocr.DdddOcr()
            with open(path, "rb") as f:
                img_bytes = f.read()
            result = ocr.classification(img_bytes)
            return result.strip()

        def fill_invoice_info(page):
            page.goto("https://www.einvoice.nat.gov.tw/portal/btc/audit/btc601w/search")

            today = datetime.today()
            year_diff = today.year - date_obj.year
            month_diff = today.month - date_obj.month

            page.get_by_role("textbox", name="發票號碼").click()
            page.get_by_role("textbox", name="發票號碼").fill(invoice_number)

            page.locator("[data-test=\"dp-input\"]").click()

            while month_diff:
                page.get_by_role("button", name="上個月").click()
                month_diff -= 1

            if year_diff != 0:
                page.locator("[data-test=\"year-toggle-overlay-0\"]").click()
                page.get_by_text(f"{date_obj.year}年").click()

            page.locator(f"[data-test=\"{full_date_str} 00\\:00\\:00 GMT\\+0800 \\(台北標準時間\\)\"]").get_by_text(
                f"{date_obj.day}").click()

            page.get_by_role("textbox", name="位隨機碼").click()
            page.get_by_role("textbox", name="位隨機碼").fill(random_code)

        def try_full_process_with_retry(page):
            for attempt in range(MAX_RETRIES):
                print(f"\n[第 {attempt + 1} 次嘗試]")

                try:
                    fill_invoice_info(page)

                    page.get_by_role("textbox", name="圖形驗證碼").click()
                    if not solve_captcha_with_ocr(page):
                        raise ValueError("驗證碼擷取失敗")

                    captcha_result = out_result()
                    if captcha_result.isdigit() and len(captcha_result) == 5:
                        page.get_by_role("textbox", name="圖形驗證碼").fill(captcha_result)
                        print(f"成功輸入驗證碼: {captcha_result}")

                        page.get_by_role("button", name="查詢").click()
                        page.wait_for_selector("table", timeout=5000)

                        # 開啟詳細資料
                        page.get_by_role("dialog").locator("div").filter(
                            has_text=re.compile(f"^{invoice_number}$")).click()

                        rows = page.locator("table tbody tr")
                        for i in range(rows.count()):
                            row = rows.nth(i)
                            cells = row.locator("td")
                            raw_texts = cells.all_inner_texts()
                            clean_texts = [text.strip().replace('\xa0', '') for text in raw_texts]
                            if not any(clean_texts):
                                continue
                            invoice_detail.append(clean_texts)
                            # print(f"第 {i + 1} 列資料：{clean_texts}")
                        return True

                    else:
                        print(f"驗證碼格式錯誤（{captcha_result}），重試中...")
                        time.sleep(RETRY_INTERVAL)
                        page.reload()

                except Exception as e:
                    print("流程中出現錯誤，將重新整理頁面再試一次：", e)
                    time.sleep(RETRY_INTERVAL)
                    page.reload()

            print("\n超過最大重試次數，結束程序")
            return False

        def run(playwright: Playwright) -> None:
            browser = playwright.chromium.launch(
                headless=False,
                args=["--window-position=-2000,0"]
            )
            context = browser.new_context()
            page = context.new_page()

            success = try_full_process_with_retry(page)

            if not success:
                print("無法成功查詢發票資訊。")

            context.close()
            browser.close()
            items = invoice_detail[1:-1]

            total = 0
            products = []
            for item in items:
                total += int(item[3])
                products.append(f"品名:\n{item[0]} \n金額: {item[3]}\n\n")


            date = invoice_detail[0][0]
            company = invoice_detail[0][4]
            total = str(total)


            # 上傳資料庫
            db = firestore.client()

            doc_ref = db.collection('invoice').document()
            doc_ref.set({
                '發票日期': date,
                '店家': company,
                '購買商品': products,
                '總花費': total,
                'user_id': user_id,
            })

            print(f'發票資訊已上傳資料庫')

            _type = products_type(item[0], date)
            dt = datetime.strptime(date, "%Y年%m月%d日 %H:%M:%S")
            date = dt.strftime("%Y-%m-%d")

            for item in items:

                if(int(item[3])<0):
                    # 加到記帳資料庫
                    doc_ref = db.collection('transactions').document()
                    doc_ref.set({
                        '類型': "收入",
                        '日期': date,
                        '類別': '其他',
                        '金額': int(item[3]),
                        '備註': f'{item[0]} 以發票掃描存入',
                        'user_id': user_id,
                    })

                else :
                    # 加到記帳資料庫
                    doc_ref = db.collection('transactions').document()
                    doc_ref.set({
                        '類型': "支出",
                        '日期': date,
                        '類別': _type,
                        '金額': int(item[3]),
                        '備註': f'{item[0]}(發票)',
                        'user_id': user_id,
                    })
                    print('發票已存入記帳資料庫')



        with sync_playwright() as playwright:
            run(playwright)

        # print('回傳給flutter')
        return jsonify({"status": "success", "message": "success"}), 200

    except Exception as e:
        # 捕捉錯誤以利除錯
        print(f"錯誤：{e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get_invoices', methods=['POST'])
def get_invoices():
    try:
        invoices_ref = db.collection('invoice').get()
        invoices = []
        for invoice in invoices_ref:
            invoice_data = invoice.to_dict()
            invoice_data['id'] = invoice.id
            invoices.append(invoice_data)
        return jsonify({'invoices': invoices}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/export_transactions', methods=['POST'])
def export_transactions():
    try:
        data = request.get_json()
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        user_id = data.get('user_id')

        if not all([start_date, end_date, user_id]):
            return jsonify({'error': '缺少 start_date, end_date 或 user_id'}), 400

        # 查詢 Firestore 中的 transactions
        transactions_ref = db.collection('transactions').where('user_id', '==', user_id).get()
        transactions = []
        for transaction in transactions_ref:
            transaction_data = transaction.to_dict()
            transaction_date = datetime.strptime(transaction_data['日期'], '%Y-%m-%d').date()
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            if start_date_obj <= transaction_date <= end_date_obj:
                transactions.append(transaction_data)

        # 創建 Excel 檔案
        wb = Workbook()
        ws = wb.active
        ws.title = "Transactions"
        headers = ['類型', '日期', '類別', '金額', '備註', 'user_id']
        ws.append(headers)

        for transaction in transactions:
            row = [transaction.get(header, '') for header in headers]
            ws.append(row)

        # 儲存 Excel 檔案
        excel_file = f"transactions_{user_id}_{start_date}_to_{end_date}.xlsx"
        wb.save(excel_file)

        # 回傳檔案給前端下載
        with open(excel_file, 'rb') as f:
            response = jsonify({'message': '匯出成功', 'file': excel_file})
            response.headers['Content-Disposition'] = f'attachment; filename={excel_file}'
            response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            return response

    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)