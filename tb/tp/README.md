# TP层验证说明

## 测试平台概览

本目录包含TP层（传输层）的测试平台：

1. **ub_tp_transmitter_tb.v** - 发送器单独测试
2. **ub_tp_receiver_tb.v** - 接收器单独测试
3. **ub_tp_loopback_tb.v** - 发送器+接收器回环测试

## 如何运行测试

### 前置要求

- VCS仿真器或其他SystemVerilog仿真器
- 或者使用Verilator（需要修改Makefile）

### 使用VCS运行

```bash
cd tb/tp

# 运行所有测试
make all

# 单独运行发送器测试
make transmitter

# 单独运行接收器测试
make receiver

# 运行回环测试
make loopback

# 清理
make clean
```

### 查看波形

运行测试后，生成VCD波形文件：

```bash
# 用GTKWave查看
gtkwave ub_tp_transmitter_tb.vcd
gtkwave ub_tp_receiver_tb.vcd
gtkwave ub_tp_loopback_tb.vcd
```

## 测试内容

### 1. 发送器测试 (ub_tp_transmitter_tb)

验证内容：
- PSN（数据包序列号）生成和递增
- RTPH头部添加
- 重传缓冲区存储
- TPACK/TPNAK处理

### 2. 接收器测试 (ub_tp_receiver_tb)

验证内容：
- PSN检查和期望序列跟踪
- 乱序数据包缓冲
- 按顺序重排和交付
- 重复数据包检测
- TPACK/TPNAK生成

### 3. 回环测试 (ub_tp_loopback_tb)

验证内容：
- 端到端数据包传输
- 发送器→接收器连接
- 反馈路径（TPACK/TPNAK）

## 预期结果

所有测试应该显示：
- "Test PASSED!" 如果没有错误
- 数据包正确传输
- PSN按预期递增
- 没有数据不匹配

## 手动检查要点

查看波形时检查：

1. **发送器侧：**
   - `ta_valid` / `ta_ready` 握手正常
   - `tp_tx_psn` 从0开始递增
   - `tp_tx_data` 包含正确的RTPH头部

2. **接收器侧：**
   - `tp_rx_expected_psn` 正确跟踪
   - `tp_rx_valid` 在预期时间置位
   - `tp_rx_data` 与发送数据匹配

3. **反馈路径：**
   - `tp_ack_valid` / `tp_nak_valid` 正确置位
   - `tp_ack_psn` / `tp_nak_psn` 包含正确的PSN

