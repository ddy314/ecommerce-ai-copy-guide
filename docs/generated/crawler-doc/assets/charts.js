(function() {
  var style = getComputedStyle(document.documentElement);
  var accent = style.getPropertyValue('--accent').trim();
  var accent2 = style.getPropertyValue('--accent2').trim();
  var ink = style.getPropertyValue('--ink').trim();
  var muted = style.getPropertyValue('--muted').trim();
  var rule = style.getPropertyValue('--rule').trim();
  var bg2 = style.getPropertyValue('--bg2').trim();

  // --- Chart 1: Platform Anti-Crawling Comparison (Radar) ---
  var chart1 = echarts.init(document.getElementById('chart-radar-compare'), null, { renderer: 'svg' });
  chart1.setOption({
    title: {
      text: '苏宁易购 vs 京东 反爬强度对比',
      left: 'center',
      top: 10,
      textStyle: { color: ink, fontSize: 16, fontWeight: 600 }
    },
    tooltip: {
      trigger: 'item',
      appendToBody: true
    },
    legend: {
      bottom: 5,
      textStyle: { color: muted, fontSize: 13 },
      data: ['苏宁易购', '京东 (JD.com)']
    },
    radar: {
      indicator: [
        { name: '登录态要求', max: 10 },
        { name: '设备指纹检测', max: 10 },
        { name: '动态JS渲染', max: 10 },
        { name: '价格加密', max: 10 },
        { name: 'API签名验证', max: 10 },
        { name: 'IP风控强度', max: 10 }
      ],
      center: ['50%', '52%'],
      radius: '62%',
      axisName: {
        color: ink,
        fontSize: 13,
        fontWeight: 600
      },
      splitLine: { lineStyle: { color: rule } },
      splitArea: { areaStyle: { color: [bg2, 'transparent'] } },
      axisLine: { lineStyle: { color: rule } }
    },
    series: [{
      type: 'radar',
      animation: false,
      data: [
        {
          value: [2, 1, 3, 1, 1, 3],
          name: '苏宁易购',
          areaStyle: { color: accent + '33' },
          lineStyle: { color: accent, width: 2 },
          itemStyle: { color: accent }
        },
        {
          value: [9, 9, 8, 9, 8, 9],
          name: '京东 (JD.com)',
          areaStyle: { color: accent2 + '33' },
          lineStyle: { color: accent2, width: 2 },
          itemStyle: { color: accent2 }
        }
      ]
    }]
  });
  window.addEventListener('resize', function() { chart1.resize(); });

  // --- Chart 2: Category Distribution (Bar) ---
  var chart2 = echarts.init(document.getElementById('chart-category-bar'), null, { renderer: 'svg' });
  chart2.setOption({
    title: {
      text: '9大品类采集商品数量分布',
      left: 'center',
      top: 10,
      textStyle: { color: ink, fontSize: 16, fontWeight: 600 }
    },
    tooltip: {
      trigger: 'axis',
      appendToBody: true,
      axisPointer: { type: 'shadow' }
    },
    grid: { left: '8%', right: '8%', bottom: '12%', top: '18%', containLabel: true },
    xAxis: {
      type: 'category',
      data: ['数码电子', '生活用品', '家居家电', '办公家具', '服装服饰', '户外运动', '化妆品', '母婴用品', '宠物用品'],
      axisLabel: { color: muted, fontSize: 11, rotate: 25 },
      axisLine: { lineStyle: { color: rule } },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      name: '商品数量',
      nameTextStyle: { color: muted, fontSize: 12 },
      axisLabel: { color: muted, fontSize: 12 },
      splitLine: { lineStyle: { color: rule } },
      axisLine: { show: false }
    },
    series: [{
      type: 'bar',
      animation: false,
      data: [320, 180, 150, 280, 120, 200, 250, 280, 220],
      itemStyle: {
        color: function(params) {
          var colors = [accent, accent2, accent, accent2, accent, accent2, accent, accent2, accent];
          return colors[params.dataIndex];
        },
        borderRadius: [4, 4, 0, 0]
      },
      barWidth: '55%',
      label: {
        show: true,
        position: 'top',
        color: ink,
        fontSize: 12,
        fontWeight: 600
      }
    }]
  });
  window.addEventListener('resize', function() { chart2.resize(); });

  // --- Chart 3: JD Strategy Failure (Horizontal Bar) ---
  var chart3 = echarts.init(document.getElementById('chart-strategy-fail'), null, { renderer: 'svg' });
  chart3.setOption({
    title: {
      text: '京东反爬突破策略效果评估 (有效率%)',
      left: 'center',
      top: 10,
      textStyle: { color: ink, fontSize: 16, fontWeight: 600 }
    },
    tooltip: {
      trigger: 'axis',
      appendToBody: true,
      axisPointer: { type: 'shadow' },
      formatter: function(params) {
        var p = params[0];
        return p.name + ': 有效率 ' + p.value + '%';
      }
    },
    grid: { left: '5%', right: '12%', bottom: '5%', top: '18%', containLabel: true },
    xAxis: {
      type: 'value',
      max: 100,
      axisLabel: { color: muted, fontSize: 12, formatter: '{value}%' },
      splitLine: { lineStyle: { color: rule } },
      axisLine: { show: false }
    },
    yAxis: {
      type: 'category',
      data: [
        '策略7: Playwright stealth',
        '策略6: undetected-chromedriver',
        '策略5: 代理IP池',
        '策略4: 修改WebDriver特征',
        '策略3: Selenium模拟浏览器',
        '策略2: 携带Cookie',
        '策略1: 直接requests请求'
      ],
      axisLabel: { color: ink, fontSize: 12 },
      axisLine: { lineStyle: { color: rule } },
      axisTick: { show: false }
    },
    series: [{
      type: 'bar',
      animation: false,
      data: [
        { value: 25, itemStyle: { color: accent2 + '88' } },
        { value: 35, itemStyle: { color: accent2 } },
        { value: 15, itemStyle: { color: accent + '88' } },
        { value: 20, itemStyle: { color: accent + 'aa' } },
        { value: 15, itemStyle: { color: accent } },
        { value: 10, itemStyle: { color: accent + 'cc' } },
        { value: 5, itemStyle: { color: accent } }
      ],
      barWidth: '55%',
      label: {
        show: true,
        position: 'right',
        color: ink,
        fontSize: 12,
        fontWeight: 600,
        formatter: '{c}%'
      }
    }]
  });
  window.addEventListener('resize', function() { chart3.resize(); });

})();
