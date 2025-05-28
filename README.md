# Testcase App
Ứng dụng gửi file JSON kiểm thử đến Linux qua SCP/SFTP, dùng GUI.
- Gửi đến /root/config, nhận kết quả từ /root/result.
- Dùng SSH qua LAN (192.168.88.1) với mật khẩu.
- Phát triển trên Ubuntu, build .exe cho Windows 11.

## Cài đặt
1. Chạy \`scripts/setup_env.sh\` để cài thư viện.
2. Cấu hình \`config/settings.ini\` với IP, username.
3. Chạy \`python3 src/main.py\` trên Ubuntu.
4. Chạy \`scripts/build_exe.sh\` để build .exe.

## Tổng quan hệ thống
Hệ thống xử lý tuần tự, gửi từng file JSON kiểm thử đến `/root/config` trên thiết bị Linux (192.168.88.1), chờ kết quả từ `/root/result`, hiển thị trên GUI, và lưu lịch sử vào SQLite. Xem chi tiết trong tài liệu trước.

## Yêu cầu
- Python 3.8+
- Ubuntu (phát triển), Windows 11 (chạy)
