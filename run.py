# -*- coding: utf-8 -*-
from app import create_app

app = create_app()

if __name__ == '__main__':
    from config import ADMIN_USER
    print("=" * 50)
    print("  短视频热门数据采集与可视化平台")
    print("  访问地址: http://127.0.0.1:5000")
    print(f"  管理员账号: {ADMIN_USER['username']}（密码见 .env）")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)
