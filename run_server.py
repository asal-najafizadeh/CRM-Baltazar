from waitress import serve
from app import create_app  # اسم فایل اصلی یا فکتوری فلسک شما

app = create_app()

if __name__ == '__main__':
    print("Baltazar CRM is launching on port 5000...")
    # این دستور برنامه را روی پورت 5000 و روی تمام آی‌پی‌های سرور زنده نگه می‌دارد
    serve(app, host='5.57.35.140', port=5000)