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

# مجلد الصور - تجربة عدة مسارات
@app.route('/images/<filename>')
def images(filename):
    import os
    
    # جرب المسارات المحتملة
    possible_paths = ['صور', 'images', 'Images', 'صور', './صور', './images']
    
    for path in possible_paths:
        if os.path.exists(path) and os.path.isdir(path):
            file_path = os.path.join(path, filename)
            if os.path.exists(file_path):
                return send_from_directory(path, filename)
    
    # إذا لم توجد، أرجع خطأ مع تفاصيل
    current_dir = os.getcwd()
    dirs = [d for d in os.listdir('.') if os.path.isdir(d)]
    return f"Image not found! Current dir: {current_dir}, Available dirs: {dirs}", 404

# route للتشخيص
@app.route('/debug')
def debug():
    import os
    current_dir = os.getcwd()
    all_items = os.listdir('.')
    dirs = [d for d in all_items if os.path.isdir(d)]
    files = [f for f in all_items if os.path.isfile(f)]
    
    html = f"""
    <h2>Debug Info</h2>
    <p><b>Current Directory:</b> {current_dir}</p>
    <p><b>Directories:</b> {dirs}</p>
    <p><b>Files:</b> {files}</p>
    """
    
    # فحص محتويات كل مجلد
    for d in dirs:
        try:
            contents = os.listdir(d)
            html += f"<p><b>Contents of '{d}':</b> {contents}</p>"
        except:
            html += f"<p><b>Cannot read '{d}'</b></p>"
    
    return html

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
