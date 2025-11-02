# resource_monitor.py
import psutil
import logging
from datetime import datetime

def check_resources():
    """リソース使用状況を確認"""
    
    # メモリ
    memory = psutil.virtual_memory()
    memory_percent = memory.percent
    memory_available_gb = memory.available / (1024**3)
    
    # CPU
    cpu_percent = psutil.cpu_percent(interval=1)
    
    # ディスク
    disk = psutil.disk_usage('/')
    disk_percent = disk.percent
    
    # ネットワーク
    net = psutil.net_io_counters()
    
    log_message = f"""
    ━━━━━━━━━━━━━━━━━━━━━━━━
    📊 リソース使用状況
    時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    ━━━━━━━━━━━━━━━━━━━━━━━━
    💾 メモリ使用率: {memory_percent:.1f}%
       利用可能: {memory_available_gb:.2f}GB
    
    🖥️  CPU使用率: {cpu_percent:.1f}%
    
    💿 ディスク使用率: {disk_percent:.1f}%
    
    🌐 ネットワーク:
       送信: {net.bytes_sent / (1024**3):.2f}GB
       受信: {net.bytes_recv / (1024**3):.2f}GB
    ━━━━━━━━━━━━━━━━━━━━━━━━
    """
    
    print(log_message)
    
    # メモリが90%超えたら警告
    if memory_percent > 90:
        print("⚠️  警告: メモリ使用率が90%を超えています！")
    
    # CPUが80%超えたら警告
    if cpu_percent > 80:
        print("⚠️  警告: CPU使用率が80%を超えています！")
    
    return {
        'memory_percent': memory_percent,
        'memory_available_gb': memory_available_gb,
        'cpu_percent': cpu_percent,
        'disk_percent': disk_percent
    }

if __name__ == "__main__":
    check_resources()
