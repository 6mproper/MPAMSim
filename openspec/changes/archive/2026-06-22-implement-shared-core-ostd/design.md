## 目标

- 模拟两个SMT线程共享core事务跟踪资源。
- 保持线程激励和thread OSTD独立。
- 让CBusy只作用于匹配目标MC和PARTID的新准入。
- 让阻塞原因和core状态可观察。

## Core OSTD状态

每个core保存：

- total limit、current和interval peak；
- 每thread current；
- pending thread集合；
- 上次grant thread；
- policy和reserve。

### shared

所有线程共享core总entry，每个线程仍受自己的thread limit。

### static_partition

core limit按稳定thread顺序静态划分，线程不能借用其他份额。

### reserve_borrow

每个线程保留`thread_ostd_reserve`。线程可使用自己的reserve；超过reserve后只能使用
未被其他线程保留的core空间。

## Round-robin

generator生成待发描述并标记pending。Core pool在本轮满足本地限制的pending线程之间，
从上次grant后开始轮询。无其他eligible线程时当前线程立即前进。

## 目标MC

地址生成后用当前MC interleave函数解析home MC。待发描述在重试期间保持不变，
transaction ID只在准入成功后分配。

CBusy有效上限只读取该home MC对PARTID的反馈。UI聚合显示仍可报告最高档，但准入判断
不跨MC传播。

## 完成

L3 hit和MC完成都使用transaction中预解析的home MC释放：

- requester thread OSTD；
- requester `(PARTID, MC)` OSTD；
- core total和thread计数。

## 监控

现有每requester/PARTID行增加core ID、core current/peak/limit、policy和各类stall。
另导出每requester、PARTID、目标MC的current、issued、completed、CBusy和stall。
