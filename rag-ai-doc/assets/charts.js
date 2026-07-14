/* assets/charts.js — ECharts visualizations for RAG & AI layer documentation */
(function () {
  var style = getComputedStyle(document.documentElement);
  var accent = style.getPropertyValue('--accent').trim();
  var accent2 = style.getPropertyValue('--accent2').trim();
  var ink = style.getPropertyValue('--ink').trim();
  var muted = style.getPropertyValue('--muted').trim();
  var rule = style.getPropertyValue('--rule').trim();
  var bg2 = style.getPropertyValue('--bg2').trim();

  // ---- Chart 1: 检索层级评分权重对比 ----
  var chart1El = document.getElementById('chart-retrieval-weight');
  if (chart1El) {
    var chart1 = echarts.init(chart1El, null, { renderer: 'svg' });
    chart1.setOption({
      animation: false,
      title: { text: '', left: 'center' },
      tooltip: { trigger: 'axis', appendToBody: true, axisPointer: { type: 'shadow' } },
      legend: { data: ['关键词长度倍率', '评分加成'], top: 4, textStyle: { color: muted } },
      grid: { left: '3%', right: '5%', bottom: '3%', top: 52, containLabel: true },
      xAxis: {
        type: 'category',
        data: ['精确商品名匹配', '核心关键词+分类', '通用关键词+分类', '全局搜索'],
        axisLabel: { color: ink, fontSize: 11, interval: 0, rotate: 0 },
        axisLine: { lineStyle: { color: rule } },
      },
      yAxis: {
        type: 'value',
        name: '权重倍率',
        nameTextStyle: { color: muted },
        axisLabel: { color: muted },
        splitLine: { lineStyle: { color: rule } },
      },
      series: [
        {
          name: '关键词长度倍率',
          type: 'bar',
          data: [10.0, 5.0, 2.0, 2.0],
          itemStyle: { color: accent, borderRadius: [4, 4, 0, 0] },
          barWidth: '30%',
        },
        {
          name: '评分加成',
          type: 'bar',
          data: [0.5, 0.1, 0.1, 0.1],
          itemStyle: { color: accent2, borderRadius: [4, 4, 0, 0] },
          barWidth: '30%',
        },
      ],
    });
    window.addEventListener('resize', function () { chart1.resize(); });
  }

  // ---- Chart 2: 各问题类型触发关键词数量 ----
  var chart2El = document.getElementById('chart-qtype-keywords');
  if (chart2El) {
    var chart2 = echarts.init(chart2El, null, { renderer: 'svg' });
    chart2.setOption({
      animation: false,
      tooltip: { trigger: 'axis', appendToBody: true, axisPointer: { type: 'shadow' } },
      grid: { left: '3%', right: '8%', bottom: '3%', top: 16, containLabel: true },
      xAxis: {
        type: 'value',
        axisLabel: { color: muted },
        splitLine: { lineStyle: { color: rule } },
      },
      yAxis: {
        type: 'category',
        data: ['recommend 推荐', 'price 价格', 'brand 品牌', 'review 评价', 'compare 比较', 'size 尺寸', 'function 功能', 'after_sale 售后'],
        axisLabel: { color: ink, fontSize: 11 },
        axisLine: { lineStyle: { color: rule } },
      },
      series: [
        {
          type: 'bar',
          data: [7, 9, 6, 8, 6, 10, 14, 7],
          itemStyle: {
            color: function (p) { return p.dataIndex % 2 === 0 ? accent : accent2; },
            borderRadius: [0, 4, 4, 0],
          },
          barWidth: '55%',
          label: { show: true, position: 'right', color: ink, fontSize: 11 },
        },
      ],
    });
    window.addEventListener('resize', function () { chart2.resize(); });
  }

  // ---- Chart 3: 品牌知识库分类分布 ----
  var chart3El = document.getElementById('chart-brand-dist');
  if (chart3El) {
    var chart3 = echarts.init(chart3El, null, { renderer: 'svg' });
    chart3.setOption({
      animation: false,
      tooltip: { trigger: 'item', appendToBody: true },
      legend: {
        orient: 'vertical',
        right: 8,
        top: 'center',
        textStyle: { color: muted, fontSize: 12 },
      },
      series: [
        {
          type: 'pie',
          radius: ['42%', '70%'],
          center: ['38%', '50%'],
          avoidLabelOverlap: true,
          itemStyle: { borderColor: bg2, borderWidth: 2 },
          label: { show: true, color: ink, fontSize: 11, formatter: '{b}\n{d}%' },
          labelLine: { length: 12, length2: 10 },
          data: [
            { value: 11, name: '化妆品品牌', itemStyle: { color: accent } },
            { value: 8, name: '母婴品牌', itemStyle: { color: accent2 } },
            { value: 6, name: '数码品牌', itemStyle: { color: '#c8893f' } },
            { value: 5, name: '宠物品牌', itemStyle: { color: '#a67c52' } },
            { value: 3, name: '家居家电品牌', itemStyle: { color: '#b87333' } },
            { value: 2, name: '家具品牌', itemStyle: { color: '#d4a373' } },
            { value: 2, name: '运动品牌', itemStyle: { color: '#8b6f47' } },
          ],
        },
      ],
    });
    window.addEventListener('resize', function () { chart3.resize(); });
  }

  // ---- Chart 4: 相似度评分构成 ----
  var chart4El = document.getElementById('chart-similarity');
  if (chart4El) {
    var chart4 = echarts.init(chart4El, null, { renderer: 'svg' });
    chart4.setOption({
      animation: false,
      tooltip: { trigger: 'axis', appendToBody: true, axisPointer: { type: 'shadow' } },
      grid: { left: '3%', right: '5%', bottom: '3%', top: 24, containLabel: true },
      xAxis: {
        type: 'category',
        data: ['关键词命中内容', '关键词命中entry关键词', '完整问题命中内容', '关键词命中标题'],
        axisLabel: { color: ink, fontSize: 11, interval: 0 },
        axisLine: { lineStyle: { color: rule } },
      },
      yAxis: {
        type: 'value',
        name: '加分值',
        nameTextStyle: { color: muted },
        axisLabel: { color: muted },
        splitLine: { lineStyle: { color: rule } },
      },
      series: [
        {
          type: 'bar',
          data: [0.3, 0.5, 0.5, 0.2],
          itemStyle: { color: accent, borderRadius: [4, 4, 0, 0] },
          barWidth: '45%',
          label: { show: true, position: 'top', color: ink, fontSize: 12 },
        },
      ],
    });
    window.addEventListener('resize', function () { chart4.resize(); });
  }
})();
