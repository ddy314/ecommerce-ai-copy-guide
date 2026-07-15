// assets/charts.js
// 电商 AI 智能导购系统 · 收入检测面板与订单状态可视化
(function () {
  var style = getComputedStyle(document.documentElement);
  var accent = style.getPropertyValue('--accent').trim();
  var accent2 = style.getPropertyValue('--accent2').trim();
  var ink = style.getPropertyValue('--ink').trim();
  var muted = style.getPropertyValue('--muted').trim();
  var rule = style.getPropertyValue('--rule').trim();
  var bg2 = style.getPropertyValue('--bg2').trim();
  var green = style.getPropertyValue('--green').trim();
  var yellow = style.getPropertyValue('--yellow').trim();

  // ============================================================
  // Chart 1: 近 7 日收入趋势（折线 + 面积）
  // ============================================================
  var chartRevenue = document.getElementById('chart-revenue');
  if (chartRevenue && typeof echarts !== 'undefined') {
    var revenueChart = echarts.init(chartRevenue, null, { renderer: 'svg' });

    var days = ['07-08', '07-09', '07-10', '07-11', '07-12', '07-13', '07-14'];
    var revenueData = [12800, 15600, 14200, 18900, 22300, 20100, 24800];
    var orderCountData = [42, 55, 48, 67, 78, 71, 86];

    revenueChart.setOption({
      animation: false,
      tooltip: {
        trigger: 'axis',
        appendToBody: true,
        backgroundColor: bg2,
        borderColor: rule,
        textStyle: { color: ink, fontFamily: 'sans-serif' }
      },
      legend: {
        data: ['营收(元)', '订单数'],
        top: 0,
        right: 10,
        textStyle: { color: muted, fontSize: 12 }
      },
      grid: { top: 50, left: 60, right: 60, bottom: 40 },
      xAxis: {
        type: 'category',
        data: days,
        axisLine: { lineStyle: { color: rule } },
        axisLabel: { color: muted, fontSize: 12 }
      },
      yAxis: [
        {
          type: 'value',
          name: '营收(元)',
          nameTextStyle: { color: muted, fontSize: 12 },
          axisLine: { show: false },
          splitLine: { lineStyle: { color: rule, type: 'dashed' } },
          axisLabel: { color: muted, fontSize: 12 }
        },
        {
          type: 'value',
          name: '订单数',
          nameTextStyle: { color: muted, fontSize: 12 },
          axisLine: { show: false },
          splitLine: { show: false },
          axisLabel: { color: muted, fontSize: 12 }
        }
      ],
      series: [
        {
          name: '营收(元)',
          type: 'line',
          smooth: true,
          symbol: 'circle',
          symbolSize: 8,
          data: revenueData,
          itemStyle: { color: accent },
          lineStyle: { color: accent, width: 3 },
          areaStyle: {
            color: {
              type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: accent + '55' },
                { offset: 1, color: accent + '05' }
              ]
            }
          }
        },
        {
          name: '订单数',
          type: 'bar',
          yAxisIndex: 1,
          data: orderCountData,
          barWidth: 18,
          itemStyle: {
            color: accent2 + '66',
            borderRadius: [4, 4, 0, 0]
          }
        }
      ]
    });

    window.addEventListener('resize', function () { revenueChart.resize(); });
  }

  // ============================================================
  // Chart 2: 订单状态分布（环形饼图）
  // ============================================================
  var chartStatus = document.getElementById('chart-order-status');
  if (chartStatus && typeof echarts !== 'undefined') {
    var statusChart = echarts.init(chartStatus, null, { renderer: 'svg' });

    statusChart.setOption({
      animation: false,
      tooltip: {
        trigger: 'item',
        appendToBody: true,
        backgroundColor: bg2,
        borderColor: rule,
        textStyle: { color: ink, fontFamily: 'sans-serif' },
        formatter: '{b}: {c} 单 ({d}%)'
      },
      legend: {
        orient: 'vertical',
        right: 10,
        top: 'center',
        textStyle: { color: muted, fontSize: 13 },
        itemGap: 14
      },
      color: [accent, accent2, green, yellow, muted],
      series: [
        {
          name: '订单状态',
          type: 'pie',
          radius: ['42%', '68%'],
          center: ['38%', '50%'],
          avoidLabelOverlap: true,
          itemStyle: {
            borderColor: bg2,
            borderWidth: 3
          },
          label: {
            show: true,
            color: ink,
            fontSize: 13,
            formatter: '{b}\n{c}单'
          },
          labelLine: { lineStyle: { color: rule } },
          data: [
            { value: 186, name: '已完成' },
            { value: 94, name: '已支付' },
            { value: 67, name: '已发货' },
            { value: 38, name: '待支付' },
            { value: 15, name: '已取消' }
          ]
        }
      ]
    });

    window.addEventListener('resize', function () { statusChart.resize(); });
  }

  // ============================================================
  // Mermaid 初始化
  // ============================================================
  if (typeof mermaid !== 'undefined') {
    mermaid.initialize({
      startOnLoad: true,
      theme: 'neutral',
      securityLevel: 'loose',
      themeVariables: {
        primaryColor: '#fff3e6',
        primaryTextColor: '#211a14',
        primaryBorderColor: '#d95f2d',
        lineColor: '#82391f',
        secondaryColor: '#f7f1e7',
        tertiaryColor: '#fff8ec',
        fontFamily: 'sans-serif',
        fontSize: '14px'
      }
    });
  }
})();
