## Cache状态

每个已访问set按需分配`ways`个line：

```text
valid
tag
owner_partid
owner_pmg
last_touch
```

未实例化set等价于全部invalid，避免默认32K set场景预分配大量Python对象。

## Lookup

```text
line_address = floor(address / line_size)
set = line_address mod sets
tag = floor(line_address / sets)
```

tag匹配任意valid way即hit。CPBM不限制已有line命中，只限制新fill选择way。

## MSHR

MSHR entry保存第一miss和waiter：

- 默认只合并同line read/read；
- 每个waiter保留自己的PARTID/PMG和CPU OSTD；
- 第一miss的PARTID/PMG决定fill owner；
- MSHR满时miss进入L3 miss资源等待状态，不额外访问MC。

关闭merge或包含write时可建立同line独立MSHR并发出重复MC请求。

## Fill

MC返回到L3时先检查fill buffer。接受后占一个entry并等待`fill_latency_ns`。

fill时：

1. 已有同tag line：记录冗余memory fetch，不修改owner；
2. 否则应用CPBM way资格；
3. CMAX达到时只允许替换请求者自己的line；
4. CMIN保护不高于最低目标的victim owner；
5. 无合法victim则旁路，不阻塞返回；
6. 完成MSHR全部waiter。

## 替换

- LRU按`last_touch`选择最旧合法way；
- PLRU使用每set的`ways-1` tree bit；bit表示优先替换分支，并对eligible mask递归选择。
- PLRU要求way数为2的幂。

## 监控

- actual occupancy扫描所有真实valid line；
- sampled occupancy只扫描`set % 8 == 0`的真实line并乘8；
- hit/miss、merge、MSHR full、fill full、eviction、self replacement、bypass和redundant fetch按PARTID记录。
