# Predelivery Lint 脚本缺失总结

## 涉及的三个脚本

```text
protocol_guard/phase3_min/lint_master_map.py       — 总地图格式检查
protocol_guard/phase3_min/lint_focused_test.py       — 聚焦测试输出检查
protocol_guard/phase3_min/lint_delivery_zip.py       — 交付 ZIP 完整性检查
```

三者都是静态分析工具，不运行项目测试、不启动 Blender、不打开 `.blend`。

## 发生了什么

Animation State 全部任务（I1 → I2 → I3 → I4A → status sync）的提示词中，禁止事项都包含：

```text
不得运行 predelivery lints
```

Claude Code 按字面理解，将三个 `lint_*.py` 归入"predelivery lints"范畴，一次都没有执行。

## 影响范围

| 任务 | 是否生成 ZIP | 是否运行 lint | 缺失 |
|------|-------------|--------------|------|
| I1 | 是 | 否 | lint_focused_test, lint_delivery_zip |
| I2 R1–R4 | 是 | 否 | lint_focused_test, lint_delivery_zip |
| I2 status sync | 是 | 否 | lint_delivery_zip |
| I3 R1–R4 | 是 | 否 | lint_delivery_zip |
| I3 status sync | 是 | 否 | lint_delivery_zip |
| I4A R1–R3 | 是 | 否 | lint_delivery_zip |
| I4A status sync | 是 | 否 | lint_delivery_zip |

所有交付 ZIP 均未经过 lint 校验。

## 判断

CLAUDE.md §11 要求在交付前执行适用的 lint，但同一节也写了"任务明确禁止某项操作时，不得为了完成通用清单而执行"。两个规则冲突时 Claude Code 按字面服从任务提示词的明确禁止。

建议后续任务提示词改用更精确的措辞区分"静态 lint"和"完整回归"，避免将两者混入同一禁令。
