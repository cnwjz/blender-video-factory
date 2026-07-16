# Human Review Checklist — Phase 1: Mechanism & Shot Locking

Project: `bvf_test_001_checkout_bottleneck`
Status: `planned`
Review Date: (pending)

---

## 1. Silent Understanding (静音理解)

- [ ] 第一秒能看出有三个收银窗口和三条队伍
- [ ] 两秒左右能看出中间窗口关闭
- [ ] 六秒前能看出顾客向剩余窗口分流
- [ ] 九秒前能看出剩余队伍明显变长
- [ ] 最终能理解"窗口减少导致队伍拥堵"

## 2. First Frame Impact (第一秒识别)

- [ ] 第一秒存在清楚空间和人物动作
- [ ] 竖屏主体足够大
- [ ] 三个窗口和三条队伍一目了然
- [ ] 不出现大面积无意义空白
- [ ] 不依赖小字说明

## 3. Window Close Status (关闭状态)

- [ ] 中间窗口关闭通过实体视觉变化表达
- [ ] 至少满足两项：灯牌熄灭 / 挡板落下 / 颜色变暗
- [ ] 无声观看即可理解窗口不再可用
- [ ] 中间队伍明显停止/停顿

## 4. Diversion Direction (分流方向)

- [ ] 中间队伍向左分流的方向清楚
- [ ] 中间队伍向右分流的方向清楚
- [ ] 左右队伍后方有新顾客加入
- [ ] 分流过程中无人物穿模

## 5. Character Count & Queue Growth (人物数量 & 队伍变化)

- [ ] Shot 1: 三条队伍长度相近，各 2-3 人
- [ ] Shot 3: 左右队伍长度明显增长
- [ ] Shot 4: 每条队伍 4-5 人以上
- [ ] 总人数不超过 15 人
- [ ] 队伍间距合理，不粘连

## 6. Final Result (最终结果)

- [ ] 两条队伍明显长于 Shot 1
- [ ] 中间窗口保持空置
- [ ] 队伍前进速度可见变慢
- [ ] 最终画面稳定停留 >= 0.8 秒
- [ ] 无声即可理解因果闭环

## 7. Visual Quality (画面质量)

- [ ] 不像三维灰盒作业
- [ ] 不像软件 Demo
- [ ] 不像素材拼装
- [ ] 颜色不超过规定范围
- [ ] 灯光分离人物和柜台
- [ ] 阴影不过黑

## 8. Technical (三维技术)

- [ ] 人物不穿模
- [ ] 人物不漂浮
- [ ] 移动速度稳定
- [ ] 镜头不眩晕
- [ ] 物体比例统一
- [ ] 输出无缺帧和黑帧

---

## Review Decision

- [ ] **Pass** — 可以进入阶段 2 灰盒场景
- [ ] **Pass with minor revisions** — 局部修改后可进入阶段 2
- [ ] **Major revision required** — 需要重新设计机制表达
- [ ] **Fail** — 机制无法在无声条件下理解

Review Notes:
(留空，人工审核时填写)
