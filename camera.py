from onvif import ONVIFCamera
import cv2
import time
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import sys
import zeep
import zeep.exceptions
from zeep.transports import Transport
from requests import Session

def zeep_pythonvalue(self, xmlvalue):
    return xmlvalue

zeep.xsd.simple.AnySimpleType.pythonvalue = zeep_pythonvalue

class CameraApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("rtsptool")
        self.setGeometry(100, 100, 800, 600)
        
        # Kamera bilgileri
        self.camera_ip = '192.168.0.0'
        self.camera_port = 80  # ONVIF port
        self.rtsp_port = 554   # RTSP port
        self.username = 'admin'
        self.password = 'admin'
        
        # ONVIF timeout ve transport ayarları
        self.session = Session()
        self.transport = Transport(session=self.session, timeout=10)
        
        # Kamera değişkenleri
        self.cap = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.is_camera_active = False

        self.setup_ui()
        self.setup_onvif_connection()
        
    def setup_onvif_connection(self):
        try:
            print("ONVIF bağlantısı başlatılıyor...")
            
            # WSDL dosyalarının bulunduğu dizin
            wsdl_path = './wsdl'  # WSDL dizininin yolunu belirtin

            # ONVIF kamera nesnesini oluştur
            self.mycam = ONVIFCamera(
                self.camera_ip,
                self.camera_port,
                self.username,
                self.password,
                wsdl_dir=wsdl_path,
                transport=self.transport
            )

            # Servis adreslerini güncelle
            self.mycam.update_xaddrs()
            time.sleep(1)

            # Media servisi oluştur
            print("Media servisi oluşturuluyor...")
            self.media = self.mycam.create_media_service()
            self.media_profile = self.media.GetProfiles()[0]
            print(f"Media profili alındı: {self.media_profile.token}")

            # Imaging servisi oluşturuluyor
            try:
                print("Imaging servisi oluşturuluyor...")
                self.imaging = self.mycam.create_imaging_service()
                print("Imaging servisi oluşturuldu.")
            except Exception as e:
                print(f"Imaging servisi oluşturulamadı: {e}")

            # Cihaz yeteneklerini al
            self.get_camera_capabilities()

            # Imaging ayarlarını al
            self.get_imaging_settings()

            print("ONVIF bağlantısı başarılı!")

        except Exception as e:
            print(f"ONVIF bağlantı hatası: {e}")
            import traceback
            traceback.print_exc()

    def get_camera_capabilities(self):
        try:
            devicemgmt = self.mycam.create_devicemgmt_service()
            capabilities = devicemgmt.GetCapabilities({'Category': 'All'})
            print(f"Cihaz Yetenekleri: {capabilities}")
            
            if hasattr(capabilities, 'Imaging') and capabilities.Imaging:
                print("Imaging servisi destekleniyor.")
            else:
                print("Imaging servisi desteklenmiyor.")
        except Exception as e:
            print(f"Yetenekleri alma hatası: {e}")

    def get_imaging_settings(self):
        try:
            if hasattr(self, 'imaging'):
                video_source = self.media.GetVideoSources()[0]
                imaging_settings = self.imaging.GetImagingSettings({'VideoSourceToken': video_source.token})
                print(f"Mevcut Imaging Ayarları: {imaging_settings}")
            else:
                print("Imaging servisi mevcut değil.")
        except Exception as e:
            print(f"Imaging ayarlarını alma hatası: {e}")

    def adjust_brightness(self, value):
        try:
            if hasattr(self, 'imaging'):
                # Parlaklık değerini güncelle
                self.brightness_value.setText(str(value))

                # Video kaynağı tokenini al
                video_source = self.media.GetVideoSources()[0]

                # Imaging settings oluştur
                request = self.imaging.create_type('SetImagingSettings')
                request.VideoSourceToken = video_source.token

                # Mevcut imaging ayarlarını al
                imaging_settings = self.imaging.GetImagingSettings({'VideoSourceToken': video_source.token})

                # Yeni parlaklık değerini ayarla
                imaging_settings.Brightness = float(value)
                request.ImagingSettings = imaging_settings
                request.ForcePersistence = True

                # Yeni ayarları gönder
                self.imaging.SetImagingSettings(request)

                print(f"Parlaklık ayarlandı: {value}")
                print("Parlaklık ayarı gönderildi")

            else:
                print("Imaging servisi mevcut değil.")
        except zeep.exceptions.Fault as e:
            print(f"ONVIF Fault: {e}")
        except Exception as e:
            print(f"Parlaklık ayarlama hatası: {e}")
            import traceback
            traceback.print_exc()
            print("Parlaklık ayarı gönderilemedi")

    def set_ir_cut_filter_mode(self, mode):
        try:
            if hasattr(self, 'imaging'):
                # Video kaynağı tokenini al
                video_source = self.media.GetVideoSources()[0]

                # Imaging settings oluştur
                request = self.imaging.create_type('SetImagingSettings')
                request.VideoSourceToken = video_source.token

                # Mevcut imaging ayarlarını al
                imaging_settings = self.imaging.GetImagingSettings({'VideoSourceToken': video_source.token})

                # IR Cut Filter modunu ayarla
                imaging_settings.IRCutFilter = mode  # 'ON', 'OFF' veya 'AUTO' olabilir
                request.ImagingSettings = imaging_settings
                request.ForcePersistence = True

                # Yeni ayarları gönder
                self.imaging.SetImagingSettings(request)

                print(f"IR Cut Filter modu ayarlandı: {mode}")
            else:
                print("Imaging servisi mevcut değil.")
        except zeep.exceptions.Fault as e:
            print(f"ONVIF Fault: {e}")
        except Exception as e:
            print(f"IR Cut Filter ayarlama hatası: {e}")
            import traceback
            traceback.print_exc()

    def toggle_camera(self):
        if not self.is_camera_active:
            # URL'i input'tan al
            rtsp_url = self.url_input.text().strip()
            if not rtsp_url.startswith('rtsp://'):
                QMessageBox.warning(self, "Hata", "Geçerli bir RTSP URL'i giriniz!")
                return
                
            print(f"Bağlanılıyor: {rtsp_url}")
            self.cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            if self.cap.isOpened():
                print("Kamera bağlandı!")
                self.is_camera_active = True
                self.connect_button.setText("Durdur")
                self.set_status_color("green")
                self.timer.start(30)
            else:
                print("Kamera bağlantısı başarısız!")
                QMessageBox.warning(self, "Hata", "Kamera bağlantısı başarısız!")
                self.set_status_color("red")
        else:
            self.stop_camera()

    def move_ptz(self, pan=0, tilt=0, zoom=0):
        try:
            print(f"PTZ hareket başlatılıyor: zoom={zoom}")
            
            if not hasattr(self, 'ptz') or not hasattr(self, 'media_profile'):
                print("PTZ servisi veya media profili bulunamadı!")
                return
                
            # PTZ request oluştur
            request = self.ptz.create_type('ContinuousMove')
            request.ProfileToken = self.media_profile.token
            
            # Velocity ayarla
            request.Velocity = self.ptz.create_type('PTZSpeed')
            
            if zoom != 0:
                request.Velocity.Zoom = self.ptz.create_type('Vector1D')
                request.Velocity.Zoom.x = float(zoom)
                print(f"Zoom request ayarlandı: {request.Velocity.Zoom.x}")
            
            # Request'i gönder
            print("PTZ isteği gönderiliyor...")
            response = self.ptz.ContinuousMove(request)
            print(f"PTZ yanıtı: {response}")
            
        except Exception as e:
            print(f"PTZ hareket hatası: {e}")
            import traceback
            traceback.print_exc()

    def stop_ptz(self):
        try:
            print("PTZ hareketi durduruluyor...")
            if hasattr(self, 'ptz') and hasattr(self, 'media_profile'):
                self.ptz.Stop({
                    'ProfileToken': self.media_profile.token,
                    'PanTilt': True,
                    'Zoom': True
                })
                print("PTZ hareket durduruldu")
        except Exception as e:
            print(f"PTZ durdurma hatası: {e}")

    def setup_ui(self):
        # Ana widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Ana horizontal layout
        main_layout = QHBoxLayout(central_widget)
        
        # Sol panel (kamera görüntüsü ve kontroller)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Kontrol butonları için horizontal layout
        control_layout = QHBoxLayout()
        
        # RTSP URL input
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("rtsp://username:password@ip:port/stream")
        self.url_input.setText(f"rtsp://192.168.1.192:554/user=admin_password=Xms9XJIs_channel=1_stream=1.sdp?real_stream")
        self.url_input.setMinimumWidth(400)
        
        # Bağlantı durum göstergesi
        self.status_indicator = QPushButton()
        self.status_indicator.setFixedSize(20, 20)
        self.status_indicator.setEnabled(False)
        self.set_status_color("red")
        
        # Başlat/Durdur butonu
        self.connect_button = QPushButton("Bağlan")
        self.connect_button.clicked.connect(self.toggle_camera)
        
        # Kontrol layout'una ekle
        control_layout.addWidget(QLabel("RTSP URL:"))
        control_layout.addWidget(self.url_input)
        control_layout.addWidget(self.status_indicator)
        control_layout.addWidget(self.connect_button)
        
        # Kamera görüntüsü için label
        self.image_label = QLabel()
        self.image_label.setStyleSheet("QLabel { background-color: black; }")
        
        # Sol panel layout'una ekle
        left_layout.addLayout(control_layout)
        left_layout.addWidget(self.image_label)
        
        # Sağ panel (kamera bilgileri ve gece görüş kontrolü)
        right_panel = QWidget()
        right_panel.setMaximumWidth(300)
        right_layout = QFormLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        
        # Kamera bilgi alanları
        self.ip_input = QLineEdit(self.camera_ip)
        self.port_input = QLineEdit(str(self.camera_port))
        self.rtsp_port_input = QLineEdit(str(self.rtsp_port))
        self.username_input = QLineEdit(self.username)
        self.password_input = QLineEdit(self.password)
        #self.password_input.setEchoMode(QLineEdit.Password) /şiifre gizleme
        
        # Sağ panel form layout'una ekle
        right_layout.addRow("IP Adresi:", self.ip_input)
        right_layout.addRow("ONVIF Port:", self.port_input)
        right_layout.addRow("RTSP Port:", self.rtsp_port_input)
        right_layout.addRow("Kullanıcı Adı:", self.username_input)
        right_layout.addRow("Şifre:", self.password_input)
        
        # Gece görüş modu kontrolü
        night_vision_layout = QHBoxLayout()
        self.night_vision_button = QPushButton("Gece Görüşü Aç/Kapat")
        self.night_vision_button.clicked.connect(self.toggle_night_vision)
        night_vision_layout.addWidget(self.night_vision_button)
        right_layout.addRow("", night_vision_layout)
        
        # Ana layout'a panelleri ekle
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)

    def toggle_night_vision(self):
        # Gece görüş modunu değiştir
        try:
            # Modu almak veya tutmak için bir değişken kullanabilirsiniz
            if not hasattr(self, 'night_vision_on'):
                self.night_vision_on = False

            new_mode = 'ON' if not self.night_vision_on else 'OFF'
            self.set_ir_cut_filter_mode(new_mode)
            self.night_vision_on = not self.night_vision_on

            print(f"Gece görüş modu {'açıldı' if self.night_vision_on else 'kapatıldı'}")
        except Exception as e:
            print(f"Gece görüş modu değiştirme hatası: {e}")

    def set_status_color(self, color):
        self.status_indicator.setStyleSheet(
            f"QPushButton {{ background-color: {color}; border-radius: 10px; }}"
        )
        
    def stop_camera(self):
        self.timer.stop()
        if self.cap is not None:
            self.cap.release()
        self.is_camera_active = False
        self.connect_button.setText("Bağlan")
        self.set_status_color("red")
        self.image_label.clear()
        self.image_label.setStyleSheet("QLabel { background-color: black; }")
        
    def update_frame(self):
        if self.cap is None or not self.cap.isOpened():
            print("Kamera bağlantısı yok!")
            self.stop_camera()
            return

        try:
            ret, frame = self.cap.read()
            if ret:
                # Parlaklık değerini al
                
                # Parlaklık ayarı (-50 ile +50 arasında)
               
                
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                scaled_pixmap = QPixmap.fromImage(qt_image).scaled(
                    self.image_label.size(), 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                )
                self.image_label.setPixmap(scaled_pixmap)
            else:
                print("Frame okunamadı!")
                self.stop_camera()
        except Exception as e:
            print(f"Hata oluştu: {e}")
            self.stop_camera()
            
    def update_camera_info(self):
        try:
            # Get values from inputs
            self.camera_ip = self.ip_input.text().strip()
            self.camera_port = int(self.port_input.text().strip())
            self.rtsp_port = int(self.rtsp_port_input.text().strip())
            self.username = self.username_input.text().strip()
            self.password = self.password_input.text().strip()
            
            # Update RTSP URL
            new_rtsp_url = f"rtsp://{self.username}:{self.password}@{self.camera_ip}:{self.rtsp_port}/cam/realmonitor?channel=1&subtype=0"
            self.url_input.setText(new_rtsp_url)
            
            # If camera is connected, disconnect first
            if self.is_camera_active:
                self.stop_camera()
                
            # Try to setup new ONVIF connection
            self.setup_onvif_connection()
            self.get_camera_capabilities()
            
            QMessageBox.information(self, "Başarılı", "Kamera bilgileri güncellendi!")
            
        except ValueError as e:
            QMessageBox.warning(self, "Hata", "Port numaraları sayı olmalıdır!")
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Güncelleme başarısız: {str(e)}")
            
    def closeEvent(self, event):
        self.stop_camera()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = CameraApp()
    window.show()
    sys.exit(app.exec_())