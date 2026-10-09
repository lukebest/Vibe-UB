# Changelog

## Unreleased

### Added

- `docs/SPEC.md`：M1 功能规格（范围、模块划分、接口、时钟复位、状态机、异常、参数、测试钩子、两套 `TEST_HOOKS` 网表）。
- `docs/REGMAP.md`：M1 寄存器表（CTRL/STATUS/PARAM/ERR/TEST + App. D 端口子集镜像）。
- `docs/CODING_STYLE.md`：pyc4.0 生成、同步复位、白名单单元、禁止 force/deposit、lint/waiver、两套网表门禁。

### Changed

- 架构关闭若干待定项：M1 单时钟 80.57 MHz、`rst_n` 封装、CSR 整字/1 拍/未映射 `csr_err`、非法 VL 丢包、信用下溢计数+irq（TB assert）、`irq` 高有效默认全屏蔽、预编码默认关、信用钩子仅 VL0、`tb_obs_lmsm_st` 仅顶层编码。
