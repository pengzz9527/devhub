---
title: "📊 DuckDB 实战笔记｜2026-08-27：Gap 和 Island 问题 — 连续区间检测与断档分析的 SQL 解法"
description: "每天一个 DuckDB 实战技巧。今天教你用窗口函数解决经典的 Gap 和 Island 问题：连续登录天数、价格连续涨跌区间、设备在线离线状态分析——一条 SQL 搞定以前需要写几十行代码的复杂逻辑。"
date: 2026-08-27
tags: ["DuckDB", "窗口函数", "Gap Island", "连续区间", "断档分析", "SQL", "实战"]
categories: ["DuckDB 实战笔记"]
toc: false
---

# 📊 DuckDB 实战笔记 ｜ 2026-08-27

> **每天一个 DuckDB 实战技巧，让你立刻能用。**

---

## 🔥 今日话题：Gap 和 Island 问题 — 连续区间检测与断档分析

你有没有遇到过这种场景：

> 用户登录日志表里，你需要统计「每个用户最长连续登录天数」。或者价格表中，你要找出「价格连续上涨的天数区间」。
>
> 用 Python 写？先排序、再遍历、标记连续段……代码二十行起步，还容易出错。

**这是经典的「Gap 和 Island」问题。**

- **Island（岛）**：连续满足条件的数据段
- **Gap（间隙）**：不满足条件的间隔

DuckDB 用窗口函数，**一条 SQL 就能精准识别所有连续区间**。

---

## 📋 场景一：连续登录天数统计

假设你有一张用户登录日志表 `login_log`：

```sql
CREATE TABLE login_log AS
SELECT * FROM (VALUES
    (1, DATE '2026-08-01'),
    (1, DATE '2026-08-02'),
    (1, DATE '2026-08-03'),
    (1, DATE '2026-08-05'),
    (1, DATE '2026-08-06'),
    (2, DATE '2026-08-01'),
    (2, DATE '2026-08-03'),
    (2, DATE '2026-08-04'),
    (2, DATE '2026-08-05'),
    (2, DATE '2026-08-07'),
    (2, DATE '2026-08-08')
) AS t(user_id, login_date);
```

**需求：每个用户的连续登录区间有哪些？每个区间持续几天？**

### 核心思路：差值法

```sql
WITH numbered AS (
    SELECT 
        user_id,
        login_date,
        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY login_date) AS rn
    FROM login_log
),
grouped AS (
    SELECT 
        user_id,
        login_date,
        login_date - INTERVAL (rn) DAY AS grp
    FROM numbered
)
SELECT 
    user_id,
    MIN(login_date) AS start_date,
    MAX(login_date) AS end_date,
    COUNT(*) AS consecutive_days
FROM grouped
GROUP BY user_id, grp
ORDER BY user_id, start_date;
```

**输出：**

```
┌──────────┬────────────┬────────────┬──────────────────┐
│ user_id  │ start_date │ end_date   │ consecutive_days │
├──────────┼────────────┼────────────┼──────────────────┤
│ 1        │ 2026-08-01 │ 2026-08-03 │       3          │
│ 1        │ 2026-08-05 │ 2026-08-06 │       2          │
│ 2        │ 2026-08-01 │ 2026-08-01 │       1          │
│ 2        │ 2026-08-03 │ 2026-08-05 │       3          │
│ 2        │ 2026-08-07 │ 2026-08-08 │       2          │
└──────────┴────────────┴────────────┴──────────────────┘
```

**原理：**
- 用户 1：8/1、8/2、8/3 连续 → `date - row_number` 得到相同值 → 同一个组
- 8/5、8/6 连续 → 另一个 `date - row_number` 值 → 第二个组
- 差值相同的日期，必然是连续的

---

## 💡 核心技巧：Gap Island 通用模板

这个问题的解法有一个**通用模板**，适用于各种连续区间场景：

```sql
WITH numbered AS (
    -- 1. 给每条记录编号
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY <分组列> ORDER BY <排序列>) AS rn
    FROM <表>
    WHERE <条件>  -- 只取「岛上」的数据
),
grouped AS (
    -- 2. 用差值法识别连续区间
    SELECT *,
           <排序列> - INTERVAL (rn) <单位> AS grp
    FROM numbered
)
-- 3. 按组聚合
SELECT <分组列>, MIN(<排序列>), MAX(<排序列>), COUNT(*)
FROM grouped
GROUP BY <分组列>, grp;
```

**关键洞察：连续整数减去连续序号，结果恒定。**

---

## 📋 场景二：价格连续涨跌区间

假设你有一张股票价格表 `stock_price`：

