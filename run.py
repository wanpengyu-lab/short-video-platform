# -*- coding: utf-8 -*-
from app import create_app

app = create_app()

if __name__ == '__main__':
    from config import ADMIN_USER, FLASK_CONFIG, SERVER_CONFIG

    host = SERVER_CONFIG['host']
    port = SERVER_CONFIG['port']
    debug = FLASK_CONFIG['DEBUG']

    print("=" * 50)
    print("  短视频热门数据采集与可视化平台")
    print(f"  访问地址: http://{host}:{port}")
    print(f"  管理员账号: {ADMIN_USER['username']}（密码见 .env）")
    print(f"  调试模式: {'开启' if debug else '关闭'}")
    if host == '0.0.0.0':
        print("  ⚠️ 当前监听所有网卡，局域网内其他设备可访问本服务")
    print("=" * 50)
    app.run(host=host, port=port, debug=debug)
