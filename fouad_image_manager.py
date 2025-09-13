#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
مدير صور موقع فؤاد للأمن السيبراني
Image Manager for Fouad Cyber Security Store
تطبيق PyQt5 لإدارة وتعديل صور الموقع بطريقة سلسة وذكية
"""

import sys
import os
import json
import subprocess
import threading
import time
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any

# PyQt5 imports
try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QListWidget, QListWidgetItem, QSplitter,
        QTextEdit, QProgressBar, QGroupBox, QGridLayout, QSlider,
        QSpinBox, QComboBox, QCheckBox, QFileDialog, QMessageBox,
        QStatusBar, QTabWidget, QScrollArea, QFrame, QDialog,
        QDialogButtonBox, QFormLayout, QLineEdit, QTreeWidget,
        QTreeWidgetItem, QHeaderView
    )
    from PyQt5.QtCore import (
        Qt, QThread, pyqtSignal, QTimer, QSize, QUrl, QProcess,
        QSettings, QDir, QFileInfo, QMimeData
    )
    from PyQt5.QtGui import (
        QPixmap, QIcon, QFont, QPalette, QColor, QBrush,
        QLinearGradient, QPainter, QDragEnterEvent, QDropEvent
    )
except ImportError:
    print("❌ PyQt5 غير مثبت! يرجى تثبيته بالأمر:")
    print("pip install PyQt5 Pillow requests")
    sys.exit(1)

# PIL imports for image processing
try:
    from PIL import Image, ImageFilter, ImageEnhance, ImageDraw
except ImportError:
    print("❌ Pillow غير مثبت! يرجى تثبيته بالأمر:")
    print("pip install Pillow")
    sys.exit(1)

# Requests for server communication
try:
    import requests
except ImportError:
    print("❌ Requests غير مثبت! يرجى تثبيته بالأمر:")
    print("pip install requests")
    sys.exit(1)


class ServerManager(QThread):
    """مدير الخادم - يدير تشغيل وإيقاف خادم Flask"""
    
    status_changed = pyqtSignal(bool, str)  # (is_running, message)
    server_started = pyqtSignal(bool, str)  # عند محاولة تشغيل الخادم
    
    def __init__(self, project_path: str):
        super().__init__()
        self.project_path = project_path
        self.server_process = None
        self.server_url = "http://localhost:5000"
        self.is_running = False
        self.should_stop = False
        self.start_requested = False
    
    def request_start_server(self):
        """طلب تشغيل الخادم (غير متزامن)"""
        self.start_requested = True
    
    def start_server(self):
        """تشغيل الخادم في thread منفصل"""
        if self.is_running:
            self.server_started.emit(True, "الخادم يعمل بالفعل")
            return
        
        app_py_path = os.path.join(self.project_path, "app.py.py")
        if not os.path.exists(app_py_path):
            self.server_started.emit(False, "ملف app.py.py غير موجود")
            return
        
        try:
            # تشغيل الخادم في عملية منفصلة
            self.server_process = QProcess()
            self.server_process.setWorkingDirectory(self.project_path)
            
            # إعداد متغيرات البيئة
            env = self.server_process.processEnvironment()
            env.insert("PYTHONPATH", self.project_path)
            self.server_process.setProcessEnvironment(env)
            
            # تشغيل الخادم
            python_exe = sys.executable  # استخدام نفس Python المستخدم
            self.server_process.start(python_exe, [app_py_path])
            
            # انتظار بدء العملية
            if self.server_process.waitForStarted(5000):
                self.server_started.emit(True, "تم بدء تشغيل الخادم...")
                
                # فحص الحالة بعد 3 ثواني
                QTimer.singleShot(3000, self.delayed_status_check)
            else:
                self.server_started.emit(False, "فشل في بدء عملية الخادم")
                
        except Exception as e:
            self.server_started.emit(False, f"خطأ في تشغيل الخادم: {str(e)}")
    
    def delayed_status_check(self):
        """فحص حالة الخادم بعد تأخير"""
        if self.check_server_status():
            self.is_running = True
            self.status_changed.emit(True, "الخادم يعمل بنجاح")
        else:
            self.status_changed.emit(False, "الخادم لم يبدأ بعد، جاري المحاولة...")
    
    def start_server_external(self):
        """تشغيل الخادم في terminal منفصل (Windows)"""
        app_py_path = os.path.join(self.project_path, "app.py.py")
        if not os.path.exists(app_py_path):
            self.server_started.emit(False, "ملف app.py.py غير موجود")
            return
        
        try:
            if sys.platform.startswith('win'):
                # تشغيل في cmd منفصل على Windows
                cmd = f'start cmd /k "cd /d "{self.project_path}" && python app.py.py"'
                os.system(cmd)
            elif sys.platform.startswith('darwin'):
                # macOS
                cmd = f'osascript -e \'tell app "Terminal" to do script "cd {self.project_path} && python app.py.py"\''
                os.system(cmd)
            else:
                # Linux
                cmd = f'gnome-terminal -- bash -c "cd {self.project_path} && python app.py.py; exec bash"'
                os.system(cmd)
            
            self.server_started.emit(True, "تم تشغيل الخادم في terminal منفصل")
            
            # فحص الحالة بعد 5 ثواني
            QTimer.singleShot(5000, self.delayed_status_check)
            
        except Exception as e:
            self.server_started.emit(False, f"خطأ في تشغيل الخادم: {str(e)}")
    
    def stop_server(self):
        """إيقاف الخادم"""
        if self.server_process and self.server_process.state() == QProcess.Running:
            self.server_process.kill()
            self.server_process.waitForFinished(5000)
        
        self.is_running = False
        self.status_changed.emit(False, "تم إيقاف الخادم")
    
    def check_server_status(self) -> bool:
        """فحص حالة الخادم"""
        try:
            response = requests.get(self.server_url, timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def run(self):
        """مراقبة حالة الخادم باستمرار"""
        while not self.should_stop:
            current_status = self.check_server_status()
            if current_status != self.is_running:
                self.is_running = current_status
                status_msg = "الخادم متصل" if current_status else "الخادم غير متصل"
                self.status_changed.emit(current_status, status_msg)
            
            time.sleep(5)  # فحص كل 5 ثواني


class ImageProcessor:
    """معالج الصور - يحتوي على جميع وظائف تعديل الصور"""
    
    def __init__(self, images_path: str):
        self.images_path = images_path
    
    def get_image_info(self, filename: str) -> Dict[str, Any]:
        """الحصول على معلومات الصورة"""
        filepath = os.path.join(self.images_path, filename)
        if not os.path.exists(filepath):
            return {}
        
        try:
            with Image.open(filepath) as img:
                file_size = os.path.getsize(filepath)
                return {
                    'filename': filename,
                    'format': img.format,
                    'mode': img.mode,
                    'size': img.size,  # (width, height)
                    'file_size': file_size,
                    'file_size_mb': round(file_size / (1024 * 1024), 2)
                }
        except Exception as e:
            return {'error': str(e)}
    
    def resize_image(self, filename: str, new_width: int, new_height: int) -> str:
        """تغيير حجم الصورة"""
        input_path = os.path.join(self.images_path, filename)
        name, ext = os.path.splitext(filename)
        output_filename = f"{name}_resized_{new_width}x{new_height}{ext}"
        output_path = os.path.join(self.images_path, output_filename)
        
        try:
            with Image.open(input_path) as img:
                resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                resized_img.save(output_path)
                return output_filename
        except Exception as e:
            raise Exception(f"خطأ في تغيير الحجم: {str(e)}")
    
    def apply_brightness(self, filename: str, factor: float) -> str:
        """تطبيق تأثير الإضاءة"""
        input_path = os.path.join(self.images_path, filename)
        name, ext = os.path.splitext(filename)
        output_filename = f"{name}_bright_{factor}{ext}"
        output_path = os.path.join(self.images_path, output_filename)
        
        try:
            with Image.open(input_path) as img:
                enhancer = ImageEnhance.Brightness(img)
                bright_img = enhancer.enhance(factor)
                bright_img.save(output_path)
                return output_filename
        except Exception as e:
            raise Exception(f"خطأ في تعديل الإضاءة: {str(e)}")
    
    def apply_contrast(self, filename: str, factor: float) -> str:
        """تطبيق تأثير التباين"""
        input_path = os.path.join(self.images_path, filename)
        name, ext = os.path.splitext(filename)
        output_filename = f"{name}_contrast_{factor}{ext}"
        output_path = os.path.join(self.images_path, output_filename)
        
        try:
            with Image.open(input_path) as img:
                enhancer = ImageEnhance.Contrast(img)
                contrast_img = enhancer.enhance(factor)
                contrast_img.save(output_path)
                return output_filename
        except Exception as e:
            raise Exception(f"خطأ في تعديل التباين: {str(e)}")
    
    def apply_blur(self, filename: str, radius: int) -> str:
        """تطبيق تأثير التمويه"""
        input_path = os.path.join(self.images_path, filename)
        name, ext = os.path.splitext(filename)
        output_filename = f"{name}_blur_{radius}{ext}"
        output_path = os.path.join(self.images_path, output_filename)
        
        try:
            with Image.open(input_path) as img:
                blurred_img = img.filter(ImageFilter.GaussianBlur(radius))
                blurred_img.save(output_path)
                return output_filename
        except Exception as e:
            raise Exception(f"خطأ في تطبيق التمويه: {str(e)}")
    
    def apply_sharpen(self, filename: str) -> str:
        """تطبيق تأثير الحدة"""
        input_path = os.path.join(self.images_path, filename)
        name, ext = os.path.splitext(filename)
        output_filename = f"{name}_sharp{ext}"
        output_path = os.path.join(self.images_path, output_filename)
        
        try:
            with Image.open(input_path) as img:
                sharpened_img = img.filter(ImageFilter.SHARPEN)
                sharpened_img.save(output_path)
                return output_filename
        except Exception as e:
            raise Exception(f"خطأ في تطبيق الحدة: {str(e)}")
    
    def rotate_image(self, filename: str, angle: int) -> str:
        """دوران الصورة"""
        input_path = os.path.join(self.images_path, filename)
        name, ext = os.path.splitext(filename)
        output_filename = f"{name}_rotated_{angle}{ext}"
        output_path = os.path.join(self.images_path, output_filename)
        
        try:
            with Image.open(input_path) as img:
                rotated_img = img.rotate(angle, expand=True)
                rotated_img.save(output_path)
                return output_filename
        except Exception as e:
            raise Exception(f"خطأ في دوران الصورة: {str(e)}")
    
    def crop_image(self, filename: str, left: int, top: int, right: int, bottom: int) -> str:
        """قص الصورة"""
        input_path = os.path.join(self.images_path, filename)
        name, ext = os.path.splitext(filename)
        output_filename = f"{name}_cropped{ext}"
        output_path = os.path.join(self.images_path, output_filename)
        
        try:
            with Image.open(input_path) as img:
                cropped_img = img.crop((left, top, right, bottom))
                cropped_img.save(output_path)
                return output_filename
        except Exception as e:
            raise Exception(f"خطأ في قص الصورة: {str(e)}")


class ImageListWidget(QListWidget):
    """قائمة الصور مع دعم السحب والإفلات"""
    
    image_selected = pyqtSignal(str)  # إشارة عند اختيار صورة
    
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.InternalMove)
        self.setSelectionMode(QListWidget.SingleSelection)
        
        # تنسيق القائمة
        self.setStyleSheet("""
            QListWidget {
                background-color: #1a1a2e;
                border: 2px solid #00ff41;
                border-radius: 8px;
                color: #00ff41;
                font-family: 'Courier New', monospace;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #333;
                background-color: rgba(0, 255, 65, 0.1);
            }
            QListWidget::item:selected {
                background-color: #00ff41;
                color: black;
                font-weight: bold;
            }
            QListWidget::item:hover {
                background-color: rgba(0, 255, 65, 0.2);
            }
        """)
        
        self.itemClicked.connect(self.on_item_selected)
    
    def on_item_selected(self, item):
        """عند اختيار عنصر من القائمة"""
        filename = item.text()
        self.image_selected.emit(filename)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """عند بدء سحب ملف"""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
    
    def dropEvent(self, event: QDropEvent):
        """عند إفلات ملف"""
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        image_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]
        
        if image_files:
            # إشارة لرفع الملفات (يتم التعامل معها في النافذة الرئيسية)
            for file_path in image_files:
                print(f"تم إفلات ملف: {file_path}")


class ImagePreviewWidget(QLabel):
    """عنصر معاينة الصور"""
    
    def __init__(self):
        super().__init__()
        self.setMinimumSize(400, 300)
        self.setScaledContents(True)
        self.setAlignment(Qt.AlignCenter)
        
        # تنسيق المعاينة
        self.setStyleSheet("""
            QLabel {
                background-color: #0a0a0a;
                border: 2px solid #00ff41;
                border-radius: 8px;
                color: #00ff41;
                font-size: 14px;
            }
        """)
        
        self.setText("🖼️ اختر صورة لعرضها")
        self.current_image_path = None
    
    def load_image(self, image_path: str):
        """تحميل وعرض صورة"""
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                # تغيير حجم الصورة للمعاينة
                scaled_pixmap = pixmap.scaled(
                    self.size(), 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                )
                self.setPixmap(scaled_pixmap)
                self.current_image_path = image_path
            else:
                self.setText("❌ لا يمكن تحميل الصورة")
        else:
            self.setText("❌ الملف غير موجود")
    
    def clear_preview(self):
        """مسح المعاينة"""
        self.clear()
        self.setText("🖼️ اختر صورة لعرضها")
        self.current_image_path = None


class ProjectDetector:
    """كاشف المشروع - يكتشف مجلد المشروع تلقائياً"""
    
    @staticmethod
    def find_project_path() -> Optional[str]:
        """البحث عن مجلد المشروع"""
        # البحث في المجلد الحالي أولاً
        current_dir = os.getcwd()
        if ProjectDetector.is_valid_project(current_dir):
            return current_dir
        
        # البحث في المجلد الذي يحتوي على هذا الملف
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if ProjectDetector.is_valid_project(script_dir):
            return script_dir
        
        # البحث في مجلدات سطح المكتب
        desktop_paths = [
            os.path.join(os.path.expanduser("~"), "Desktop"),
            os.path.join(os.path.expanduser("~"), "سطح المكتب"),
        ]
        
        for desktop in desktop_paths:
            if os.path.exists(desktop):
                for item in os.listdir(desktop):
                    item_path = os.path.join(desktop, item)
                    if os.path.isdir(item_path) and ProjectDetector.is_valid_project(item_path):
                        return item_path
        
        return None
    
    @staticmethod
    def is_valid_project(path: str) -> bool:
        """فحص ما إذا كان المجلد يحتوي على مشروع فؤاد"""
        required_files = ["app.py.py", "index.html", "main.html"]
        images_folder = os.path.join(path, "images")
        
        # فحص وجود الملفات المطلوبة
        for file in required_files:
            if not os.path.exists(os.path.join(path, file)):
                return False
        
        # فحص وجود مجلد الصور
        return os.path.exists(images_folder)
    
    @staticmethod
    def get_images_in_project(project_path: str) -> List[str]:
        """الحصول على قائمة الصور في المشروع"""
        images_path = os.path.join(project_path, "images")
        if not os.path.exists(images_path):
            return []
        
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
        images = []
        
        for file in os.listdir(images_path):
            if any(file.lower().endswith(ext) for ext in image_extensions):
                images.append(file)
        
        return sorted(images)


class FouadImageManager(QMainWindow):
    """النافذة الرئيسية لمدير صور فؤاد"""
    
    def __init__(self):
        super().__init__()
        self.project_path = None
        self.images_path = None
        self.server_manager = None
        self.image_processor = None
        self.current_selected_image = None
        
        # إعدادات التطبيق
        self.settings = QSettings("FouadCyber", "ImageManager")
        
        # البحث عن مجلد المشروع
        self.detect_project()
        
        # إعداد الواجهة
        self.setup_ui()
        self.setup_styles()
        
        # بدء مراقبة الخادم
        if self.project_path:
            self.start_server_monitoring()
        
        # تحميل الصور
        self.refresh_images()
    
    def detect_project(self):
        """كشف مجلد المشروع تلقائياً"""
        self.project_path = ProjectDetector.find_project_path()
        
        if self.project_path:
            self.images_path = os.path.join(self.project_path, "images")
            self.image_processor = ImageProcessor(self.images_path)
            self.setWindowTitle(f"🛡️ مدير صور فؤاد - {os.path.basename(self.project_path)}")
        else:
            self.setWindowTitle("🛡️ مدير صور فؤاد - لم يتم العثور على المشروع")
    
    def setup_ui(self):
        """إعداد واجهة المستخدم"""
        self.setMinimumSize(1200, 800)
        self.setWindowIcon(QIcon())  # يمكن إضافة أيقونة هنا
        
        # الودجت المركزي
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # التخطيط الرئيسي
        main_layout = QHBoxLayout(central_widget)
        
        # الشريط الجانبي الأيسر (قائمة الصور والتحكم)
        left_panel = self.create_left_panel()
        
        # المنطقة الوسطى (معاينة الصور)
        center_panel = self.create_center_panel()
        
        # الشريط الجانبي الأيمن (أدوات التعديل)
        right_panel = self.create_right_panel()
        
        # تقسيم المساحة
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(center_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 600, 300])
        
        main_layout.addWidget(splitter)
        
        # إعداد شريط الحالة
        self.status_bar = self.statusBar()
        self.status_bar.setStyleSheet("QStatusBar { color: #00ff00; background-color: #1a1a1a; border-top: 1px solid #333; }")
        self.status_bar.showMessage("جاري تحميل المشروع...")
        
        # رسالة ترحيب
        if self.project_path:
            self.status_bar.showMessage(f"✅ تم العثور على المشروع: {self.project_path}")
        else:
            self.status_bar.showMessage("❌ لم يتم العثور على مشروع فؤاد")
    
    def create_left_panel(self) -> QWidget:
        """إنشاء الشريط الجانبي الأيسر"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # عنوان القسم
        title = QLabel("🖼️ قائمة الصور")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(title)
        
        # أزرار التحكم
        buttons_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 تحديث")
        refresh_btn.clicked.connect(self.refresh_images)
        buttons_layout.addWidget(refresh_btn)
        
        add_btn = QPushButton("➕ إضافة")
        add_btn.clicked.connect(self.add_images)
        buttons_layout.addWidget(add_btn)
        
        layout.addLayout(buttons_layout)
        
        # قائمة الصور
        self.images_list = ImageListWidget()
        self.images_list.image_selected.connect(self.on_image_selected)
        layout.addWidget(self.images_list)
        
        # معلومات الصورة المختارة
        self.image_info_group = QGroupBox("📊 معلومات الصورة")
        self.image_info_layout = QVBoxLayout(self.image_info_group)
        
        self.info_label = QLabel("اختر صورة لعرض المعلومات")
        self.info_label.setWordWrap(True)
        self.image_info_layout.addWidget(self.info_label)
        
        layout.addWidget(self.image_info_group)
        
        # حالة الخادم
        self.server_group = QGroupBox("🌐 حالة الخادم")
        server_layout = QVBoxLayout(self.server_group)
        
        self.server_status_label = QLabel("⚪ فحص الحالة...")
        server_layout.addWidget(self.server_status_label)
        
        # أزرار تحكم الخادم
        server_buttons_layout = QVBoxLayout()
        
        # الصف الأول - تشغيل عادي وإيقاف
        row1_layout = QHBoxLayout()
        self.start_server_btn = QPushButton("▶️ تشغيل الخادم")
        self.start_server_btn.clicked.connect(self.start_server)
        row1_layout.addWidget(self.start_server_btn)
        
        self.stop_server_btn = QPushButton("⏹️ إيقاف الخادم")
        self.stop_server_btn.clicked.connect(self.stop_server)
        self.stop_server_btn.setEnabled(False)
        row1_layout.addWidget(self.stop_server_btn)
        
        # الصف الثاني - تشغيل في terminal منفصل
        row2_layout = QHBoxLayout()
        self.start_external_btn = QPushButton("🖥️ تشغيل في Terminal")
        self.start_external_btn.setToolTip("تشغيل الخادم في نافذة Terminal منفصلة (لتجنب التعليق)")
        self.start_external_btn.clicked.connect(self.start_server_external)
        row2_layout.addWidget(self.start_external_btn)
        
        server_buttons_layout.addLayout(row1_layout)
        server_buttons_layout.addLayout(row2_layout)
        server_layout.addLayout(server_buttons_layout)
        
        layout.addWidget(self.server_group)
        
        return panel
    
    def create_center_panel(self) -> QWidget:
        """إنشاء المنطقة الوسطى لمعاينة الصور"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # عنوان القسم
        title = QLabel("👁️ معاينة الصورة")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # منطقة معاينة الصورة
        self.preview_widget = ImagePreviewWidget()
        layout.addWidget(self.preview_widget, 1)
        
        # معلومات سريعة
        info_layout = QHBoxLayout()
        
        self.quick_info = QLabel("الأبعاد: -- | الحجم: -- | النوع: --")
        self.quick_info.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(self.quick_info)
        
        layout.addLayout(info_layout)
        
        # أزرار سريعة
        quick_buttons_layout = QHBoxLayout()
        
        view_original_btn = QPushButton("🔍 الحجم الأصلي")
        view_original_btn.clicked.connect(self.view_original_size)
        
        open_folder_btn = QPushButton("📁 فتح المجلد")
        open_folder_btn.clicked.connect(self.open_images_folder)
        
        preview_web_btn = QPushButton("🌐 معاينة الموقع")
        preview_web_btn.clicked.connect(self.preview_website)
        
        quick_buttons_layout.addWidget(view_original_btn)
        quick_buttons_layout.addWidget(open_folder_btn)
        quick_buttons_layout.addWidget(preview_web_btn)
        
        layout.addLayout(quick_buttons_layout)
        
        return panel
    
    def create_right_panel(self) -> QWidget:
        """إنشاء الشريط الجانبي الأيمن لأدوات التعديل"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # علامات التبويب للأدوات المختلفة
        self.tools_tabs = QTabWidget()
        
        # تبويب تغيير الحجم
        resize_tab = self.create_resize_tab()
        self.tools_tabs.addTab(resize_tab, "📏 الحجم")
        
        # تبويب الفلاتر
        filters_tab = self.create_filters_tab()
        self.tools_tabs.addTab(filters_tab, "🎨 الفلاتر")
        
        # تبويب التحويل
        transform_tab = self.create_transform_tab()
        self.tools_tabs.addTab(transform_tab, "🔄 تحويل")
        
        # تبويب الإعدادات
        settings_tab = self.create_settings_tab()
        self.tools_tabs.addTab(settings_tab, "⚙️ إعدادات")
        
        layout.addWidget(self.tools_tabs)
        
        # شريط التقدم للعمليات
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # رسائل الحالة
        self.operation_status = QLabel("")
        self.operation_status.setWordWrap(True)
        layout.addWidget(self.operation_status)
        
        return panel
    
    def create_resize_tab(self) -> QWidget:
        """إنشاء تبويب تغيير الحجم"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # مجموعة أبعاد جديدة
        dimensions_group = QGroupBox("📐 أبعاد جديدة")
        dimensions_layout = QFormLayout(dimensions_group)
        
        self.width_spinbox = QSpinBox()
        self.width_spinbox.setRange(1, 9999)
        self.width_spinbox.setValue(800)
        
        self.height_spinbox = QSpinBox()
        self.height_spinbox.setRange(1, 9999)
        self.height_spinbox.setValue(600)
        
        dimensions_layout.addRow("العرض (px):", self.width_spinbox)
        dimensions_layout.addRow("الارتفاع (px):", self.height_spinbox)
        
        # خيار الحفاظ على النسبة
        self.keep_ratio_checkbox = QCheckBox("الحفاظ على النسبة")
        self.keep_ratio_checkbox.setChecked(True)
        self.keep_ratio_checkbox.stateChanged.connect(self.on_ratio_changed)
        dimensions_layout.addRow(self.keep_ratio_checkbox)
        
        layout.addWidget(dimensions_group)
        
        # أحجام مسبقة الإعداد
        presets_group = QGroupBox("🎯 أحجام جاهزة")
        presets_layout = QVBoxLayout(presets_group)
        
        preset_sizes = [
            ("صغير - 400x300", 400, 300),
            ("متوسط - 800x600", 800, 600),
            ("كبير - 1200x900", 1200, 900),
            ("HD - 1920x1080", 1920, 1080),
            ("مربع - 500x500", 500, 500)
        ]
        
        for name, width, height in preset_sizes:
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, w=width, h=height: self.set_preset_size(w, h))
            presets_layout.addWidget(btn)
        
        layout.addWidget(presets_group)
        
        # زر تطبيق تغيير الحجم
        self.apply_resize_btn = QPushButton("✅ تطبيق تغيير الحجم")
        self.apply_resize_btn.clicked.connect(self.apply_resize)
        self.apply_resize_btn.setEnabled(False)
        layout.addWidget(self.apply_resize_btn)
        
        layout.addStretch()
        return widget
    
    def create_filters_tab(self) -> QWidget:
        """إنشاء تبويب الفلاتر"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # فلتر الإضاءة
        brightness_group = QGroupBox("💡 الإضاءة")
        brightness_layout = QVBoxLayout(brightness_group)
        
        self.brightness_slider = QSlider(Qt.Horizontal)
        self.brightness_slider.setRange(10, 300)  # 0.1 to 3.0
        self.brightness_slider.setValue(100)  # 1.0
        self.brightness_slider.valueChanged.connect(self.update_brightness_label)
        
        self.brightness_label = QLabel("1.0")
        brightness_layout.addWidget(QLabel("المستوى:"))
        brightness_layout.addWidget(self.brightness_slider)
        brightness_layout.addWidget(self.brightness_label)
        
        self.apply_brightness_btn = QPushButton("✨ تطبيق الإضاءة")
        self.apply_brightness_btn.clicked.connect(self.apply_brightness)
        self.apply_brightness_btn.setEnabled(False)
        brightness_layout.addWidget(self.apply_brightness_btn)
        
        layout.addWidget(brightness_group)
        
        # فلتر التباين
        contrast_group = QGroupBox("🌓 التباين")
        contrast_layout = QVBoxLayout(contrast_group)
        
        self.contrast_slider = QSlider(Qt.Horizontal)
        self.contrast_slider.setRange(10, 300)
        self.contrast_slider.setValue(100)
        self.contrast_slider.valueChanged.connect(self.update_contrast_label)
        
        self.contrast_label = QLabel("1.0")
        contrast_layout.addWidget(QLabel("المستوى:"))
        contrast_layout.addWidget(self.contrast_slider)
        contrast_layout.addWidget(self.contrast_label)
        
        self.apply_contrast_btn = QPushButton("🎭 تطبيق التباين")
        self.apply_contrast_btn.clicked.connect(self.apply_contrast)
        self.apply_contrast_btn.setEnabled(False)
        contrast_layout.addWidget(self.apply_contrast_btn)
        
        layout.addWidget(contrast_group)
        
        # فلتر التمويه
        blur_group = QGroupBox("🌫️ التمويه")
        blur_layout = QVBoxLayout(blur_group)
        
        self.blur_slider = QSlider(Qt.Horizontal)
        self.blur_slider.setRange(1, 20)
        self.blur_slider.setValue(2)
        self.blur_slider.valueChanged.connect(self.update_blur_label)
        
        self.blur_label = QLabel("2")
        blur_layout.addWidget(QLabel("الشدة:"))
        blur_layout.addWidget(self.blur_slider)
        blur_layout.addWidget(self.blur_label)
        
        self.apply_blur_btn = QPushButton("💨 تطبيق التمويه")
        self.apply_blur_btn.clicked.connect(self.apply_blur)
        self.apply_blur_btn.setEnabled(False)
        blur_layout.addWidget(self.apply_blur_btn)
        
        layout.addWidget(blur_group)
        
        # فلتر الحدة
        sharpen_group = QGroupBox("🔪 الحدة")
        sharpen_layout = QVBoxLayout(sharpen_group)
        
        self.apply_sharpen_btn = QPushButton("⚡ تطبيق الحدة")
        self.apply_sharpen_btn.clicked.connect(self.apply_sharpen)
        self.apply_sharpen_btn.setEnabled(False)
        sharpen_layout.addWidget(self.apply_sharpen_btn)
        
        layout.addWidget(sharpen_group)
        
        layout.addStretch()
        return widget
    
    def create_transform_tab(self) -> QWidget:
        """إنشاء تبويب التحويل"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # دوران الصورة
        rotation_group = QGroupBox("🔄 دوران الصورة")
        rotation_layout = QVBoxLayout(rotation_group)
        
        rotation_buttons_layout = QHBoxLayout()
        
        rotate_90_btn = QPushButton("↺ 90°")
        rotate_90_btn.clicked.connect(lambda: self.rotate_image(90))
        
        rotate_180_btn = QPushButton("↻ 180°")
        rotate_180_btn.clicked.connect(lambda: self.rotate_image(180))
        
        rotate_270_btn = QPushButton("↺ 270°")
        rotate_270_btn.clicked.connect(lambda: self.rotate_image(270))
        
        rotation_buttons_layout.addWidget(rotate_90_btn)
        rotation_buttons_layout.addWidget(rotate_180_btn)
        rotation_buttons_layout.addWidget(rotate_270_btn)
        
        rotation_layout.addLayout(rotation_buttons_layout)
        
        # دوران مخصص
        custom_rotation_layout = QHBoxLayout()
        self.rotation_spinbox = QSpinBox()
        self.rotation_spinbox.setRange(-360, 360)
        self.rotation_spinbox.setValue(0)
        
        custom_rotate_btn = QPushButton("دوران مخصص")
        custom_rotate_btn.clicked.connect(self.apply_custom_rotation)
        
        custom_rotation_layout.addWidget(QLabel("الزاوية:"))
        custom_rotation_layout.addWidget(self.rotation_spinbox)
        custom_rotation_layout.addWidget(custom_rotate_btn)
        
        rotation_layout.addLayout(custom_rotation_layout)
        layout.addWidget(rotation_group)
        
        # انعكاس الصورة
        flip_group = QGroupBox("🪞 انعكاس الصورة")
        flip_layout = QVBoxLayout(flip_group)
        
        flip_buttons_layout = QHBoxLayout()
        
        flip_horizontal_btn = QPushButton("⟷ أفقي")
        flip_horizontal_btn.clicked.connect(self.flip_horizontal)
        
        flip_vertical_btn = QPushButton("⟸ عمودي")
        flip_vertical_btn.clicked.connect(self.flip_vertical)
        
        flip_buttons_layout.addWidget(flip_horizontal_btn)
        flip_buttons_layout.addWidget(flip_vertical_btn)
        
        flip_layout.addLayout(flip_buttons_layout)
        layout.addWidget(flip_group)
        
        # تحويل الصيغة
        format_group = QGroupBox("📄 تحويل الصيغة")
        format_layout = QVBoxLayout(format_group)
        
        self.output_format_combo = QComboBox()
        self.output_format_combo.addItems(["PNG", "JPEG", "GIF", "BMP", "WEBP"])
        
        convert_format_btn = QPushButton("🔄 تحويل الصيغة")
        convert_format_btn.clicked.connect(self.convert_format)
        
        format_layout.addWidget(QLabel("الصيغة الجديدة:"))
        format_layout.addWidget(self.output_format_combo)
        format_layout.addWidget(convert_format_btn)
        
        layout.addWidget(format_group)
        
        layout.addStretch()
        return widget
    
    def create_settings_tab(self) -> QWidget:
        """إنشاء تبويب الإعدادات"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # إعدادات الحفظ
        save_group = QGroupBox("💾 إعدادات الحفظ")
        save_layout = QVBoxLayout(save_group)
        
        self.backup_original_checkbox = QCheckBox("إنشاء نسخة احتياطية من الأصلي")
        self.backup_original_checkbox.setChecked(True)
        
        self.add_timestamp_checkbox = QCheckBox("إضافة التاريخ والوقت للاسم")
        self.add_timestamp_checkbox.setChecked(False)
        
        save_layout.addWidget(self.backup_original_checkbox)
        save_layout.addWidget(self.add_timestamp_checkbox)
        
        layout.addWidget(save_group)
        
        # إعدادات الخادم
        server_settings_group = QGroupBox("🌐 إعدادات الخادم")
        server_settings_layout = QFormLayout(server_settings_group)
        
        self.server_url_edit = QLineEdit("http://localhost:5000")
        self.auto_start_server_checkbox = QCheckBox("تشغيل الخادم تلقائياً")
        self.auto_start_server_checkbox.setChecked(True)
        
        server_settings_layout.addRow("عنوان الخادم:", self.server_url_edit)
        server_settings_layout.addRow(self.auto_start_server_checkbox)
        
        layout.addWidget(server_settings_group)
        
        # أدوات إضافية
        tools_group = QGroupBox("🔧 أدوات إضافية")
        tools_layout = QVBoxLayout(tools_group)
        
        clear_cache_btn = QPushButton("🗑️ مسح الملفات المؤقتة")
        clear_cache_btn.clicked.connect(self.clear_cache)
        
        backup_images_btn = QPushButton("📦 نسخ احتياطي للصور")
        backup_images_btn.clicked.connect(self.backup_images)
        
        optimize_images_btn = QPushButton("⚡ تحسين جميع الصور")
        optimize_images_btn.clicked.connect(self.optimize_all_images)
        
        tools_layout.addWidget(clear_cache_btn)
        tools_layout.addWidget(backup_images_btn)
        tools_layout.addWidget(optimize_images_btn)
        
        layout.addWidget(tools_group)
        
        # معلومات التطبيق
        info_group = QGroupBox("ℹ️ معلومات التطبيق")
        info_layout = QVBoxLayout(info_group)
        
        version_label = QLabel("الإصدار: 1.0.0")
        developer_label = QLabel("المطور: فؤاد للأمن السيبراني")
        
        info_layout.addWidget(version_label)
        info_layout.addWidget(developer_label)
        
        layout.addWidget(info_group)
        
        layout.addStretch()
        return widget
    
    def setup_styles(self):
        """إعداد تنسيقات التطبيق بنمط فؤاد السايبرني"""
        self.setStyleSheet("""
        QMainWindow {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #0a0a0a, stop:0.5 #1a1a2e, stop:1 #16213e);
            color: #00ff41;
            font-family: 'Courier New', monospace;
        }
        QWidget {
            background-color: transparent;
            color: #00ff41;
        }
        QPushButton {
            background-color: rgba(0, 255, 65, 0.2);
            border: 2px solid #00ff41;
            border-radius: 6px;
            color: #00ff41;
            font-weight: bold;
            padding: 8px 16px;
            font-family: 'Courier New', monospace;
        }
        QPushButton:hover {
            background-color: rgba(0, 255, 65, 0.4);
            box-shadow: 0 0 10px #00ff41;
        }
        QPushButton:pressed {
            background-color: #00ff41;
            color: black;
        }
        QPushButton:disabled {
            background-color: rgba(128, 128, 128, 0.2);
            border-color: #666;
            color: #666;
        }
        QGroupBox {
            border: 2px solid #00ff41;
            border-radius: 8px;
            margin: 5px;
            padding-top: 15px;
            font-weight: bold;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            color: #00ff41;
            font-weight: bold;
        }
        QTabWidget::pane {
            border: 2px solid #00ff41;
            background-color: rgba(0, 0, 0, 0.3);
        }
        QTabBar::tab {
            background-color: rgba(0, 255, 65, 0.1);
            border: 1px solid #00ff41;
            padding: 8px 12px;
            margin: 2px;
            color: #00ff41;
        }
        QTabBar::tab:selected {
            background-color: #00ff41;
            color: black;
            font-weight: bold;
        }
        QSlider::groove:horizontal {
            border: 1px solid #00ff41;
            height: 6px;
            background: #1a1a2e;
            border-radius: 3px;
        }
        QSlider::handle:horizontal {
            background: #00ff41;
            border: 1px solid #00ff41;
            width: 18px;
            margin: -6px 0;
            border-radius: 9px;
        }
        QSpinBox, QComboBox, QLineEdit {
            border: 2px solid #00ff41;
            border-radius: 4px;
            padding: 4px 8px;
            background-color: rgba(0, 0, 0, 0.5);
            color: #00ff41;
        }
        QProgressBar {
            border: 2px solid #00ff41;
            border-radius: 5px;
            text-align: center;
            background-color: #1a1a2e;
        }
        QProgressBar::chunk {
            background-color: #00ff41;
            border-radius: 3px;
        }
        QStatusBar {
            background-color: rgba(0, 0, 0, 0.8);
            border-top: 1px solid #00ff41;
            color: #00ff41;
        }
        """)
    
    def refresh_images(self):
        """تحديث قائمة الصور"""
        if not self.images_path or not os.path.exists(self.images_path):
            self.status_bar.showMessage("❌ مجلد الصور غير موجود")
            return
        
        self.images_list.clear()
        images = ProjectDetector.get_images_in_project(self.project_path)
        
        for image in images:
            item = QListWidgetItem(image)
            self.images_list.addItem(item)
        
        self.status_bar.showMessage(f"🔄 تم تحديث القائمة - {len(images)} صورة")
    
    def on_image_selected(self, filename: str):
        """عند اختيار صورة من القائمة"""
        self.current_selected_image = filename
        image_path = os.path.join(self.images_path, filename)
        
        # عرض الصورة في المعاينة
        self.preview_widget.load_image(image_path)
        
        # عرض معلومات الصورة
        if self.image_processor:
            info = self.image_processor.get_image_info(filename)
            if 'error' not in info:
                info_text = f"""
الاسم: {info['filename']}
الصيغة: {info['format']}
الأبعاد: {info['size'][0]}x{info['size'][1]} بكسل
نمط الألوان: {info['mode']}
حجم الملف: {info['file_size_mb']} ميجابايت
                """.strip()
                self.info_label.setText(info_text)
                
                # تحديث المعلومات السريعة
                self.quick_info.setText(
                    f"الأبعاد: {info['size'][0]}x{info['size'][1]} | "
                    f"الحجم: {info['file_size_mb']} MB | "
                    f"النوع: {info['format']}"
                )
                
                # تمكين أزرار التعديل
                self.enable_edit_buttons(True)
                
                # تحديث قيم تغيير الحجم
                self.width_spinbox.setValue(info['size'][0])
                self.height_spinbox.setValue(info['size'][1])
            else:
                self.info_label.setText(f"خطأ: {info['error']}")
        
        self.status_bar.showMessage(f"تم اختيار: {filename}")
    
    def enable_edit_buttons(self, enabled: bool):
        """تمكين/تعطيل أزرار التعديل"""
        self.apply_resize_btn.setEnabled(enabled)
        self.apply_brightness_btn.setEnabled(enabled)
        self.apply_contrast_btn.setEnabled(enabled)
        self.apply_blur_btn.setEnabled(enabled)
        self.apply_sharpen_btn.setEnabled(enabled)
    
    def add_images(self):
        """إضافة صور جديدة"""
        if not self.images_path:
            QMessageBox.warning(self, "تحذير", "مجلد المشروع غير محدد")
            return
        
        files, _ = QFileDialog.getOpenFileNames(
            self, 
            "اختر الصور المراد إضافتها",
            "",
            "ملفات الصور (*.png *.jpg *.jpeg *.gif *.bmp *.webp);;جميع الملفات (*.*)"
        )
        
        if files:
            copied_count = 0
            for file_path in files:
                filename = os.path.basename(file_path)
                dest_path = os.path.join(self.images_path, filename)
                
                try:
                    shutil.copy2(file_path, dest_path)
                    copied_count += 1
                except Exception as e:
                    QMessageBox.warning(self, "خطأ", f"فشل نسخ {filename}: {str(e)}")
            
            if copied_count > 0:
                self.refresh_images()
                QMessageBox.information(self, "نجح", f"تم إضافة {copied_count} صورة بنجاح")
    
    def set_preset_size(self, width: int, height: int):
        """تعيين حجم مسبق"""
        self.width_spinbox.setValue(width)
        self.height_spinbox.setValue(height)
    
    def on_ratio_changed(self):
        """عند تغيير خيار الحفاظ على النسبة"""
        if self.keep_ratio_checkbox.isChecked() and self.current_selected_image:
            # حساب النسبة من الصورة الأصلية
            info = self.image_processor.get_image_info(self.current_selected_image)
            if 'error' not in info:
                original_ratio = info['size'][0] / info['size'][1]
                current_width = self.width_spinbox.value()
                new_height = int(current_width / original_ratio)
                self.height_spinbox.setValue(new_height)
    
    def apply_resize(self):
        """تطبيق تغيير الحجم"""
        if not self.current_selected_image:
            return
        
        width = self.width_spinbox.value()
        height = self.height_spinbox.value()
        
        try:
            self.show_operation_progress("جاري تغيير الحجم...")
            new_filename = self.image_processor.resize_image(
                self.current_selected_image, width, height
            )
            
            self.operation_status.setText(f"✅ تم إنشاء: {new_filename}")
            self.refresh_images()
            QMessageBox.information(self, "نجح", f"تم تغيير حجم الصورة!\nالملف الجديد: {new_filename}")
            
        except Exception as e:
            self.operation_status.setText(f"❌ فشل: {str(e)}")
            QMessageBox.critical(self, "خطأ", f"فشل تغيير الحجم: {str(e)}")
        finally:
            self.hide_operation_progress()
    
    def update_brightness_label(self, value):
        """تحديث نص شريط الإضاءة"""
        factor = value / 100.0
        self.brightness_label.setText(f"{factor:.1f}")
    
    def update_contrast_label(self, value):
        """تحديث نص شريط التباين"""
        factor = value / 100.0
        self.contrast_label.setText(f"{factor:.1f}")
    
    def update_blur_label(self, value):
        """تحديث نص شريط التمويه"""
        self.blur_label.setText(str(value))
    
    def apply_brightness(self):
        """تطبيق فلتر الإضاءة"""
        if not self.current_selected_image:
            return
        
        factor = self.brightness_slider.value() / 100.0
        
        try:
            self.show_operation_progress("جاري تطبيق الإضاءة...")
            new_filename = self.image_processor.apply_brightness(
                self.current_selected_image, factor
            )
            
            self.operation_status.setText(f"✅ تم إنشاء: {new_filename}")
            self.refresh_images()
            
        except Exception as e:
            self.operation_status.setText(f"❌ فشل: {str(e)}")
            QMessageBox.critical(self, "خطأ", f"فشل تطبيق الإضاءة: {str(e)}")
        finally:
            self.hide_operation_progress()
    
    def apply_contrast(self):
        """تطبيق فلتر التباين"""
        if not self.current_selected_image:
            return
        
        factor = self.contrast_slider.value() / 100.0
        
        try:
            self.show_operation_progress("جاري تطبيق التباين...")
            new_filename = self.image_processor.apply_contrast(
                self.current_selected_image, factor
            )
            
            self.operation_status.setText(f"✅ تم إنشاء: {new_filename}")
            self.refresh_images()
            
        except Exception as e:
            self.operation_status.setText(f"❌ فشل: {str(e)}")
            QMessageBox.critical(self, "خطأ", f"فشل تطبيق التباين: {str(e)}")
        finally:
            self.hide_operation_progress()
    
    def apply_blur(self):
        """تطبيق فلتر التمويه"""
        if not self.current_selected_image:
            return
        
        radius = self.blur_slider.value()
        
        try:
            self.show_operation_progress("جاري تطبيق التمويه...")
            new_filename = self.image_processor.apply_blur(
                self.current_selected_image, radius
            )
            
            self.operation_status.setText(f"✅ تم إنشاء: {new_filename}")
            self.refresh_images()
            
        except Exception as e:
            self.operation_status.setText(f"❌ فشل: {str(e)}")
            QMessageBox.critical(self, "خطأ", f"فشل تطبيق التمويه: {str(e)}")
        finally:
            self.hide_operation_progress()
    
    def apply_sharpen(self):
        """تطبيق فلتر الحدة"""
        if not self.current_selected_image:
            return
        
        try:
            self.show_operation_progress("جاري تطبيق الحدة...")
            new_filename = self.image_processor.apply_sharpen(self.current_selected_image)
            
            self.operation_status.setText(f"✅ تم إنشاء: {new_filename}")
            self.refresh_images()
            
        except Exception as e:
            self.operation_status.setText(f"❌ فشل: {str(e)}")
            QMessageBox.critical(self, "خطأ", f"فشل تطبيق الحدة: {str(e)}")
        finally:
            self.hide_operation_progress()
    
    def rotate_image(self, angle: int):
        """دوران الصورة"""
        if not self.current_selected_image:
            return
        
        try:
            self.show_operation_progress(f"جاري دوران الصورة {angle}°...")
            new_filename = self.image_processor.rotate_image(
                self.current_selected_image, angle
            )
            
            self.operation_status.setText(f"✅ تم إنشاء: {new_filename}")
            self.refresh_images()
            
        except Exception as e:
            self.operation_status.setText(f"❌ فشل: {str(e)}")
            QMessageBox.critical(self, "خطأ", f"فشل دوران الصورة: {str(e)}")
        finally:
            self.hide_operation_progress()
    
    def apply_custom_rotation(self):
        """تطبيق دوران مخصص"""
        angle = self.rotation_spinbox.value()
        if angle != 0:
            self.rotate_image(angle)
    
    def flip_horizontal(self):
        """انعكاس أفقي"""
        if not self.current_selected_image:
            return
        
        try:
            input_path = os.path.join(self.images_path, self.current_selected_image)
            name, ext = os.path.splitext(self.current_selected_image)
            output_filename = f"{name}_flipped_h{ext}"
            output_path = os.path.join(self.images_path, output_filename)
            
            self.show_operation_progress("جاري الانعكاس الأفقي...")
            
            with Image.open(input_path) as img:
                flipped_img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                flipped_img.save(output_path)
            
            self.operation_status.setText(f"✅ تم إنشاء: {output_filename}")
            self.refresh_images()
            
        except Exception as e:
            self.operation_status.setText(f"❌ فشل: {str(e)}")
            QMessageBox.critical(self, "خطأ", f"فشل الانعكاس: {str(e)}")
        finally:
            self.hide_operation_progress()
    
    def flip_vertical(self):
        """انعكاس عمودي"""
        if not self.current_selected_image:
            return
        
        try:
            input_path = os.path.join(self.images_path, self.current_selected_image)
            name, ext = os.path.splitext(self.current_selected_image)
            output_filename = f"{name}_flipped_v{ext}"
            output_path = os.path.join(self.images_path, output_filename)
            
            self.show_operation_progress("جاري الانعكاس العمودي...")
            
            with Image.open(input_path) as img:
                flipped_img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
                flipped_img.save(output_path)
            
            self.operation_status.setText(f"✅ تم إنشاء: {output_filename}")
            self.refresh_images()
            
        except Exception as e:
            self.operation_status.setText(f"❌ فشل: {str(e)}")
            QMessageBox.critical(self, "خطأ", f"فشل الانعكاس: {str(e)}")
        finally:
            self.hide_operation_progress()
    
    def convert_format(self):
        """تحويل صيغة الصورة"""
        if not self.current_selected_image:
            return
        
        new_format = self.output_format_combo.currentText().lower()
        if new_format == 'jpeg':
            ext = '.jpg'
        else:
            ext = f'.{new_format}'
        
        try:
            input_path = os.path.join(self.images_path, self.current_selected_image)
            name = os.path.splitext(self.current_selected_image)[0]
            output_filename = f"{name}_converted{ext}"
            output_path = os.path.join(self.images_path, output_filename)
            
            self.show_operation_progress(f"جاري تحويل إلى {new_format.upper()}...")
            
            with Image.open(input_path) as img:
                # تحويل إلى RGB إذا كان التنسيق لا يدعم الشفافية
                if new_format in ['jpeg', 'bmp'] and img.mode in ['RGBA', 'LA']:
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = rgb_img
                
                img.save(output_path, format=new_format.upper())
            
            self.operation_status.setText(f"✅ تم التحويل: {output_filename}")
            self.refresh_images()
            
        except Exception as e:
            self.operation_status.setText(f"❌ فشل: {str(e)}")
            QMessageBox.critical(self, "خطأ", f"فشل تحويل الصيغة: {str(e)}")
        finally:
            self.hide_operation_progress()
    
    def show_operation_progress(self, message: str):
        """عرض شريط التقدم مع رسالة"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # شريط لانهائي
        self.operation_status.setText(f"⏳ {message}")
        QApplication.processEvents()
    
    def hide_operation_progress(self):
        """إخفاء شريط التقدم"""
        self.progress_bar.setVisible(False)
        QApplication.processEvents()
    
    def view_original_size(self):
        """عرض الصورة بحجمها الأصلي"""
        if not self.current_selected_image:
            return
        
        image_path = os.path.join(self.images_path, self.current_selected_image)
        if sys.platform.startswith('win'):
            os.startfile(image_path)
        elif sys.platform.startswith('darwin'):
            subprocess.call(['open', image_path])
        else:
            subprocess.call(['xdg-open', image_path])
    
    def open_images_folder(self):
        """فتح مجلد الصور"""
        if not self.images_path:
            return
        
        if sys.platform.startswith('win'):
            os.startfile(self.images_path)
        elif sys.platform.startswith('darwin'):
            subprocess.call(['open', self.images_path])
        else:
            subprocess.call(['xdg-open', self.images_path])
    
    def preview_website(self):
        """معاينة الموقع في المتصفح"""
        url = self.server_url_edit.text()
        if sys.platform.startswith('win'):
            os.startfile(url)
        elif sys.platform.startswith('darwin'):
            subprocess.call(['open', url])
        else:
            subprocess.call(['xdg-open', url])
    
    def start_server_monitoring(self):
        """بدء مراقبة الخادم"""
        if not self.project_path:
            return
        
        self.server_manager = ServerManager(self.project_path)
        # الاتصال بإشارات الخادم
        self.server_manager.status_changed.connect(self.on_server_status_changed)
        self.server_manager.server_started.connect(self.on_server_start_attempt)
        self.server_manager.start()
        
        # تشغيل تلقائي للخادم إذا كان مفعلاً (بدون تعليق)
        if hasattr(self, 'auto_start_server_checkbox') and self.auto_start_server_checkbox.isChecked():
            QTimer.singleShot(1000, self.auto_start_server)
    
    def auto_start_server(self):
        """تشغيل تلقائي للخادم بدون تعليق"""
        if self.server_manager:
            self.server_manager.start_server_external()  # تشغيل في terminal منفصل
    
    def start_server(self):
        """تشغيل الخادم (عادي)"""
        if self.server_manager:
            self.server_manager.start_server()
    
    def start_server_external(self):
        """تشغيل الخادم في terminal منفصل"""
        if self.server_manager:
            self.server_manager.start_server_external()
    
    def stop_server(self):
        """إيقاف الخادم"""
        if self.server_manager:
            self.server_manager.stop_server()
    
    def on_server_start_attempt(self, success: bool, message: str):
        """معالج محاولة تشغيل الخادم"""
        if success:
            self.status_bar.showMessage(f"✅ {message}", 5000)
        else:
            self.status_bar.showMessage(f"❌ {message}", 5000)
    
    def on_server_status_changed(self, is_running: bool, message: str):
        """معالج تغيير حالة الخادم"""
        if is_running:
            self.server_status_label.setText("🟢 الخادم يعمل")
            self.server_status_label.setStyleSheet("color: #00ff00;")
            self.start_server_btn.setText("🔄 إعادة تشغيل")
            self.stop_server_btn.setEnabled(True)
            if hasattr(self, 'preview_website_btn'):
                self.preview_website_btn.setEnabled(True)
        else:
            self.server_status_label.setText("🔴 الخادم متوقف")
            self.server_status_label.setStyleSheet("color: #ff4444;")
            self.start_server_btn.setText("▶️ تشغيل الخادم")
            self.stop_server_btn.setEnabled(False)
            if hasattr(self, 'preview_website_btn'):
                self.preview_website_btn.setEnabled(False)
        
        self.status_bar.showMessage(message, 5000)
    
    def clear_cache(self):
        """مسح الملفات المؤقتة"""
        if not self.images_path:
            return
        
        reply = QMessageBox.question(
            self, 
            "تأكيد", 
            "هل تريد حذف جميع الصور المعدلة (التي تحتوي على _modified, _resized, إلخ)؟",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            deleted_count = 0
            for filename in os.listdir(self.images_path):
                if any(tag in filename for tag in ['_modified', '_resized', '_bright', '_contrast', '_blur', '_sharp', '_rotated', '_flipped', '_converted']):
                    file_path = os.path.join(self.images_path, filename)
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                    except Exception:
                        pass
            
            self.refresh_images()
            QMessageBox.information(self, "تم", f"تم حذف {deleted_count} ملف مؤقت")
    
    def backup_images(self):
        """عمل نسخة احتياطية للصور"""
        if not self.images_path:
            return
        
        backup_dir = QFileDialog.getExistingDirectory(self, "اختر مجلد النسخ الاحتياطي")
        if backup_dir:
            try:
                backup_folder = os.path.join(backup_dir, f"fouad_images_backup_{time.strftime('%Y%m%d_%H%M%S')}")
                shutil.copytree(self.images_path, backup_folder)
                QMessageBox.information(self, "نجح", f"تم إنشاء النسخة الاحتياطية في:\n{backup_folder}")
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"فشل إنشاء النسخة الاحتياطية: {str(e)}")
    
    def optimize_all_images(self):
        """تحسين جميع الصور (ضغط بدون فقدان جودة)"""
        if not self.images_path:
            return
        
        reply = QMessageBox.question(
            self, 
            "تأكيد", 
            "هل تريد تحسين جميع الصور؟ (قد يستغرق وقتاً طويلاً)",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            images = ProjectDetector.get_images_in_project(self.project_path)
            optimized_count = 0
            
            for i, image in enumerate(images):
                try:
                    image_path = os.path.join(self.images_path, image)
                    with Image.open(image_path) as img:
                        # حفظ بجودة محسنة
                        img.save(image_path, optimize=True, quality=85)
                        optimized_count += 1
                except Exception:
                    pass
                
                # تحديث التقدم
                progress = int((i + 1) / len(images) * 100)
                self.status_bar.showMessage(f"تحسين الصور... {progress}%")
                QApplication.processEvents()
            
            self.status_bar.showMessage(f"تم تحسين {optimized_count} صورة")
            QMessageBox.information(self, "تم", f"تم تحسين {optimized_count} صورة بنجاح")
    
    def closeEvent(self, event):
        """عند إغلاق التطبيق"""
        if self.server_manager:
            self.server_manager.should_stop = True
            self.server_manager.stop_server()
            self.server_manager.wait()
        
        # حفظ الإعدادات
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        
        event.accept()


def main():
    """الدالة الرئيسية لتشغيل التطبيق"""
    app = QApplication(sys.argv)
    
    # إعداد خصائص التطبيق
    app.setApplicationName("مدير صور فؤاد")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Fouad Cyber Security")
    app.setOrganizationDomain("fouadcyber.com")
    
    # إعداد ترميز UTF-8
    if sys.platform.startswith('win'):
        import locale
        try:
            locale.setlocale(locale.LC_ALL, 'C.UTF-8')
        except:
            pass
    
    # إنشاء النافذة الرئيسية
    window = FouadImageManager()
    window.show()
    
    # تشغيل التطبيق
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
