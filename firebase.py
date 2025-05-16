import firebase_admin
from firebase_admin import credentials, firestore
import datetime
import pytz
taipei = pytz.timezone('Asia/Taipei')


# 使用服務賬戶密鑰初始化 Firebase
#cred = credentials.Certificate('firebase_api.json')
#firebase_admin.initialize_app(cred)


def upload_to_firestore(date,company,products,total):
    db = firestore.client()

    doc_ref = db.collection('invoice').document()
    doc_ref.set({
        '發票日期' : date,
        '店家' : company,
        '購買商品' : products,
        '總花費' : total,
    })

    print(f'發票資訊已上傳成功')

