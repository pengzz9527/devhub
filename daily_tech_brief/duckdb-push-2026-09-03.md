# 📊 DuckDB 实战笔记 ｜ 2026-09-03

> 每天一个 DuckDB 实战技巧，让你立刻能用。

---

## 🔥 今日话题：窗口函数实战 — LAG/LEAD/ROW_NUMBER 解决 80% 的分析难题

**核心技巧：用 LAG/LEAD 做同比环比，用 ROW_NUMBER 做去重和 TopN，一套组合拳解决日常分析。**

```sql
-- 创建订单表（可直接运行）
CREATE TABLE orders AS SELECT * FROM (VALUES
    ('2024-01-01', 'A', 100),
    ('2024-01-02', 'A', 150),
    ('2024-01-03', 'A', 120),
    ('2024-01-01', 'B', 200),
    ('2024-01-02', 'B', 180)
) t(dt, product, amount);

-- 场景 1：计算每日销售额的日环比
SELECT dt, product, amount,
       LAG(amount) OVER (PARTITION BY product ORDER BY dt) AS prev_day_amount,
       ROUND((amount - LAG(amount) OVER (PARTITION BY product ORDER BY dt)) 
             / LAG(amount) OVER (PARTITION BY product ORDER BY dt) * 100, 2) AS growth_pct
FROM orders
ORDER BY product, dt;
```

**原理：窗口函数在每行数据上，基于 `PARTITION BY` 分组、`ORDER BY` 排序，让你访问该行前后 N 行的数据，无需自连接。**

适用场景：
- 📈 销售/流量数据的日环比、周同比
- 🏆 各类排行榜的 TopN 查询
- 🧹 数据去重（保留最新记录）
- ⏱️ 计算相邻事件的时间间隔
- 📊 移动平均、累计求和

---

### 🎯 场景 1：计算日环比（LAG 实战）

**问题**：电商运营每天要看各产品的销售趋势，想知道今天比昨天增长多少。

```sql
-- 直接计算环比，NULL 表示没有前一天数据
SELECT dt, product, amount,
       LAG(amount) OVER (PARTITION BY product ORDER BY dt) AS prev_amount,
       ROUND((amount - LAG(amount) OVER w) * 100.0 / LAG(amount) OVER w, 2) AS mom_pct
FROM orders
WINDOW w AS (PARTITION BY product ORDER BY dt)
ORDER BY product, dt;
```

**结果解读**：A 产品 1月2日 环比增长 50%，1月3日环比下降 20%，一目了然。

---

### 🎯 场景 2：TopN 分析（ROW_NUMBER 实战）

**问题**：找出每个产品销量最大的前 2 天，方便做促销复盘。

```sql
WITH ranked AS (
    SELECT dt, product, amount,
           ROW_NUMBER() OVER (PARTITION BY product ORDER BY amount DESC) AS rn
    FROM orders
)
SELECT * FROM ranked WHERE rn <= 2;
```

**扩展技巧**：把 `ROW_NUMBER` 换成 `RANK()` 或 `DENSE_RANK()`，可以处理并列排名的情况。`ROW_NUMBER` 用于严格去重，`RANK` 用于体育比赛式排名。

---

### 🎯 场景 3：时间间隔计算（LEAD 实战）

**问题**：用户行为分析中，计算每个用户相邻两次购买的时间间隔。

```sql
-- 用户购买记录
CREATE TABLE purchases AS SELECT * FROM (VALUES
    (1, '2024-01-01'), (1, '2024-01-05'),
    (1, '2024-01-10'), (2, '2024-01-02'), (2, '2024-01-08')
) t(user_id, purchase_date);

-- 计算购买间隔天数
SELECT user_id, purchase_date,
       LEAD(purchase_date) OVER (PARTITION BY user_id ORDER BY purchase_date) AS next_purchase,
       DATEDIFF('day', purchase_date, 
                LEAD(purchase_date) OVER (PARTITION BY user_id ORDER BY purchase_date)) AS gap_days
FROM purchases
ORDER BY user_id, purchase_date;
```

**业务价值**：间隔天数 > 30 的用户可能已流失，需要触发召回策略。

---

### 💡 进阶技巧：窗口函数 + FILTER 组合

```sql
-- 计算 7 日移动平均（用 ROWS BETWEEN 指定窗口范围）
SELECT dt, amount,
       AVG(amount) OVER (ORDER BY dt ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS ma_7d
FROM orders WHERE product = 'A';
```

---

## 📌 总结

窗口函数是 SQL 分析的核心武器，`LAG/LEAD` 处理时间序列、`ROW_NUMBER` 解决排名去重，掌握这三个函数就能应对大多数分析需求。遇到复杂问题，先用窗口函数拆解，比 JOIN 自身高效得多。

**行动建议**：打开 DuckDB 终端，用今天的订单表数据跑一遍示例，然后尝试改成你自己的业务数据（比如把 product 换成 region、amount 换成 revenue）。实践一次胜过读十遍！

📌 收藏笔记，下次遇到直接参考。
🔍 [duckdblab.org](https://duckdblab.org) 系统学习 DuckDB。
