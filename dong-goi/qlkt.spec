# -*- mode: python ; coding: utf-8 -*-
# Đóng gói: pyinstaller dong-goi/qlkt.spec  (chạy ở thư mục gốc repo, trên Windows)
# Kết quả: dist/QLKT/QLKT.exe (dạng thư mục: khởi động nhanh, ít bị phần mềm diệt virus báo nhầm hơn dạng 1 tệp)
from pathlib import Path

GOC = Path(SPECPATH).parent

# Bỏ các thành phần Qt không dùng cho nhẹ bộ cài
BO_QUA = ["PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick", "PySide6.Qt3DCore",
          "PySide6.Qt3DRender", "PySide6.QtQuick", "PySide6.QtQml", "PySide6.QtMultimedia", "PySide6.QtCharts",
          "PySide6.QtDataVisualization", "PySide6.QtPdf", "PySide6.QtBluetooth", "PySide6.QtPositioning",
          "PySide6.QtSensors", "PySide6.QtSerialPort", "PySide6.QtTest", "tkinter", "pytest"]

a = Analysis(
    [str(GOC / "dong-goi" / "chay.py")],
    pathex=[str(GOC)],
    datas=[
        (str(GOC / "qlkt" / "db" / "schema.sql"), "qlkt/db"),
        (str(GOC / "mau" / "to_trinh.docx"), "mau"),
        (str(GOC / "mau" / "quyet_dinh.docx"), "mau"),
    ],
    hiddenimports=["sqlcipher3", "sqlcipher3.dbapi2"],
    excludes=BO_QUA,
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="QLKT",
    console=False,
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="QLKT", upx=False)
