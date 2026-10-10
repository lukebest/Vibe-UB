"""Golden-model constants from the YAML regmap (tb-selfcheck collects model/)."""

from __future__ import annotations

from model import regs


def test_word_and_align():
    assert regs.WORD_BITS == 32
    assert regs.ADDR_BITS == 16
    assert regs.ALIGN_BYTES == 4
    assert regs.READ_LATENCY_CYCLES == 1


def test_param_variant_address_and_reset_word():
    assert regs.PARAM_VARIANT == 0x011C
    assert regs.PARAM_VARIANT_NUM_VL_LSB == 0
    assert regs.PARAM_VARIANT_SCR_PLACEHOLDER_LSB == 4
    assert regs.VARIANT_PRODUCT_X4_VL2_PARAM_VARIANT_RESET == 0x02
    assert regs.VARIANT_PRODUCT_X8_VL2_PARAM_VARIANT_RESET == 0x02
    assert regs.VARIANT_X4_VL2_PLACEHOLDER_PARAM_VARIANT_RESET == 0x12
    assert regs.VARIANT_X8_VL2_PLACEHOLDER_PARAM_VARIANT_RESET == 0x12
