# UB TP层（传输层）设计规范

**日期：** 2026-03-30
**状态：** 草案
**目标：** Vibe-UB项目，仅RTP模式（简化版本）

## 1. 概述

本文档规定了Vibe-UB项目的传输层（TP）设计。它实现了UB基础规范版本2.0中规定的简化RTP（可靠传输）模式。

### 1.1 范围

此实现专注于最小可行的RTP功能：
- PSN（数据包序列号）生成和跟踪
- 基础重传机制
- TPACK/TPNAK处理
- 乱序数据包检测和缓冲

TPSACK、拥塞控制、多通道支持和TPG等高级功能将在未来迭代中添加。

### 1.2 参考

- UB基础规范版本2.0，第6节（传输层）
- Vibe-UB项目中现有的DLL和PCS层代码

## 2. 架构

### 2.1 协议栈位置

```
TA层（事务层）
    ↑
TP层（传输层）← 本层
    ↑
NL层（网络层）
    ↑
DLL层（数据链路层）
    ↑
PCS/PHY层
```

### 2.2 模块层次

```
ub_controller_tx/rx（顶层）
    └── ub_tp_controller_tx/rx（TP顶层）
            ├── ub_tp_transmitter（RTP发送器）
            └── ub_tp_receiver（RTP接收器）
```

### 2.3 目录结构

```
rtl/
├── tp/
│   ├── ub_tp_transmitter.v      # RTP发送器
│   ├── ub_tp_receiver.v        # RTP接收器
│   ├── ub_tp_controller_tx.v   # TP TX控制器
│   └── ub_tp_controller_rx.v   # TP RX控制器
├── dll/                          （已存在）
├── pcs/                          （已存在）
├── ub_controller_tx.v
└── ub_controller_rx.v

tb/
└── tp/                           （新建测试平台）
    ├── ub_tp_transmitter_tb.v
    ├── ub_tp_receiver_tb.v
    └── ub_tp_loopback_tb.v
```

## 3. 接口定义

### 3.1 接口风格

所有接口都遵循与现有DLL和PCS层相同的ready/valid握手模式：
- `clk, rst_n`：时钟和低电平复位
- `valid`：表示总线上有效数据
- `ready`：表示接收器准备好接受数据
- `sop`：数据包起始（事务的第一个flit）
- `eop`：数据包结束（事务的最后一个flit）
- `data[159:0]`：160位（20字节）flit数据

### 3.2 TA层 → TP层（TA-TP TX接口）

从事务层到TP发送器的接口：

```systemverilog
// TA → TP（事务层到TP发送器）
input  [159:0] ta_data,        // 事务数据（flit）
input        ta_valid,         // TA数据有效
input        ta_sop,           // 事务数据包起始
input        ta_eop,           // 事务数据包结束
output       ta_ready,         // TP准备好接受

// TP → TA（发送器侧状态）
output [23:0] tp_tx_psn,        // 正在发送的当前PSN
output        tp_tx_busy,       // 发送器忙（缓冲区满）
```

### 3.3 TP层 → NL层（TP-NL TX接口）

从TP发送器到网络层的接口：

```systemverilog
// TP → NL（TP发送器到网络层）
output [159:0] tp_tx_data,       // TP数据包数据（带RTPH）
output        tp_tx_valid,      // TP数据有效
output        tp_tx_sop,        // TP数据包起始
output        tp_tx_eop,        // TP数据包结束
input         tp_tx_ready,      // NL准备好接受
```

### 3.4 NL层 → TP层（NL-TP RX接口）

从网络层到TP接收器的接口：

```systemverilog
// NL → TP（网络层到TP接收器）
input  [159:0] nl_rx_data,       // 接收的TP数据包数据
input         nl_rx_valid,      // NL数据有效
input         nl_rx_sop,        // 接收的TP数据包起始
input         nl_rx_eop,        // 接收的TP数据包结束
output        nl_rx_ready,      // TP准备好接受
```

### 3.5 TP层 → TA层（TP-TA RX接口）

从TP接收器到事务层的接口：

```systemverilog
// TP → TA（TP接收器到事务层）
output [159:0] tp_rx_data,       // 接收的事务数据
output        tp_rx_valid,      // TP数据有效
output        tp_rx_sop,        // 事务数据包起始
output        tp_rx_eop,        // 事务数据包结束
input         tp_rx_ready,      // TA准备好接受

// TP → TA（接收器侧状态）
output [23:0] tp_rx_expected_psn, // 下一个期望的PSN
output        tp_rx_drop,        // 数据包丢弃（检测到PSN跳跃）
output        tp_rx_dup,         // 收到重复数据包
```

### 3.6 TP接收器 → TP发送器（反馈接口）

TPACK/TPNAK反馈的内部接口：

```systemverilog
// TP接收器 → TP发送器（反馈）
output [23:0] tp_ack_psn,       // 正在确认的PSN
output        tp_ack_valid,     // TPACK有效
output [23:0] tp_nak_psn,       // 正在NAK的PSN
output        tp_nak_valid,     // TPNAK有效
```

## 4. RTP头部（RTPH）格式

### 4.1 RTPH结构（共16字节）

参见UB-TP.md第6.2.1节，图6-8。

```
字节0-3：
  [7:0]   TPOpcode     // 传输操作码（RTP数据为0x00）
  [9:8]   TPVer        // 传输版本（2'b00）
  [11:10] Padding      // 填充位
  [15:12] NLP          // 下一层协议

字节4-7：
  [23:0]  SrcTPN       // 源TPEP标识符（24位）

字节8-11：
  [23:0]  DstTPN       // 目标TPEP标识符（24位）

字节12-15：
  [31:24] Reserved     // 保留位
  [23:0]  PSN          // 数据包序列号（24位）
```

