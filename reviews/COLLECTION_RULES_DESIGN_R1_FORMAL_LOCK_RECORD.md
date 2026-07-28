# Collection Rules Design R1 正式锁定记录

```text
DOCUMENT_ID: COLLECTION_RULES_DESIGN_R1_FORMAL_LOCK_RECORD
TASK_ID: COLLECTION_RULES_DESIGN_FORMAL_LOCK_SYNC
DESIGN_VERSION: R1
DESIGN_FILE: reviews/COLLECTION_RULES_DESIGN_R1.md
DESIGN_SHA256: 1FFE22B6C020D24B60BCFF2E36EFAD9365266D659139928A9E4B5AD732EAB062
SOURCE_MASTER_MAP_VERSION: R70
TARGET_MASTER_MAP_VERSION: R71
LOCK_BASIS: USER_FORMAL_APPROVAL
LOCK_APPROVAL_DATE: 2026-07-25
INDEPENDENT_REVIEW_STATUS: ALL_CHECKS_PASS
TRUE_BLOCKING_ISSUES: 0
FORMALLY_LOCKED: TRUE
IMPLEMENTATION_AUTHORIZED: FALSE
IMPLEMENTATION_STARTED: FALSE
```

## 用户批准

```text
用户于 2026-07-25 明确批准正式锁定 Collection Rules Design R1。
```

## GPT 独立审核结论

```text
DESIGN_REVIEW_STATUS: ACCEPTED_WITH_MINOR_NOTES
TRUE_BLOCKING_ISSUES: 0
R3_DESIGN_CORRECTION_REQUIRED: FALSE
```

## 锁定范围

Collection Rules Design R1 已裁定以下内容为正式设计：

```text
1. 全局和 per-target 两层规则关系:
   TWO_COMPATIBLE_RULE_LAYERS，独立启用，独立输出。

2. collection_rules 和 target.required_collection_names
   的配置、缺失、null、空数组和启用语义:
   - collection_rules 缺失/null → 不创建 global_results key，不读 bpy
   - collection_rules: {} → 两个子检查均 NOT_CHECKED
   - required_collection_names 缺失/null/[] → NOT_CHECKED
   - forbidden_collection_name_patterns 缺失/null/[] → NOT_CHECKED
   - 非空数组 → 启用对应子检查
   - per-target required_collection_names 缺失/null/[] → NOT_CHECKED
   - 非空数组 → 进入 root 前置判定

3. global_results.collection_rules 精确结构:
   - 顶层 result + required 子检查 + forbidden 子检查
   - PASS: required_names, missing_names, forbidden_patterns, matched_collections
   - FAIL: COLLECTION_RULES_FAILURE, 附带子检查 FAIL 详情
   - ERROR: COLLECTION_RULES_COMPUTATION_ERROR, 两个子检查短路为 NOT_CHECKED

4. checks.collection_membership 精确结构:
   - required_names, direct_collections, ancestor_collections,
     matched_names, missing_names
   - PASS: 至少一个 matched
   - FAIL: TARGET_NOT_IN_REQUIRED_COLLECTION

5. required Collection 存在性检查:
   bpy.data.collections.get(name) 语义, 缺失 → FAIL

6. forbidden Collection glob 检查及 casefold 语义:
   casefold_glob_match, 匹配 → FAIL

7. object.users_collection 直接成员关系:
   只返回对象直接所属 Collection，Collection 没有 users_collection 属性

8. collection.children child-to-parent 反向索引:
   从直接 Collection 向上计算祖先闭包

9. 多父级、visited identity 和递归祖先闭包:
   每个 collection 的 parent 列表，防重复访问

10. Scene 外 Collection 可以满足归属条件的 OPTION_B:
    允许 bpy.data.collections 全量搜索

11. root 独立解析方式和前置结果复用:
    不修改 _check_root_objects()，复用 checks.object_type.actual

12. PASS、FAIL、ERROR、NOT_CHECKED 矩阵:
    全局层 10 种场景，per-target 层 9 种场景

13. 精确 failure_code 集合 (4 个):
    REQUIRED_COLLECTION_MISSING, FORBIDDEN_COLLECTION_MATCHED,
    COLLECTION_RULES_FAILURE, TARGET_NOT_IN_REQUIRED_COLLECTION

14. 精确 ERROR type 和 operation 集合 (9 个):
    G1-G5 (global), P1-P4 (per-target)

15. 属性读取次数和缓存合同:
    每属性最大读取次数，缓存策略，不跨 target 复用 ancestor_index

16. 生产函数边界和集成顺序:
    _check_collection_rules_global, _check_collection_membership,
    _materialize_collection_ancestor_index, _compute_ancestor_closure,
    _resolve_root_for_collection_rules

17. Scope Guard 合同:
    5 个授权函数, 4 个保护属性, forbidden_always 列表

18. CPython 测试矩阵:
    I1 涵盖 config/global/per-target/pass-fail-notchecked

19. Blender 5.1.2 临时场景矩阵:
    13 scenarios (CR-I4B-01 到 CR-I4B-13)

20. I1、I2、I3、I4A、I4B、E 实施拆分:
    每阶段范围、文件、测试和排除项
```

## 锁定边界

```text
本次只锁定 Collection Rules Design R1。

本次不代表:
  — Collection Rules 生产实现已经开始
  — I1 已获得实施授权
  — Collection Rules 字段组已经完成
  — Collection Rules 字段组已经最终正式锁定

LOCKED_TASKS_MUST_NOT_BE_REDESIGNED: TRUE
FUTURE_CHANGES_REQUIRE_NEW_EXPLICIT_TASK_AND_REVIEW: TRUE
IMPLEMENTATION_AUTHORIZED: FALSE
IMPLEMENTATION_STARTED: FALSE

不得修改:
  — 14A Core schema
  — _check_root_objects()
  — 任何既有锁定字段组
  — 现有 target overall 聚合语义
  — global_results.scene_basic
  — 其他字段组生产代码或测试
```

## 锁定不包含

```text
— Collection 内部对象结构验证（属于 Hierarchy）
— Collection 视觉外观
— Collection 可见性设置（属于 Visibility）
— 真实项目 .blend 验证
— Append / Link 操作
— 角色库文件路径验证
— 保存重开后的 Collection 持久化
— 生产实现代码
— 运行时测试
— Blender 验证
— Scope Guard 实现
```
