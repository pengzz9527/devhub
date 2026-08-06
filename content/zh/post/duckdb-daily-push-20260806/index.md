---
title: "📊 DuckDB 实战笔记｜2026-08-06：递归 CTE — 处理组织架构、分类树、层级数据"
description: "每天一个 DuckDB 实战技巧。今天教你用递归 CTE 处理组织架构、产品分类、文件目录等层级数据，一条 SQL 搞定无限层级的上下级关系查询。"
date: 2026-08-06
tags: ["DuckDB", "递归CTE", "层级数据", "组织架构", "SQL", "实战"]
categories: ["DuckDB 实战笔记"]
toc: false
---

# 📊 DuckDB 实战笔记 ｜ 2026-08-06

> **每天一个 DuckDB 实战技巧，让你立刻能用。**

---

## 🔥 今日话题：递归 CTE — 处理组织架构、分类树、层级数据

你有没有遇到过这种场景：

> 公司组织架构表里，每个人有一个 `manager_id` 指向上级。现在要查「某人的所有下属」（包括下属的下属、下属的下属的下属……），一共多少层？
>
> 或者电商的产品分类是无限层级的：电子产品 → 手机 → 智能手机 → iPhone。现在要导出某个类目下的所有子类目。
>
> 再比如文件目录树：根目录 → 文件夹 A → 子文件夹 B → 文件 C。要列出某个目录下的所有文件和子目录。

这些问题的共同特点是：**层级深度不固定，可能是 2 层，也可能是 10 层甚至更多。**

传统 SQL 的 `JOIN` 只能处理固定层数的关联。要处理无限层级？用 **递归 CTE（Recursive CTE）**。

---

## 📋 场景：查询组织架构的完整下属链

假设你有一张员工表 `employees`，结构如下：

| id | name | manager_id |
|----|------|------------|
| 1  | 张三 | NULL       |  ← CEO，没有上级
| 2  | 李四 | 1          |  ← 向张三汇报
| 3  | 王五 | 1          |  ← 向张三汇报
| 4  | 赵六 | 2          |  ← 向李四汇报
| 5  | 钱七 | 2          |  ← 向李四汇报
| 6  | 孙八 | 4          |  ← 向赵六汇报

**问题：查李四（id=2）的所有下属，包括间接下属。**

### 递归 CTE 写法

```sql
WITH RECURSIVE subordinates AS (
    -- 锚点：先从李四的直接下属开始
    SELECT id, name, manager_id, 1 AS level
    FROM employees
    WHERE manager_id = 2
    
    UNION ALL
    
    -- 递归：继续往下找下属的下属
    SELECT e.id, e.name, e.manager_id, s.level + 1
    FROM employees e
    JOIN subordinates s ON e.manager_id = s.id
)
SELECT * FROM subordinates;
```

**输出：**

```
┌────┬──────┬────────────┬────────┐
│ id │ name │ manager_id │ level  │
├────┼──────┼────────────┼────────┤
│ 4  │ 赵六 │ 2          │ 1      │
│ 5  │ 钱七 │ 2          │ 1      │
│ 6  │ 孙八 │ 4          │ 2      │
└────┴──────┴────────────┴────────┘
```

**解读：**
- `level=1`：赵六、钱七是李四的直接下属
- `level=2`：孙八是赵六的下属，也就是李四的间接下属

---

## 💡 递归 CTE 的核心结构

递归 CTE 由两部分组成：

### 1. 锚点查询（Anchor）
- 定义递归的起点
- 通常是直接相关的记录（直接下属、直接子分类）

### 2. 递归查询（Recursive）
- 引用 CTE 本身
- 每次递归处理下一层
- 用 `UNION ALL` 连接锚点和递归部分

```sql
WITH RECURSIVE cte_name AS (
    -- 锚点：递归的起点
    SELECT ... FROM table WHERE condition
    
    UNION ALL
    
    -- 递归：继续往下找
    SELECT ... FROM table JOIN cte_name ON ...
)
SELECT * FROM cte_name;
```

---

## 📋 场景二：产品分类树（无限层级）

电商系统的产品分类通常是树形结构：

| category_id | name | parent_id |
|-------------|------|-----------|
| 1 | 电子产品 | NULL |
| 2 | 手机 | 1 |
| 3 | 智能手机 | 2 |
| 4 | iPhone | 3 |
| 5 | 安卓手机 | 3 |
| 6 | 笔记本电脑 | 2 |
| 7 | 配件 | 1 |
| 8 | 手机壳 | 7 |

**问题：查「电子产品」（id=1）下的所有子分类，包括间接子分类。**

```sql
WITH RECURSIVE category_tree AS (
    -- 锚点：电子产品本身
    SELECT category_id, name, parent_id, 0 AS level
    FROM categories
    WHERE category_id = 1
    
    UNION ALL
    
    -- 递归：找下一级分类
    SELECT c.category_id, c.name, c.parent_id, ct.level + 1
    FROM categories c
    JOIN category_tree ct ON c.parent_id = ct.category_id
)
SELECT category_id, name, level FROM category_tree;
```

**输出：**

```
┌───────────────┬──────────┬───────┐
│ category_id   │ name     │ level │
├───────────────┼──────────┼───────┤
│ 1             │ 电子产品  │ 0     │
│ 2             │ 手机     │ 1     │
│ 3             │ 智能手机 │ 2     │
│ 4             │ iPhone   │ 3     │
│ 5             │ 安卓手机 │ 3     │
│ 6             │ 笔记本电脑│ 2    │
│ 7             │ 配件     │ 1     │
│ 8             │ 手机壳   │ 2     │
└───────────────┴──────────┴───────┘
```

