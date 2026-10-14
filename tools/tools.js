// tools/tools.js  —  工具站核心引擎（ESM，浏览器与 Node 共用）
// 约定：每个 compute 函数返回统一结果对象：
//   { kind:"value", primary, unit, rows:[[label,value],...], note }
//   { kind:"table", headers:[...], rows:[[...]], note }

function fmt(n, d = 2) {
  if (!isFinite(n)) return "—";
  return Number(n.toFixed(d)).toLocaleString("zh-CN", { maximumFractionDigits: d });
}
function pct(x) { return fmt(x * 100, 2) + "%"; }

// 日期工具（浏览器/Node 通用）
function parseDate(s) {
  if (!s) return null;
  const d = new Date(s);
  return isNaN(d.getTime()) ? null : d;
}
function addDays(date, n) {
  const d = new Date(date);
  d.setDate(d.getDate() + n);
  return d;
}
function fmtDate(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
function daysBetween(a, b) {
  return Math.round((b - a) / 86400000);
}

// 中国综合所得月度税率表（简化）
function taxTable(taxable) {
  const brackets = [
    [3000, 0.03, 0], [12000, 0.1, 210], [25000, 0.2, 1410],
    [35000, 0.25, 2660], [55000, 0.3, 4410], [80000, 0.35, 7160], [Infinity, 0.45, 15160],
  ];
  for (const [cap, rate, deduct] of brackets) {
    if (taxable <= cap) return Math.max(0, taxable * rate - deduct);
  }
  return 0;
}

const COMPUTE = {
  // ---------------- 理财 ----------------
  mortgage(i) {
    const P = i.amount * 10000;
    const r = i.rate / 100 / 12;
    const n = Math.round(i.years * 12);
    if (i.method === "等额本金") {
      const first = P / n + P * r;
      const decrease = (P * r) / n;
      const totalInterest = (P * r * (n + 1)) / 2;
      return {
        kind: "value",
        primary: fmt(first), unit: "元/月(首月)",
        rows: [["首月还款", fmt(first) + " 元"], ["每月递减", fmt(decrease) + " 元"], ["总利息", fmt(totalInterest) + " 元"], ["还款总额", fmt(P + totalInterest) + " 元"]],
      };
    }
    const pow = Math.pow(1 + r, n);
    const monthly = (P * r * pow) / (pow - 1);
    const total = monthly * n;
    return {
      kind: "value",
      primary: fmt(monthly), unit: "元/月",
      rows: [["每月还款", fmt(monthly) + " 元"], ["总利息", fmt(total - P) + " 元"], ["还款总额", fmt(total) + " 元"]],
    };
  },
  compound(i) {
    const r = i.rate / 100 / i.freq;
    const t = i.freq * i.years;
    const A = i.principal * Math.pow(1 + r, t);
    return { kind: "value", primary: fmt(A), unit: "元", rows: [["到期本息", fmt(A) + " 元"], ["总收益", fmt(A - i.principal) + " 元"]] };
  },
  annualized(i) {
    const r = Math.pow(i.end / i.start, 1 / i.years) - 1;
    return { kind: "value", primary: pct(r), unit: "", rows: [["年化收益率", pct(r)], ["总收益", fmt(i.end - i.start) + " 元"]] };
  },
  sip(i) {
    const r = i.rate / 100 / 12;
    const n = i.months;
    const FV = r === 0 ? i.pmt * n : i.pmt * ((Math.pow(1 + r, n) - 1) / r);
    return { kind: "value", primary: fmt(FV), unit: "元", rows: [["到期总额", fmt(FV) + " 元"], ["本金合计", fmt(i.pmt * n) + " 元"], ["收益", fmt(FV - i.pmt * n) + " 元"]] };
  },
  tax_personal(i) {
    const taxable = Math.max(0, i.salary - 5000 - i.insurance - i.special);
    const tax = taxTable(taxable);
    const after = i.salary - i.insurance - tax;
    return { kind: "value", primary: fmt(after), unit: "元/月", rows: [["应纳税所得额", fmt(taxable) + " 元"], ["预扣个税", fmt(tax) + " 元"], ["税后到手", fmt(after) + " 元"]] };
  },
  deposit(i) {
    const interest = i.principal * (i.rate / 100) * i.years;
    return { kind: "value", primary: fmt(i.principal + interest), unit: "元", rows: [["利息", fmt(interest) + " 元"], ["到期本息", fmt(i.principal + interest) + " 元"]] };
  },
  year_end_bonus(i) {
    const m = i.bonus / 12;
    const tax = taxTable(m) * 12; // 单独计税：以月税率表套用
    return { kind: "value", primary: fmt(i.bonus - tax), unit: "元", rows: [["应缴个税", fmt(tax) + " 元"], ["税后奖金", fmt(i.bonus - tax) + " 元"]] };
  },
  social_insurance(i) {
    const rates = { 一般城市: { p: 0.225, u: 0.36 }, 上海: { p: 0.175, u: 0.325 }, 深圳: { p: 0.155, u: 0.245 } };
    const key = Object.keys(rates).find((k) => i.city.includes(k)) || "一般城市";
    const r = rates[key];
    return {
      kind: "value", primary: fmt(i.base * r.p), unit: "元/月(个人)",
      rows: [["个人缴纳", fmt(i.base * r.p) + " 元"], ["单位缴纳(约)", fmt(i.base * r.u) + " 元"], ["个人合计比例", pct(r.p)]],
    };
  },

  // ---------------- 装修 / 居家 ----------------
  renovation_budget(i) {
    const price = parseFloat(i.tier.match(/\((\d+)/)[1]);
    const total = i.area * price;
    return { kind: "value", primary: fmt(total), unit: "元", rows: [["面积", i.area + " ㎡"], ["单价", price + " 元/㎡"], ["总预算", fmt(total) + " 元"]] };
  },
  tiles(i) {
    const single = (i.tileW * i.tileH) / 10000;
    const count = Math.ceil((i.wallArea / single) * (1 + i.waste / 100));
    return { kind: "value", primary: count + "", unit: "块", rows: [["单砖面积", fmt(single, 3) + " ㎡"], ["含损耗块数", count + " 块"]] };
  },
  paint(i) {
    const L = (i.area * i.coats) / i.coverage * 1.1;
    return { kind: "value", primary: fmt(L, 1), unit: "升", rows: [["理论用量", fmt((i.area * i.coats) / i.coverage, 1) + " 升"], ["含损耗", fmt(L, 1) + " 升"]] };
  },
  curtain(i) {
    const w = i.width * i.ratio;
    return { kind: "value", primary: fmt(w), unit: "cm(布宽)", rows: [["布料宽度", fmt(w) + " cm"], ["建议", "两侧各加 10~20cm 富余"], ["窗帘高度", i.height + " cm"]] };
  },
  renovation_schedule(i) {
    const base = { 简单: 30, 中等: 50, 复杂: 75 }[i.complex] || 50;
    const days = Math.round(base + i.area * 0.2);
    return { kind: "value", primary: days + "", unit: "天", rows: [["建议工期", days + " 天"], ["说明", "含水电/泥木/油漆/安装"]] };
  },
  grout(i) {
    const tileArea = (i.tileW * i.tileH) / 10000;
    const perM2 = 1 / tileArea;
    const jointLen = (i.tileW + i.tileH) / 100; // m
    const jointW = 0.002; // 2mm 默认缝宽
    const kgPerM2 = perM2 * jointLen * (i.depth / 1000) * jointW * 1800;
    return { kind: "value", primary: fmt(kgPerM2 * i.area, 2), unit: "kg", rows: [["每㎡约", fmt(kgPerM2, 3) + " kg"], ["总面积", i.area + " ㎡"]] };
  },
  floor_tiles(i) {
    const single = (i.tileW * i.tileH) / 10000;
    const count = Math.ceil((i.area / single) * (1 + i.waste / 100));
    return { kind: "value", primary: count + "", unit: "块", rows: [["单砖面积", fmt(single, 3) + " ㎡"], ["含损耗块数", count + " 块"]] };
  },
  utility(i) {
    const e = i.elecKwh * i.elecPrice, w = i.waterT * i.waterPrice;
    return { kind: "value", primary: fmt(e + w, 1), unit: "元/月", rows: [["电费", fmt(e, 1) + " 元"], ["水费", fmt(w, 1) + " 元"], ["合计", fmt(e + w, 1) + " 元"]] };
  },

  // ---------------- 母婴 / 健康 ----------------
  due_date(i) {
    const lmp = parseDate(i.lmp);
    if (!lmp) return { kind: "value", primary: "请选择日期", rows: [] };
    const due = addDays(lmp, 280);
    const week = Math.max(0, Math.floor(daysBetween(lmp, new Date()) / 7));
    return { kind: "value", primary: fmtDate(due), unit: "预产期", rows: [["预产期", fmtDate(due)], ["当前约", week + " 周"], ["末次月经", fmtDate(lmp)]] };
  },
  pregnancy_week(i) {
    const lmp = parseDate(i.lmp);
    if (!lmp) return { kind: "value", primary: "请选择日期", rows: [] };
    const week = Math.max(0, Math.floor(daysBetween(lmp, new Date()) / 7));
    return { kind: "value", primary: week + "", unit: "周", rows: [["当前孕周", week + " 周"], ["末次月经", fmtDate(lmp)]] };
  },
  ovulation(i) {
    const lmp = parseDate(i.lmp);
    if (!lmp) return { kind: "value", primary: "请选择日期", rows: [] };
    const cycleLen = i.cycle;
    const next = addDays(lmp, cycleLen);
    const ovu = addDays(next, -14);
    const start = addDays(ovu, -5), end = addDays(ovu, 1);
    return { kind: "value", primary: fmtDate(ovu), unit: "排卵日", rows: [["排卵日", fmtDate(ovu)], ["易孕窗口", fmtDate(start) + " ~ " + fmtDate(end)]] };
  },
  baby_growth(i) {
    // WHO 0-5岁 男/女 中位数(近似) + 1SD，按关键月龄线性插值
    const table = {
      男: { w: [[0, 3.3, 0.4], [6, 7.9, 0.9], [12, 9.6, 1.0], [24, 12.2, 1.1], [36, 14.3, 1.2], [60, 18.3, 2.1]], h: [[0, 49.9, 1.9], [6, 67.6, 2.3], [12, 75.7, 2.9], [24, 87.1, 3.5], [36, 96.1, 3.9], [60, 110.0, 4.6]] },
      女: { w: [[0, 3.2, 0.4], [6, 7.3, 0.8], [12, 8.9, 0.9], [24, 11.5, 1.1], [36, 13.9, 1.4], [60, 17.7, 2.1]], h: [[0, 49.1, 1.9], [6, 65.7, 2.3], [12, 74.0, 2.8], [24, 85.7, 3.4], [36, 95.1, 3.8], [60, 109.0, 4.5]] },
    }[i.sex] || {};
    const interp = (arr, x) => {
      const a = arr[0], b = arr[arr.length - 1];
      if (x <= a[0]) return [a[1], a[2]];
      if (x >= b[0]) return [b[1], b[2]];
      for (let k = 0; k < arr.length - 1; k++) {
        const [x0, m0, s0] = arr[k], [x1, m1, s1] = arr[k + 1];
        if (x >= x0 && x <= x1) {
          const t = (x - x0) / (x1 - x0);
          return [m0 + (m1 - m0) * t, s0 + (s1 - s0) * t];
        }
      }
      return [a[1], a[2]];
    };
    const [wm, ws] = interp(table.w, i.months);
    const [hm, hs] = interp(table.h, i.months);
    return {
      kind: "value", primary: fmt(wm, 1), unit: "kg",
      rows: [["体重中位数", fmt(wm, 1) + " kg (±" + fmt(ws, 1) + ")"], ["身高中位数", fmt(hm, 1) + " cm (±" + fmt(hs, 1) + ")"], ["月龄", i.months + " 月"]],
    };
  },
  vaccine(i) {
    const m = i.months;
    const rows = [
      ["出生", "卡介苗、乙肝疫苗(第1剂)"],
      ["1 月龄", "乙肝疫苗(第2剂)"],
      ["2 月龄", "脊灰灭活疫苗(第1剂)"],
      ["3 月龄", "脊灰(第2剂)、百白破(第1剂)"],
      ["4 月龄", "脊灰(第3剂)、百白破(第2剂)"],
      ["5 月龄", "百白破(第3剂)"],
      ["6 月龄", "乙肝疫苗(第3剂)、A群流脑(第1剂)"],
      ["8 月龄", "麻腮风(第1剂)、乙脑(减毒第1剂)"],
      ["12 月龄", "水痘(第1剂)、甲肝"],
      ["18 月龄", "百白破(第4剂)、麻腮风(第2剂)"],
      ["24 月龄", "乙脑(第2剂)、A群C群流脑(第1剂)"],
      ["36 月龄", "A群C群流脑(第2剂)"],
      ["48 月龄", "脊灰(第4剂)"],
      ["72 月龄", "白破(第1剂)"],
    ];
    const hit = rows.filter((r) => parseInt(r[0]) === m);
    const show = hit.length ? hit : rows.filter((r) => parseInt(r[0]) <= m).slice(-3);
    return { kind: "table", headers: ["月龄", "一类疫苗"], rows: show };
  },
  baby_food(i) {
    const m = i.months;
    let text = "暂以满 6 月龄为辅食起点";
    if (m < 6) text = "建议满 6 月龄前以母乳/配方奶为主";
    else if (m < 8) text = "铁强化米粉、菜泥、果泥、蛋黄泥";
    else if (m < 10) text = "增加肉泥、鱼泥、肝泥、碎菜";
    else if (m < 12) text = "软饭、烂面、手指食物、碎肉";
    else text = "过渡到家庭清淡饮食，少盐少糖";
    return { kind: "value", primary: text, unit: "", rows: [["建议", text]] };
  },
  preg_weight(i) {
    const range = i.preBmi < 18.5 ? [12.5, 18] : i.preBmi < 25 ? [11.5, 16] : i.preBmi < 30 ? [7, 11.5] : [5, 9];
    const frac = Math.min(1, i.week / 40);
    const cur = range[0] + (range[1] - range[0]) * frac;
    return { kind: "value", primary: fmt(cur, 1), unit: "kg(当前建议)", rows: [["全期建议增重", range[0] + "~" + range[1] + " kg"], ["当前孕周", i.week + " 周"]] };
  },
  bmi(i) {
    const h = i.heightCm / 100, b = i.weightKg / (h * h);
    const cat = b < 18.5 ? "偏瘦" : b < 24 ? "正常" : b < 28 ? "超重" : "肥胖";
    return { kind: "value", primary: fmt(b, 1), unit: "kg/m²", rows: [["BMI", fmt(b, 1)], ["分类", cat + " (" + (b < 18.5 ? "<18.5" : b < 24 ? "18.5–23.9" : b < 28 ? "24–27.9" : "≥28") + ")"]] };
  },
  bmr(i) {
    const base = 10 * i.weightKg + 6.25 * i.heightCm - 5 * i.age;
    const bmr = i.sex === "男" ? base + 5 : base - 161;
    return { kind: "value", primary: fmt(bmr), unit: "kcal/天", rows: [["基础代谢", fmt(bmr) + " kcal"], ["每日总消耗(轻活动×1.375)", fmt(bmr * 1.375) + " kcal"]] };
  },
  bodyfat(i) {
    const h = i.heightCm / 100, bmi = i.weightKg / (h * h);
    const g = i.sex === "男" ? 1 : 0;
    const bf = 1.2 * bmi + 0.23 * i.age - 10.8 * g - 5.4;
    return { kind: "value", primary: fmt(bf, 1), unit: "%", rows: [["估算体脂率", fmt(bf, 1) + " %"], ["BMI", fmt(bmi, 1)]] };
  },
  water(i) {
    const per = i.activity === "久坐" ? 30 : i.activity === "高强度" ? 40 : 35;
    const L = (i.weightKg * per) / 1000;
    return { kind: "value", primary: fmt(L, 2), unit: "L/天", rows: [["按 " + per + " mL/kg 计", fmt(L, 2) + " 升"]] };
  },
  calories_burn(i) {
    const met = parseFloat(i.activity.match(/\(([\d.]+)\)/)[1]);
    const kcal = (met * 3.5 * i.weightKg) / 200 * i.minutes;
    return { kind: "value", primary: fmt(kcal), unit: "kcal", rows: [["消耗热量", fmt(kcal) + " kcal"], ["MET", met + ""]] };
  },

  // ---------------- 饮食 ----------------
  food_calorie(i) {
    const data = [
      ["主食", "米饭(熟)", 116], ["主食", "馒头", 223], ["主食", "面条(熟)", 110], ["主食", "燕麦", 367],
      ["蛋白类", "鸡胸肉", 133], ["蛋白类", "鸡蛋", 144], ["蛋白类", "牛肉(瘦)", 125], ["蛋白类", "三文鱼", 208], ["蛋白类", "豆腐", 81],
      ["蔬菜", "西兰花", 34], ["蔬菜", "番茄", 18], ["蔬菜", "黄瓜", 15], ["蔬菜", "土豆", 77],
      ["水果", "苹果", 52], ["水果", "香蕉", 93], ["水果", "橙子", 47], ["水果", "西瓜", 30],
      ["零食", "巧克力", 546], ["零食", "薯片", 548], ["零食", "饼干", 433],
    ];
    const rows = i.query === "全部" ? data : data.filter((r) => r[0] === i.query);
    return { kind: "table", headers: ["类别", "食物", "热量(kcal/100g)"], rows: rows.map((r) => [r[0], r[1], r[2]]) };
  },
  protein(i) {
    const coef = parseFloat(i.goal.match(/\(([\d.]+)g/)[1]);
    const g = i.weightKg * coef;
    return { kind: "value", primary: fmt(g, 1), unit: "g/天", rows: [["系数", coef + " g/kg"], ["需求量", fmt(g, 1) + " g"]] };
  },
  sugar_replace(i) {
    const data = [
      ["饮品", "奶茶/含糖饮料", "无糖茶、气泡水、黑咖啡"],
      ["饮品", "果汁", "整颗水果(保留纤维)"],
      ["零食", "蛋糕饼干", "希腊酸奶+莓果"],
      ["零食", "糖果", "少量坚果、黑巧克力(>70%)"],
      ["主食", "白米饭面条", "杂粮饭、燕麦、红薯"],
      ["调味", "白糖/糖浆", "赤藓糖醇、少量蜂蜜"],
    ];
    const rows = i.query === "全部" ? data : data.filter((r) => r[0] === i.query);
    return { kind: "table", headers: ["类别", "高糖食物", "更优替换"], rows };
  },

  // ---------------- 出行 ----------------
  timezone(i) {
    const off = (s) => parseInt(s.match(/([+-]\d+)/)[1]);
    const diff = off(i.toTz) - off(i.fromTz);
    let h = (i.hour + diff) % 24;
    if (h < 0) h += 24;
    return { kind: "value", primary: h + "", unit: "时(目的地)", rows: [["时差", (diff >= 0 ? "+" : "") + diff + " 小时"], ["目的地当地", h + ":00"]] };
  },
  travel_budget(i) {
    const total = i.food * i.days + i.hotel * i.days + i.transport + i.ticket;
    const withBuffer = total * 1.1;
    return { kind: "value", primary: fmt(total), unit: "元", rows: [["餐饮", fmt(i.food * i.days) + " 元"], ["住宿", fmt(i.hotel * i.days) + " 元"], ["交通+门票", fmt(i.transport + i.ticket) + " 元"], ["含10%机动", fmt(withBuffer) + " 元"]] };
  },
  voltage(i) {
    const data = {
      美国: ["120V", "A/B 型"], 英国: ["230V", "G 型"], 欧盟: ["230V", "C/F 型"], 日本: ["100V", "A 型"],
      澳大利亚: ["230V", "I 型"], 中国: ["220V", "A/C 型"], 韩国: ["220V", "C/F 型"],
    };
    const [v, p] = data[i.query] || ["—", "—"];
    return { kind: "value", primary: v, unit: "", rows: [["电压", v], ["插头", p]] };
  },

  temperature(i) {
    const v = Number(i.value), from = i.from;
    const c = from === "°C" ? v : from === "°F" ? (v - 32) * 5 / 9 : v - 273.15;
    const f = c * 9 / 5 + 32, k = c + 273.15;
    return { kind: "value", primary: fmt(c, 1), unit: "°C", rows: [["摄氏度", fmt(c, 1) + " °C"], ["华氏度", fmt(f, 1) + " °F"], ["开尔文", fmt(k, 1) + " K"]] };
  },

  // ---------------- 教育 ----------------
  gpa(i) {
    const g = Math.max(0, (i.score - 50) / 10);
    return { kind: "value", primary: fmt(g, 1), unit: "/4.0", rows: [["4.0 制 GPA", fmt(g, 1)], ["百分制", i.score + " 分"]] };
  },
  score_grade(i) {
    const g = i.score >= 90 ? "优秀" : i.score >= 80 ? "良好" : i.score >= 60 ? "及格" : "不及格";
    return { kind: "value", primary: g, unit: "", rows: [["等级", g], ["分数", i.score + " 分"]] };
  },
  countdown(i) {
    const d = parseDate(i.exam);
    if (!d) return { kind: "value", primary: "请选择日期", rows: [] };
    const left = daysBetween(new Date(), d);
    return { kind: "value", primary: left + "", unit: "天", rows: [["距考试", (left >= 0 ? left : "已过期 " + -left) + " 天"], ["考试日", fmtDate(d)]] };
  },
  ielts_toefl(i) {
    const data = [["6.0", "60–78"], ["6.5", "79–93"], ["7.0", "94–101"], ["7.5", "102–109"], ["8.0", "110–114"]];
    if (i.query === "对照表") return { kind: "table", headers: ["雅思", "托福 iBT"], rows: data };
    const row = data.find((r) => i.query.includes(r[0]));
    return { kind: "value", primary: row ? row[1] : "—", unit: "托福", rows: [["雅思", i.query], ["托福 iBT", row ? row[1] : "—"]] };
  },

  // ---------------- 数码 ----------------
  px_print(i) {
    const cm = i.px / (i.dpi / 2.54);
    const inch = i.px / i.dpi;
    return { kind: "value", primary: fmt(cm, 2), unit: "cm", rows: [["厘米", fmt(cm, 2) + " cm"], ["英寸", fmt(inch, 2) + " in"]] };
  },
  resolution(i) {
    const data = [
      ["720p", "1280×720", "16:9", "92万"], ["FHD 1080p", "1920×1080", "16:9", "207万"],
      ["2K QHD", "2560×1440", "16:9", "369万"], ["4K UHD", "3840×2160", "16:9", "829万"],
    ];
    const rows = i.query === "全部" ? data : data.filter((r) => r[0] === i.query);
    return { kind: "table", headers: ["名称", "分辨率", "比例", "像素数"], rows };
  },

  // ---------------- 职场 ----------------
  hourly(i) {
    const h = i.monthly / (i.days * i.hours);
    return { kind: "value", primary: fmt(h, 1), unit: "元/时", rows: [["月薪", fmt(i.monthly) + " 元"], ["月工时", fmt(i.days * i.hours, 1) + " 小时"], ["时薪", fmt(h, 1) + " 元"]] };
  },
  overtime(i) {
    const m = parseFloat(i.mult.match(/([\d.]+)/)[1]);
    const pay = i.hourly * m * i.hours;
    return { kind: "value", primary: fmt(pay), unit: "元", rows: [["倍数", m + " 倍"], ["加班费", fmt(pay) + " 元"]] };
  },

  // ---------------- 政务 ----------------
  clothing_size(i) {
    const data = {
      男: { S: [92, 67], M: [96, 69], L: [100, 71], XL: [104, 73], XXL: [108, 75] },
      女: { S: [84, 62], M: [88, 66], L: [92, 70], XL: [96, 74], XXL: [100, 78] },
    };
    const [c, w] = data[i.sex][i.size] || [0, 0];
    return { kind: "value", primary: i.size, unit: "", rows: [["胸围", c + " cm"], ["腰围", w + " cm"]] };
  },
  retirement_age(i) {
    let age;
    if (i.sex === "男") age = 60 + Math.min(3, Math.max(0, i.birthYear - 1962));
    else if (i.sex.includes("工人")) age = 50 + Math.min(5, Math.max(0, i.birthYear - 1972));
    else age = 55 + Math.min(3, Math.max(0, i.birthYear - 1967));
    return { kind: "value", primary: age + "", unit: "岁", rows: [["建议退休年龄", age + " 岁"], ["出生年份", i.birthYear + " 年"]] };
  },
  maternity_leave(i) {
    const base = 98;
    const add = parseInt(i.provinceAdd) || 0;
    const hard = i.hard.includes("是") ? 15 : 0;
    const multi = parseInt(i.multi) || 0;
    const total = base + add + hard + multi;
    return { kind: "value", primary: total + "", unit: "天", rows: [["基础", base + " 天"], ["省增假", add + " 天"], ["难产/多胞胎", hard + multi + " 天"]] };
  },
  social_years(i) {
    const y = i.retireYear <= 2029 ? 15 : Math.min(20, 15 + (i.retireYear - 2029));
    return { kind: "value", primary: y + "", unit: "年", rows: [["最低缴费年限", y + " 年"], ["退休年份", i.retireYear + " 年"]] };
  },
  lawsuit(i) {
    const data = {
      "普通民事纠纷": "3 年", "借款/买卖": "3 年", "人身损害": "3 年",
      "国际货物买卖": "4 年", "不动产物权": "3 年(确权不受限)",
    };
    return { kind: "value", primary: data[i.query] || "3 年", unit: "", rows: [["纠纷类型", i.query], ["诉讼时效", data[i.query] || "3 年"]] };
  },
};

// 通用换算
function convert(config, value, fromName, toName) {
  const units = config.units;
  const f = units.find((u) => u.name === fromName);
  const t = units.find((u) => u.name === toName);
  if (!f || !t || !isFinite(value)) return null;
  return (value * f.factor) / t.factor;
}

// 对外统一入口（供测试与 DOM 共用）
export function computeTool(config, inputs) {
  if (config.type === "converter") {
    const r = convert(config, inputs.value, inputs.from, inputs.to);
    if (r === null) return { kind: "value", primary: "—", unit: inputs.to || "", rows: [] };
    return { kind: "value", primary: fmt(r, 6), unit: inputs.to || "", rows: [["结果", fmt(r, 6) + " " + (inputs.to || "")]] };
  }
  const fn = COMPUTE[config.id];
  if (!fn) return { kind: "value", primary: "暂不支持", unit: "", rows: [] };
  try {
    return fn(inputs, config) || { kind: "value", primary: "—", rows: [] };
  } catch (e) {
    return { kind: "value", primary: "计算出错", rows: [["提示", String(e.message || e)]] };
  }
}

// ---------------- 浏览器侧 DOM 挂载 ----------------
function buildForm(config) {
  const form = document.createElement("form");
  form.className = "tool-form";
  const getVal = (el) => (el.type === "number" ? parseFloat(el.value) : el.value);
  const gather = () => {
    const inputs = {};
    form.querySelectorAll("[data-key]").forEach((el) => (inputs[el.dataset.key] = getVal(el)));
    return inputs;
  };
  const inputsDef = config.type === "converter"
    ? [{ key: "value", label: "数值", unit: "", default: 1, min: -1e15, max: 1e15, step: "any" }]
    : config.inputs || [];
  inputsDef.forEach((inp) => {
    const wrap = document.createElement("div");
    wrap.className = "field";
    const label = document.createElement("label");
    label.textContent = inp.label + (inp.unit ? " (" + inp.unit + ")" : "");
    wrap.appendChild(label);
    let el;
    if (inp.type === "select") {
      el = document.createElement("select");
      inp.options.forEach((o) => { const op = document.createElement("option"); op.value = o; op.textContent = o; if (o === inp.default) op.selected = true; el.appendChild(op); });
    } else if (inp.type === "date") {
      el = document.createElement("input"); el.type = "date"; if (inp.default) el.value = inp.default;
    } else {
      el = document.createElement("input"); el.type = "number"; el.step = inp.step || "any";
      if (inp.min != null) el.min = inp.min; if (inp.max != null) el.max = inp.max;
      el.value = inp.default != null ? inp.default : "";
    }
    el.dataset.key = inp.key;
    wrap.appendChild(el);
    form.appendChild(wrap);
  });
  if (config.type === "converter") {
    ["from", "to"].forEach((which) => {
      const wrap = document.createElement("div"); wrap.className = "field";
      const label = document.createElement("label"); label.textContent = which === "from" ? "从" : "到";
      wrap.appendChild(label);
      const sel = document.createElement("select"); sel.dataset.key = which;
      config.units.forEach((u) => { const op = document.createElement("option"); op.value = u.name; op.textContent = u.name; if ((which === "from" && u.name === config.defaultFrom) || (which === "to" && u.name === config.defaultTo)) op.selected = true; sel.appendChild(op); });
      wrap.appendChild(sel); form.appendChild(wrap);
    });
  }
  const btn = document.createElement("button");
  btn.type = "submit"; btn.className = "tool-btn"; btn.textContent = "计算";
  form.appendChild(btn);
  const result = document.createElement("div"); result.className = "tool-result";
  const run = () => {
    const res = computeTool(config, gather());
    result.innerHTML = renderResult(res);
    result.style.display = "block";
  };
  form.addEventListener("submit", (e) => { e.preventDefault(); run(); });
  // 输入变化自动重算（除日期/按钮外）
  form.addEventListener("input", (e) => { if (e.target.type !== "date") run(); });
  form.addEventListener("change", run);
  // 首次自动算一次
  setTimeout(run, 0);
  return { form, result };
}

function renderResult(res) {
  let html = "";
  if (res.kind === "table") {
    html += "<table class='tool-table'><thead><tr>" + res.headers.map((h) => "<th>" + esc(h) + "</th>").join("") + "</tr></thead><tbody>";
    html += res.rows.map((r) => "<tr>" + r.map((c) => "<td>" + esc(c) + "</td>").join("") + "</tr>").join("");
    html += "</tbody></table>";
  } else {
    if (res.primary !== undefined && res.primary !== "") {
      html += "<div class='tool-primary'>" + esc(res.primary) + (res.unit ? " <span class='u'>" + esc(res.unit) + "</span>" : "") + "</div>";
    }
    if (res.rows && res.rows.length) {
      html += "<dl class='tool-rows'>" + res.rows.map((r) => "<dt>" + esc(r[0]) + "</dt><dd>" + esc(r[1]) + "</dd>").join("") + "</dl>";
    }
  }
  if (res.note) html += "<p class='tool-note'>" + esc(res.note) + "</p>";
  return html;
}

function esc(s) {
  return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

export function mountTool(container, config) {
  if (!container || !config) return;
  container.innerHTML = "";
  const head = document.createElement("div");
  head.className = "tool-head";
  head.innerHTML = "<strong>" + esc(config.title) + "</strong>" + (config.intro ? "<p>" + esc(config.intro) + "</p>" : "");
  const { form, result } = buildForm(config);
  container.appendChild(head);
  container.appendChild(form);
  container.appendChild(result);
  if (config.disclaimer) {
    const d = document.createElement("p");
    d.className = "tool-disclaimer";
    d.textContent = "⚠️ 计算结果仅供参考，不构成专业建议，请以官方/专业人士意见为准。";
    container.appendChild(d);
  }
}

// 自动挂载页面上所有 [data-tool-id]
export function autoMount(registry) {
  if (typeof document === "undefined") return;
  document.querySelectorAll("[data-tool-id]").forEach((el) => {
    const key = el.getAttribute("data-tool-keyword");
    const config = registry[key];
    if (config) mountTool(el, config);
  });
}