```sql
CREATE TABLE stock_price AS
SELECT * FROM (VALUES
    (1, DATE '2026-08-01', 100.0),
    (1, DATE '2026-08-02', 102.0),
    (1, DATE '2026-08-03', 104.0),
    (1, DATE '2026-08-04', 103.0),
    (1, DATE '2026-08-05', 101.0),
    (1, DATE '2026-08-06', 100.0),
    (1, DATE '2026-08-07', 102.0),
    (1, DATE '2026-08-08', 105.0)
) AS t(stock_id, trade_date, price);
```

**需求：找出价格连续上涨和连续下跌的区间**

```sql
WITH daily_change AS (
    SELECT 
        stock_id,
        trade_date,
        price,
        price - LAG(price) OVER (PARTITION BY stock_id ORDER BY trade_date) AS change
    FROM stock_price
),
labeled AS (
    SELECT 
        stock_id,
        trade_date,
        price,
        change,
        CASE 
            WHEN change > 0 THEN '上涨'
            WHEN change < 0 THEN '下跌'
            ELSE '持平'
        END AS trend,
        ROW_NUMBER() OVER (PARTITION BY stock_id ORDER BY trade_date) AS rn
    FROM daily_change
    WHERE change IS NOT NULL
),
grouped AS (
    SELECT 
        stock_id,
        trade_date,
        price,
        trend,
        change,
        trend || '_' || (rn - ROW_NUMBER() OVER (PARTITION BY stock_id, trend ORDER BY trade_date)) AS grp
    FROM labeled
)
SELECT 
    stock_id,
    trend AS 涨跌类型,
    MIN(trade_date) AS 开始日期,
    MAX(trade_date) AS 结束日期,
    COUNT(*) AS 连续天数,
    ROUND(MIN(price), 2) AS 最低价,
    ROUND(MAX(price), 2) AS 最高价
FROM grouped
GROUP BY stock_id, trend, grp
ORDER BY stock_id, 开始日期;
```

**输出：**

```
┌──────────┬────────┬────────────┬────────────┬──────────┬───────────┬───────────┐
│ stock_id │ 涨跌类型│ 开始日期   │ 结束日期   │ 连续天数 │   最低价  │   最高价  │
├──────────┼────────┼────────────┼────────────┼──────────┼───────────┼───────────┤
│ 1        │ 上涨   │ 2026-08-02 │ 2026-08-03 │    2     │   102.00  │   104.00  │
│ 1        │ 下跌   │ 2026-08-04 │ 2026-08-06 │    3     │   100.00  │   103.00  │
│ 1        │ 上涨   │ 2026-08-07 │ 2026-08-08 │    2     │   102.00  │   105.00  │
└──────────┴────────┴────────────┴────────────┴──────────┴───────────┴───────────┘
```

---

## 📋 场景三：设备在线/离线状态分析

IoT 设备每分钟上报状态，找出每次在线/离线的持续时长：

```sql
CREATE TABLE device_status AS
SELECT * FROM (VALUES
    (1, TIMESTAMP '2026-08-01 08:00:00', 'online'),
    (1, TIMESTAMP '2026-08-01 08:01:00', 'online'),
    (1, TIMESTAMP '2026-08-01 08:02:00', 'offline'),
    (1, TIMESTAMP '2026-08-01 08:03:00', 'offline'),
    (1, TIMESTAMP '2026-08-01 08:04:00', 'offline'),
    (1, TIMESTAMP '2026-08-01 08:05:00', 'online'),
    (1, TIMESTAMP '2026-08-01 08:06:00', 'online'),
    (2, TIMESTAMP '2026-08-01 08:00:00', 'online'),
    (2, TIMESTAMP '2026-08-01 08:01:00', 'offline'),
    (2, TIMESTAMP '2026-08-01 08:02:00', 'offline'),
    (2, TIMESTAMP '2026-08-01 08:03:00', 'online')
) AS t(device_id, ts, status);
```

```sql
WITH numbered AS (
    SELECT device_id, ts, status,
           ROW_NUMBER() OVER (PARTITION BY device_id ORDER BY ts) AS rn
    FROM device_status
),
grouped AS (
    SELECT device_id, ts, status,
           status || '_' || (rn - ROW_NUMBER() OVER (
               PARTITION BY device_id, status ORDER BY ts
           )) AS grp
    FROM numbered
)
SELECT device_id, status,
       MIN(ts) AS start_time,
       MAX(ts) AS end_time,
       COUNT(*) AS duration_minutes
FROM grouped
GROUP BY device_id, status, grp
ORDER BY device_id, start_time;
```

**输出：**

