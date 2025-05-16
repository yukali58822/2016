from config import GROQ_API_KEY
from groq import Groq

# 初始化 Groq 客戶端
client = Groq(api_key=GROQ_API_KEY)


def products_type(_type, date):
    conversation_history = [
        {
            "role": "user",
            "content": f"""你是一位商品分類專家，請幫我將以下商品名稱分類為下列其中之一 :
            
            『食品』『飲料』『交通』『書籍』『寵物』，如果不在這些範圍內就是『其他』。
            請只回覆分類名稱，不要加註解。

            商品名稱：""" + _type,
        }
    ]

    # 與模型進行第一次對話
    chat_completion = client.chat.completions.create(
        messages=conversation_history,
        model="llama3-8b-8192",
    )

    # 獲取回應內容
    response_content = chat_completion.choices[0].message.content

    if (response_content == '食品'):
        if (date[-8] != 0):
            time = int(date[-8:-6])
            if (time < 11):
                response_content = '早餐'
            elif (time < 15):
                response_content = '午餐'
            else:
                response_content = '晚餐'
        else:

            if (int(date[-9]) > 5):
                response_content = '早餐'
            else:
                response_content = '宵夜'

    return response_content

# 查詢單一使用者的所有發票紀錄
# invoices = db.collection('invoice1').where('user_id', '==', user_id).stream()
# for invoice in invoices:
#     print(invoice.to_dict())
