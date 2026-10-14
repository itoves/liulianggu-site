import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { computeTool } from "../tools.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const registry = JSON.parse(readFileSync(join(__dirname, "..", "registry.json"), "utf-8"));

const approx = (a, b, eps = 0.5) => Math.abs(a - b) <= eps;
// 计算结果显示带千位逗号/单位，解析时先清洗
const num = (s) => Number(String(s).replace(/[,\s]/g, "").replace(/[^\d.\-]/g, ""));
const cfg = (k) => registry[k];
const run = (k, inputs) => computeTool(cfg(k), inputs);

test("BMI: 170cm/65kg -> 22.5 正常", () => {
  const r = run("BMI 体重指数计算器", { heightCm: 170, weightKg: 65 });
  assert.ok(approx(num(r.primary), 22.5, 0.1), r.primary);
  assert.match(r.rows[1][1], /正常/);
});
test("复利: 10000/5%/10年/12次 -> ~16470", () => {
  const r = run("复利计算器", { principal: 10000, rate: 5, years: 10, freq: 12 });
  assert.ok(approx(num(r.primary), 16470, 5), r.primary);
});
test("年化收益率: 10000->15000/3年 -> 14.47%", () => {
  const r = run("年化收益率计算器", { start: 10000, end: 15000, years: 3 });
  assert.ok(approx(num(r.primary), 14.47, 0.1), r.primary);
});
test("基金定投: 1000/8%/60月 -> ~73470", () => {
  const r = run("基金定投收益计算器", { pmt: 1000, rate: 8, months: 60 });
  assert.ok(approx(num(r.primary), 73470, 50), r.primary);
});
test("个税: 20000/3000/2000 -> 税后16210", () => {
  const r = run("个人所得税计算器", { salary: 20000, insurance: 3000, special: 2000 });
  assert.ok(approx(num(r.rows[2][1]), 16210, 1), r.rows[2][1]);
});
test("存款: 50000/1.5%/1年 -> 本息50750", () => {
  const r = run("存款利息计算器", { principal: 50000, rate: 1.5, years: 1 });
  assert.ok(approx(num(r.primary), 50750, 1), r.primary);
});
test("房贷等额本息: 100万/3.95%/30年 -> 月供~4746", () => {
  const r = run("房贷利率计算器", { amount: 100, rate: 3.95, years: 30, method: "等额本息" });
  assert.ok(approx(num(r.primary), 4746, 20), r.primary);
});
test("温度: 25°C -> 77°F / 298.15K", () => {
  const r = run("温度单位换算", { value: 25, from: "°C" });
  assert.ok(approx(num(r.rows[1][1]), 77, 0.1), r.rows[1][1]);
  assert.ok(approx(num(r.rows[2][1]), 298.15, 0.1), r.rows[2][1]);
});
test("换算: 1公里 -> 0.62137英里", () => {
  const r = computeTool(cfg("公里英里换算"), { value: 1, from: "公里(km)", to: "英里(mi)" });
  assert.ok(approx(num(r.primary), 0.62137, 1e-4), r.primary);
});
test("基础代谢(男30/170/65) -> 1567.5", () => {
  const r = run("基础代谢率计算器", { sex: "男", age: 30, heightCm: 170, weightKg: 65 });
  assert.ok(approx(num(r.primary), 1567.5, 0.1), r.primary);
});
test("体脂率(男30/170/65) -> ~17.7%", () => {
  const r = run("体脂率计算器", { sex: "男", age: 30, heightCm: 170, weightKg: 65 });
  assert.ok(approx(num(r.primary), 17.7, 0.2), r.primary);
});
test("每日饮水(65kg中等) -> 2.275L", () => {
  const r = run("每日饮水量计算器", { weightKg: 65, activity: "中等" });
  assert.ok(approx(num(r.primary), 2.275, 0.01), r.primary);
});
test("卡路里(65kg慢跑7/30分) -> ~238.9", () => {
  const r = run("卡路里消耗计算器", { weightKg: 65, activity: "慢跑(7)", minutes: 30 });
  assert.ok(approx(num(r.primary), 238.9, 1), r.primary);
});
test("GPA(85) -> 3.5", () => {
  const r = run("GPA 换算器", { score: 85 });
  assert.ok(approx(num(r.primary), 3.5, 0.01), r.primary);
});
test("等级(85) -> 良好", () => {
  const r = run("百分制等级换算", { score: 85 });
  assert.match(r.primary, /良好/);
});
test("时薪(8000/(21.75*8)) -> ~46.0", () => {
  const r = run("时薪换算器", { monthly: 8000, days: 21.75, hours: 8 });
  assert.ok(approx(num(r.primary), 46.0, 0.2), r.primary);
});
test("加班费(50*1.5*10) -> 750", () => {
  const r = run("加班费计算器", { hourly: 50, hours: 10, mult: "1.5 倍(休息日)" });
  assert.ok(approx(num(r.primary), 750, 0.1), r.primary);
});
test("年终奖(30000) -> 税后29100", () => {
  const r = run("年终奖个税计算器", { bonus: 30000 });
  assert.ok(approx(num(r.primary), 29100, 1), r.primary);
});
test("五险一金(10000一般) -> 个人2250", () => {
  const r = run("五险一金计算指南", { base: 10000, city: "一般城市(养老8%/医疗2%/失业0.5%/公积金12%)" });
  assert.ok(approx(num(r.primary), 2250, 1), r.primary);
});
test("退休年龄(男1975) -> 63", () => {
  const r = run("退休年龄计算器", { sex: "男", birthYear: 1975 });
  assert.equal(r.primary, "63");
});
test("产假(60天/否/0) -> 158天", () => {
  const r = run("产假天数计算器", { provinceAdd: "60天(多数省)", hard: "否", multi: "0" });
  assert.equal(r.primary, "158");
});
test("社保年限(2045) -> 20年", () => {
  const r = run("社保缴费年限查询", { retireYear: 2045 });
  assert.equal(r.primary, "20");
});
test("预产期: lmp 2026-01-01 -> 2026-10-08", () => {
  const r = run("预产期计算器", { lmp: "2026-01-01" });
  assert.equal(r.rows[0][1], "2026-10-08");
});
test("像素打印(300px/300dpi) -> 2.54cm / 1in", () => {
  const r = run("像素与打印尺寸换算", { px: 300, dpi: 300 });
  assert.ok(approx(num(r.rows[0][1]), 2.54, 0.01), r.rows[0][1]);
});
test("装修预算(89㎡中档) -> 133500", () => {
  const r = run("装修预算计算器", { area: 89, tier: "中档(1500元/㎡)" });
  assert.ok(approx(num(r.primary), 133500, 1), r.primary);
});
test("墙砖(30㎡/30x60cm/5%) -> 块数", () => {
  const r = run("墙砖数量计算器", { wallArea: 30, tileW: 30, tileH: 60, waste: 5 });
  assert.ok(parseInt(r.primary) > 0);
});
test("全部 58 个工具都能被 computeTool 调用且不抛错", () => {
  for (const [k, c] of Object.entries(registry)) {
    const sample = {};
    (c.inputs || [{ key: "value", default: 1 }, { key: "from", default: c.units?.[0]?.name }, { key: "to", default: c.units?.[1]?.name }]).forEach((inp) => {
      sample[inp.key] = inp.default !== undefined ? inp.default : (inp.options ? inp.options[0] : 1);
    });
    if (c.type === "converter" && (!sample.from || !sample.to)) { sample.from = c.units[0].name; sample.to = c.units[1].name; sample.value = 1; }
    const res = computeTool(c, sample);
    assert.ok(res && (res.kind === "value" || res.kind === "table"), k + " 返回异常: " + JSON.stringify(res));
  }
});