---

## 📋 场景三：文件目录树

文件目录也是典型的层级结构：

| file_id | name | parent_id | is_file |
|---------|------|-----------|---------|
| 1 | 根目录 | NULL | FALSE |
| 2 | 文档 | 1 | FALSE |
| 3 | 照片 | 1 | FALSE |
| 4 | 工作文档.pdf | 2 | TRUE |
| 5 | vacation.jpg | 3 | TRUE |

**问题：列出「根目录」下的所有文件和子目录（递归展开）。**

```sql
WITH RECURSIVE file_tree AS (
    -- 锚点：根目录
    SELECT file_id, name, parent_id, is_file, 0 AS depth
    FROM files
    WHERE file_id = 1
    
    UNION ALL
    
    -- 递归：找子目录和文件
    SELECT f.file_id, f.name, f.parent_id, f.is_file, ft.depth + 1
    FROM files f
    JOIN file_tree ft ON f.parent_id = ft.file_id
)
SELECT REPEAT('  ', depth) || name AS path, is_file
FROM file_tree
ORDER BY depth, name;
```

**输出：**

```
┌──────────────────┬─────────┐
│ path             │ is_file │
├──────────────────┼─────────┤
│ 根目录           │ FALSE   │
│   文档           │ FALSE   │
│     工作文档.pdf  │ TRUE    │
│   照片           │ FALSE   │
│     vacation.jpg │ TRUE    │
└──────────────────┴─────────┘
```

---

## 🚀 实战技巧：防止递归死循环

如果数据中有循环引用（A 的上级是 B，B 的上级是 A），递归 CTE 会无限循环。

### 解决方案：加深度限制

```sql
WITH RECURSIVE subordinates AS (
    SELECT id, name, manager_id, 1 AS level
    FROM employees
    WHERE manager_id = 2
    
    UNION ALL
    
    SELECT e.id, e.name, e.manager_id, s.level + 1
    FROM employees e
    JOIN subordinates s ON e.manager_id = s.id
    WHERE s.level < 10  -- 限制最多递归 10 层
)
SELECT * FROM subordinates;
```

### 解决方案：记录已访问节点

```sql
WITH RECURSIVE subordinates AS (
    SELECT id, name, manager_id, 1 AS level, 
           CAST(id AS VARCHAR) AS path
    FROM employees
    WHERE manager_id = 2
    
    UNION ALL
    
    SELECT e.id, e.name, e.manager_id, s.level + 1,
           s.path || ',' || e.id
    FROM employees e
    JOIN subordinates s ON e.manager_id = s.id
    WHERE s.path NOT LIKE '%,' || e.id || ',%'  -- 避免循环
)
SELECT * FROM subordinates;
```

---

## 🧠 递归 CTE vs 其他方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| 递归 CTE | 纯 SQL，无需应用层代码 | 复杂查询性能较差 |
| 应用层递归 | 灵活，可加缓存 | 代码复杂，多一次数据库往返 |
| 闭包表（Closure Table） | 查询简单，性能好 | 写入复杂，需要额外维护 |
| 路径枚举（Path Enum） | 查询简单 | 更新分类时需要同步更新路径 |

**建议：** 层级数据量不大（< 10000 条）且查询频率不高时，用递归 CTE。如果性能要求高，考虑闭包表。

---

## 🐍 在 Python 中使用递归 CTE

```python
import duckdb

con = duckdb.connect(":memory:")

# 创建员工表
con.execute("""
CREATE TABLE employees AS
SELECT * FROM (VALUES
    (1, '张三', NULL),
    (2, '李四', 1),
    (3, '王五', 1),
    (4, '赵六', 2),
    (5, '钱七', 2),
    (6, '孙八', 4)
) AS t(id, name, manager_id)
""")

# 递归查询李四的所有下属
result = con.execute("""
WITH RECURSIVE subordinates AS (
    SELECT id, name, manager_id, 1 AS level
    FROM employees
    WHERE manager_id = 2
    UNION ALL
    SELECT e.id, e.name, e.manager_id, s.level + 1
    FROM employees e
    JOIN subordinates s ON e.manager_id = s.id
)
SELECT * FROM subordinates
""").fetchdf()

print(result)
```

---

## 📝 小结

| 技能 | 一句话总结 |
|------|-----------|
| 递归 CTE 结构 | 锚点查询 + `UNION ALL` + 递归查询 |
| 层级深度控制 | 用 `level` 或 `depth` 列跟踪递归层级 |
| 防止死循环 | 加 `WHERE level < N` 或记录已访问路径 |
| 常用场景 | 组织架构、产品分类、文件目录、权限树 |

**递归 CTE 让你：一条 SQL 搞定无限层级的上下级关系，再也不用在应用层写递归代码了。**

---

## 💬 互动

你的项目中有没有处理层级数据的场景？把表结构和查询需求发出来，我们一起用递归 CTE 解决！

---

📌 收藏这条笔记，下次遇到组织架构、分类树、文件目录查询时直接回来参考。

---

🔍 想系统学习 DuckDB？duckdblab.org 上有完整教程系列，从基础查询到递归 CTE、窗口函数，带你成为 DuckDB 实战专家。