```
┌────────────┬────────┬─────────────────────┬─────────────────────┬──────────────┐
│ device_id  │ 状态   │ 开始时间            │ 结束时间            │ 持续分钟数   │
├────────────┼────────┼─────────────────────┼─────────────────────┼──────────────┤
│ 1          │ online │ 2026-08-01 08:00:00 │ 2026-08-01 08:01:00 │     2        │
│ 1          │ offline│ 2026-08-01 08:02:00 │ 2026-08-01 08:04:00 │     3        │
│ 1          │ online │ 2026-08-01 08:05:00 │ 2026-08-01 08:06:00 │     2        │
│ 2          │ online │ 2026-08-01 08:00:00 │ 2026-08-01 08:00:00 │     1        │
│ 2          │ offline│ 2026-08-01 08:01:00 │ 2026-08-01 08:02:00 │     2        │
│ 2          │ online │ 2026-08-01 08:03:00 │ 2026-08-01 08:03:00 │     1        │
└────────────┴────────┴─────────────────────┴─────────────────────┴──────────────┘
```

---

## 🚀 实战技巧：只关注特定 Island

只需要连续 3 天以上价格上涨的区间？先过滤再编号：

```sql
WITH labeled AS (
    SELECT stock_id, trade_date, price,
           price - LAG(price) OVER (PARTITION BY stock_id ORDER BY trade_date) AS change,
           ROW_NUMBER() OVER (PARTITION BY stock_id ORDER BY trade_date) AS rn
    FROM stock_price
),
only_up AS (
    -- 只保留上涨的日期
    SELECT stock_id, trade_date, price, rn
    FROM labeled
    WHERE change > 0
),
grouped AS (
    SELECT stock_id, trade_date, price,
           trade_date - INTERVAL (rn) DAY AS grp
    FROM only_up
)
SELECT stock_id,
       MIN(trade_date) AS start_date,
       MAX(trade_date) AS end_date,
       COUNT(*) AS consecutive_up_days
FROM grouped
GROUP BY stock_id, grp
HAVING COUNT(*) >= 3;  -- 只保留连续 3 天以上的
```

---

## 🧠 Gap Island 问题完整对比

| 场景 | 条件 | 核心技巧 |
|------|------|---------|
| 连续日期 | `date - row_number` 相同 | 差值法 |
| 连续数值 | 相邻差值为固定值 | LAG + 差值分组 |
| 连续状态 | 状态相同的连续段 | 状态 + 行号差值 |
| 满足条件的连续 | 先过滤再编号 | WHERE 前置过滤 |

**通用公式：**

```
连续组的标识 = 排序列 - ROW_NUMBER() OVER (PARTITION BY 分组列 ORDER BY 排序列)
```

---

## 🐍 在 Python 中使用

```python
import duckdb

con = duckdb.connect(":memory:")

con.execute("""
CREATE TABLE login_log AS
SELECT * FROM (VALUES
    (1, DATE '2026-08-01'), (1, DATE '2026-08-02'),
    (1, DATE '2026-08-03'), (1, DATE '2026-08-05'),
    (1, DATE '2026-08-06'), (2, DATE '2026-08-01'),
    (2, DATE '2026-08-03'), (2, DATE '2026-08-04'),
    (2, DATE '2026-08-05'), (2, DATE '2026-08-07'),
    (2, DATE '2026-08-08')
) AS t(user_id, login_date)
""")

result = con.execute("""
WITH numbered AS (
    SELECT user_id, login_date,
           ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY login_date) AS rn
    FROM login_log
),
grouped AS (
    SELECT user_id, login_date,
           login_date - INTERVAL (rn) DAY AS grp
    FROM numbered
)
SELECT user_id,
       MIN(login_date) AS start_date,
       MAX(login_date) AS end_date,
       COUNT(*) AS consecutive_days
FROM grouped
GROUP BY user_id, grp
ORDER BY user_id, start_date
""").fetchdf()

print(result)
```

---

## 📝 小结

| 技能 | 一句话总结 |
|------|-----------|
| 差值法核心 | `排序列 - ROW_NUMBER()` 相同 → 连续同组 |
| 通用模板 | 编号 → 差值分组 → 聚合 |
| 过滤前置 | 只需要特定条件的 Island？先 WHERE 再编号 |
| 多列分组 | `PARTITION BY 用户, 状态` 支持复杂场景 |
| 有界区间 | `HAVING COUNT(*) >= N` 过滤太短的 Island |

**Gap 和 Island 问题让你：一条 SQL 搞定连续区间分析，再也不用写 Python 循环标记连续段了。**

---

## 💬 互动

你的数据里有没有「找出连续满足条件的区间」的需求？把场景发出来，我们一起看看用差值法怎么解！

---

📌 收藏这条笔记，下次遇到连续区间分析问题时直接回来参考。

---

🔍 想系统学习 DuckDB 实战技巧？[duckdblab.org](https://duckdblab.org) 上有完整教程系列，从基础查询到窗口函数高级用法，带你成为 DuckDB 实战专家。
