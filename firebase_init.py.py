import os
import json
import tempfile
import firebase_admin
from firebase_admin import credentials

firebase_json = os.environ.get('FIREBASE_CREDENTIALS')

# 建立臨時檔案，系統自動管理路徑與名稱
with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as temp_file:
    temp_file.write(firebase_json)
    temp_file_path = temp_file.name

cred = credentials.Certificate(temp_file_path)
firebase_admin.initialize_app(cred)

# 程式結束後可刪除檔案
# import os
# os.remove(temp_file_path)
