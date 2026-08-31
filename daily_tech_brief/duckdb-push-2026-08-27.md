# 📊 DuckDB 实战笔记 ｜ 2026-08-27

> 每天一个 DuckDB 实战技巧，让你立刻能用。

---

## 🔥 今日话题：Gap 和 Island 问题 — 连续区间检测与断档分析的 SQL 解法

**核心技巧：差值法**

```sql
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
GROUP BY user_id, grp;
```

**原理：连续日期 - 连续行号 = 相同值 → 同一个岛**

适用场景：连续登录天数、价格涨跌区间、设备在线状态、订单连续无操作时段。

📌 收藏笔记，下次遇到连续区间分析直接参考。
🔍 [duckdblab.org](https://duckdblab.org) 系统学习 DuckDB。
