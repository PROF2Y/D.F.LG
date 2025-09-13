from flask import Flask, render_template, send_from_directory
import os

app = Flask(__name__)

# الصفحة الرئيسية
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# صفحة الشراء
@app.route('/checkout')
@app.route('/checkout.html')
def checkout():
    return send_from_directory('.', 'checkout.html')

# صفحة التواصل
@app.route('/contact')
@app.route('/contact.html') 
def contact():
    return send_from_directory('.', 'contact.html')

# صفحة البداية
@app.route('/splash')
@app.route('/splash.html')
def splash():
    return send_from_directory('.', 'splash.html')

# الواجهة الرئيسية
@app.route('/main')
@app.route('/main.html')
def main():
    return send_from_directory('.', 'main.html')

# ملف CSS
@app.route('/style.css')
def style():
    return send_from_directory('.', 'style.css')

# مجلد الصور
@app.route('/images/<filename>')
def images(filename):
    return send_from_directory('صور', filename)

if __name__ == '__main__':
    # للنشر على منصات الاستضافة
    import os
    port = int(os.environ.get('PORT', 5000))
    
    print("🚀 تم تشغيل سيرفر فؤاد للأمن السيبراني!")
    print(f"📱 الموقع متاح على المنفذ: {port}")
    print("⏹️  اضغط Ctrl+C لإيقاف السيرفر")
    
    # تشغيل محلي أم على منصة استضافة
    debug_mode = os.environ.get('FLASK_ENV') != 'production'
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