### 4.2 TPOpcode值

- `0x00`：RTP数据包
- `0x01`：TPACK（确认）
- `0x02`：TPNAK（否定确认）

此简化实现仅处理`0x00`（数据）并生成/处理`0x01`（TPACK）和`0x02`（TPNAK）。

## 5. 模块规格

### 5.1 ub_tp_transmitter（RTP发送器）

**职责：**
1. 接受来自TA层的事务数据
2. 添加带PSN的RTPH头部
3. 将数据包存储在重传缓冲区
4. 将数据包转发到NL层
5. 处理来自接收器的TPACK/TPNAK
6. 按需重传数据包

**关键参数：**
- `PSN_BITS`：24位
- `RETRANSMIT_BUFFER_DEPTH`：32个条目（可配置）
- `MAX_RETRIES`：3（可配置）

**内部状态：**
- `current_psn[23:0]`：下一个要分配的PSN
- `retransmit_buffer`：存储等待ACK的数据包的缓冲区数组
- `retry_counters`：每个缓冲数据包的重试计数

**输入/输出：**
参见第3.2、3.3和3.6节。

### 5.2 ub_tp_receiver（RTP接收器）

**职责：**
1. 接受来自NL层的TP数据包
2. 剥离RTPH头部
3. 检查PSN的期望序列
4. 缓冲乱序数据包
5. 重排并按顺序交付到TA层
6. 检测重复数据包
7. 为成功接收生成TPACK
8. 为丢失的数据包生成TPNAK

**关键参数：**
- `PSN_BITS`：24位
- `REORDER_BUFFER_DEPTH`：32个条目（可配置）

**内部状态：**
- `expected_psn[23:0]`：下一个期望的PSN
- `reorder_buffer`：存储乱序数据包的缓冲区数组
- `received_bitmap`：跟踪已接收数据包的位图

**输入/输出：**
参见第3.4、3.5和3.6节。

### 5.3 ub_tp_controller_tx（TP TX控制器）

**职责：**
1. 实例化`ub_tp_transmitter`
2. 将TA层接口连接到发送器
3. 将发送器连接到NL层接口
4. 将来自TP接收器的反馈连接到发送器

### 5.4 ub_tp_controller_rx（TP RX控制器）

**职责：**
1. 实例化`ub_tp_receiver`
2. 将NL层接口连接到接收器
3. 将接收器连接到TA层接口
4. 将来自接收器的反馈连接到发送器

## 6. 数据流

### 6.1 发送路径（TA → TP → NL）

1. TA层通过`ta_valid/ta_sop/ta_eop`呈现事务数据
2. TP发送器：
   - 当`ta_ready`为高时接受数据
   - 分配PSN（从0递增）
   - 前置RTPH头部
   - 将副本存储在重传缓冲区
   - 通过`tp_tx_valid/tp_tx_sop/tp_tx_eop`呈现给NL层
3. 当`tp_tx_ready`为高时，NL层接受数据

### 6.2 接收路径（NL → TP → TA）

1. NL层通过`nl_rx_valid/nl_rx_sop/nl_rx_eop`呈现TP数据包
2. TP接收器：
   - 当`nl_rx_ready`为高时接受数据
   - 剥离RTPH头部
   - 提取PSN
   - 如果PSN == expected_psn：
     - 立即交付到TA层
     - 递增expected_psn
     - 检查重排序缓冲区中的下一个数据包
     - 生成TPACK
   - 否则如果PSN > expected_psn：
     - 存储在重排序缓冲区
     - 为丢失的PSN生成TPNAK
   - 否则（PSN < expected_psn）：
     - 作为重复丢弃（或者如果报告了间隙则接受）
3. 当`tp_rx_ready`为高时，TA层接受数据

### 6.3 重传流程

1. TP接收器检测到丢失的数据包（PSN间隙）
2. TP接收器为丢失的PSN生成TPNAK
3. TP发送器接收TPNAK
4. TP发送器从重传缓冲区检索数据包
5. TP发送器重传该数据包
6. TP接收器接收重传的数据包
7. TP接收器按顺序交付到TA层
8. TP接收器生成TPACK

## 7. 测试策略

### 7.1 模块级测试

- `ub_tp_transmitter_tb.v`：验证PSN生成、头部插入、缓冲区存储
- `ub_tp_receiver_tb.v`：验证PSN检查、重排序、TPACK/TPNAK生成
- `ub_tp_loopback_tb.v`：带数据包丢失和重传的端到端回环测试

### 7.2 测试用例

1. 基础数据包传输（无丢失）
2. 乱序数据包接收
3. 丢失数据包检测和重传
4. 重复数据包检测
5. 背压处理（ready/valid流控）

## 8. 配置参数

所有可配置参数定义为模块参数：

```systemverilog
parameter PSN_BITS        = 24,    // PSN位宽
parameter RETRANSMIT_DEPTH = 32,   // 重传缓冲区深度
parameter REORDER_DEPTH    = 32,   // 重排序缓冲区深度
parameter MAX_RETRIES      = 3     // 最大重传尝试次数
```

## 9. 未来增强

这是一个简化的RTP实现。未来迭代可能添加：

- TPSACK（选择性确认）
- 拥塞控制（CNP处理）
- 多TP通道
- TPG（传输通道组）支持
- CTP和UTP模式
- TP旁路模式

