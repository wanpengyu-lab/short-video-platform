// ===== 短视频热门数据采集与可视化平台 - 前端交互脚本 =====

document.addEventListener('DOMContentLoaded', function () {

    // 1. 消息提示 4 秒后自动淡出
    const alerts = document.querySelectorAll('.alert-modern');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            alert.style.transition = 'opacity .4s, transform .4s';
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-8px)';
            setTimeout(function () { alert.remove(); }, 400);
        }, 4000);
    });

    // 2. 统计数字滚动动画
    const numbers = document.querySelectorAll('.stat-value');
    numbers.forEach(function (el) {
        const raw = el.textContent.trim();
        // 提取前导数字部分（含千分位）
        const match = raw.match(/^([\d,.]+)/);
        if (!match) return;

        const numText = match[1];
        const target = parseFloat(numText.replace(/,/g, ''));
        if (isNaN(target) || target === 0) return;

        const suffix = raw.slice(numText.length); // 单位等剩余内容
        const useComma = numText.includes(',');
        const duration = 900;
        const start = performance.now();

        el.textContent = '0' + suffix;

        function tick(now) {
            const p = Math.min((now - start) / duration, 1);
            const eased = 1 - Math.pow(1 - p, 3);
            let val = Math.round(target * eased);
            el.textContent = (useComma ? val.toLocaleString('en-US') : val) + suffix;
            if (p < 1) requestAnimationFrame(tick);
        }
        requestAnimationFrame(tick);
    });

    // 3. 查询表单提交时给按钮加加载态
    const forms = document.querySelectorAll('form[method="GET"]');
    forms.forEach(function (f) {
        f.addEventListener('submit', function () {
            const btn = f.querySelector('button[type="submit"]');
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 查询中';
                setTimeout(function () {
                    btn.disabled = false;
                    btn.innerHTML = '<i class="bi bi-search"></i> 查询';
                }, 2500);
            }
        });
    });
});

// 立即执行采集：给出长耗时提示（Selenium 采集需数分钟）
function markRunning(btn, taskName) {
    setTimeout(function () {
        const msg = document.createElement('div');
        msg.className = 'alert-modern alert-info';
        msg.innerHTML = '<i class="bi bi-hourglass-split"></i> 任务「' + taskName +
            '」正在执行采集，Selenium 逐个抓取详情页需数分钟，请耐心等待页面刷新。';
        const holder = document.querySelector('.content-pad') || document.body;
        holder.insertBefore(msg, holder.firstChild);
        setTimeout(function () { msg.remove(); }, 12000);
    }, 100);
}
