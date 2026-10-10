"""UB M1 uvm-python register model. GENERATED — edit docs/regmap/regmap.yaml

Lives at tb/ral/ub_regmodel.py (PR #6 tb/ is on main).

Assumptions: uvm-python (tpoikela/uvm-python / lukebest/uvm-python) UVMReg,
UVMRegField.configure(parent, size, lsb_pos, access, volatile, reset,
has_reset, is_rand, individually_accessible). MIX/NA App. D windows are
address placeholders only (REGMAP §3).

create_ub_regmodel(variant=) applies variants: table resets (SPEC §2.2).
"""

from __future__ import annotations

DEFAULT_VARIANT = 'product_x4_vl2'
VARIANTS = {'product_x4_vl2': {'NUM_LANES': 4, 'NUM_VL': 2, 'SCR_PLACEHOLDER': 0}, 'product_x8_vl2': {'NUM_LANES': 8, 'NUM_VL': 2, 'SCR_PLACEHOLDER': 0}, 'x4_vl2_placeholder': {'NUM_LANES': 4, 'NUM_VL': 2, 'SCR_PLACEHOLDER': 1}, 'x8_vl2_placeholder': {'NUM_LANES': 8, 'NUM_VL': 2, 'SCR_PLACEHOLDER': 1}}
CSR_MODULE = {'product_x4_vl2': 'ub_csr_product_x4_vl2', 'product_x8_vl2': 'ub_csr_product_x8_vl2', 'x4_vl2_placeholder': 'ub_csr_x4_vl2_placeholder', 'x8_vl2_placeholder': 'ub_csr_x8_vl2_placeholder'}

try:
    from uvm.macros import uvm_object_utils
    from uvm.reg import UVMReg, UVMRegBlock, UVMRegField
    HAVE_UVM = True
except ImportError:  # pragma: no cover - uvm-python not required to import
    HAVE_UVM = False

    def uvm_object_utils(_cls):
        return _cls

    class UVMReg:
        def __init__(self, name, n_bits, has_coverage=0):
            self.get_name = lambda: name
            self.n_bits = n_bits
            self._fields = []

        def add_field(self, field):
            self._fields.append(field)

    class UVMRegField:
        class type_id:
            @staticmethod
            def create(name):
                obj = UVMRegField()
                obj.get_name = lambda n=name: n
                return obj

        def configure(self, parent, size, lsb_pos, access, volatile, reset,
                      has_reset, is_rand, individually_accessible):
            self.size = size
            self.lsb_pos = lsb_pos
            self.access = access
            self.volatile = volatile
            self.reset = reset
            self.has_reset = has_reset
            if parent is not None:
                parent.add_field(self)

    class UVMRegBlock:
        def __init__(self, name):
            self.get_name = lambda: name
            self.default_map = None
            self._regs = []

        def create_map(self, name, base_addr, n_bytes, endian, byte_addressing=1):
            self.default_map = _Map(name, base_addr, n_bytes, endian)
            return self.default_map

        def lock_model(self):
            self.locked = True

    class _Map:
        def __init__(self, name, base_addr, n_bytes, endian):
            self.name = name
            self.base_addr = base_addr
            self.n_bytes = n_bytes
            self.endian = endian
            self.entries = []

        def add_reg(self, reg, offset, rights, unmapped=0):
            self.entries.append((reg, offset, rights, unmapped))


class ub_ctrl_reg(UVMReg):
    def __init__(self, name="CTRL"):
        super().__init__(name, 32, 0)
        self.PORT_RST = UVMRegField.type_id.create('PORT_RST')
        self.LMSM_START = UVMRegField.type_id.create('LMSM_START')
        self.IRQ_EN = UVMRegField.type_id.create('IRQ_EN')
        self.RSVD = UVMRegField.type_id.create('RSVD')

    def build(self, variant=None):
        self.PORT_RST.configure(self, 1, 0, 'WO', 1, 0, 1, 1, 0)
        self.LMSM_START.configure(self, 1, 1, 'RW', 0, 0, 1, 1, 0)
        self.IRQ_EN.configure(self, 1, 2, 'RW', 0, 0, 1, 1, 0)
        self.RSVD.configure(self, 29, 3, 'RO', 1, 0, 1, 1, 0)


ub_ctrl_reg = uvm_object_utils(ub_ctrl_reg)


class ub_status_reg(UVMReg):
    def __init__(self, name="STATUS"):
        super().__init__(name, 32, 0)
        self.LINK_UP = UVMRegField.type_id.create('LINK_UP')
        self.LINK_READY = UVMRegField.type_id.create('LINK_READY')
        self.DLL_STATUS_UP = UVMRegField.type_id.create('DLL_STATUS_UP')
        self.LMSM_ST = UVMRegField.type_id.create('LMSM_ST')
        self.DLL_SM_ST = UVMRegField.type_id.create('DLL_SM_ST')
        self.RETRY_REQ_ST = UVMRegField.type_id.create('RETRY_REQ_ST')
        self.RETRY_ACK_ST = UVMRegField.type_id.create('RETRY_ACK_ST')
        self.RSVD = UVMRegField.type_id.create('RSVD')

    def build(self, variant=None):
        self.LINK_UP.configure(self, 1, 0, 'RO', 1, 0, 1, 1, 0)
        self.LINK_READY.configure(self, 1, 1, 'RO', 1, 0, 1, 1, 0)
        self.DLL_STATUS_UP.configure(self, 1, 2, 'RO', 1, 0, 1, 1, 0)
        self.LMSM_ST.configure(self, 5, 3, 'RO', 1, 0, 1, 1, 0)
        self.DLL_SM_ST.configure(self, 2, 8, 'RO', 1, 0, 1, 1, 0)
        self.RETRY_REQ_ST.configure(self, 3, 10, 'RO', 1, 0, 1, 1, 0)
        self.RETRY_ACK_ST.configure(self, 2, 13, 'RO', 1, 0, 1, 1, 0)
        self.RSVD.configure(self, 17, 15, 'RO', 1, 0, 1, 1, 0)


ub_status_reg = uvm_object_utils(ub_status_reg)


class ub_irq_status_reg(UVMReg):
    def __init__(self, name="IRQ_STATUS"):
        super().__init__(name, 32, 0)
        self.FEC_UNCORR = UVMRegField.type_id.create('FEC_UNCORR')
        self.CRC_FAIL = UVMRegField.type_id.create('CRC_FAIL')
        self.RETRY_ERR = UVMRegField.type_id.create('RETRY_ERR')
        self.CRD_PROTO = UVMRegField.type_id.create('CRD_PROTO')
        self.TRAIN_FAIL = UVMRegField.type_id.create('TRAIN_FAIL')
        self.BAD_VL = UVMRegField.type_id.create('BAD_VL')
        self.CRD_UF = UVMRegField.type_id.create('CRD_UF')
        self.RSVD = UVMRegField.type_id.create('RSVD')

    def build(self, variant=None):
        self.FEC_UNCORR.configure(self, 1, 0, 'W1C', 1, 0, 1, 1, 0)
        self.CRC_FAIL.configure(self, 1, 1, 'W1C', 1, 0, 1, 1, 0)
        self.RETRY_ERR.configure(self, 1, 2, 'W1C', 1, 0, 1, 1, 0)
        self.CRD_PROTO.configure(self, 1, 3, 'W1C', 1, 0, 1, 1, 0)
        self.TRAIN_FAIL.configure(self, 1, 4, 'W1C', 1, 0, 1, 1, 0)
        self.BAD_VL.configure(self, 1, 5, 'W1C', 1, 0, 1, 1, 0)
        self.CRD_UF.configure(self, 1, 6, 'W1C', 1, 0, 1, 1, 0)
        self.RSVD.configure(self, 25, 7, 'RO', 1, 0, 1, 1, 0)


ub_irq_status_reg = uvm_object_utils(ub_irq_status_reg)


class ub_irq_mask_reg(UVMReg):
    def __init__(self, name="IRQ_MASK"):
        super().__init__(name, 32, 0)
        self.MASK = UVMRegField.type_id.create('MASK')
        self.RSVD = UVMRegField.type_id.create('RSVD')

    def build(self, variant=None):
        self.MASK.configure(self, 7, 0, 'RW', 0, 127, 1, 1, 0)
        self.RSVD.configure(self, 25, 7, 'RO', 1, 0, 1, 1, 0)


ub_irq_mask_reg = uvm_object_utils(ub_irq_mask_reg)


class ub_port_cna_reg(UVMReg):
    def __init__(self, name="PORT_CNA"):
        super().__init__(name, 32, 0)
        self.CNA = UVMRegField.type_id.create('CNA')

    def build(self, variant=None):
        self.CNA.configure(self, 32, 0, 'RW', 0, 0, 1, 1, 0)


ub_port_cna_reg = uvm_object_utils(ub_port_cna_reg)


class ub_param_phy_reg(UVMReg):
    def __init__(self, name="PARAM_PHY"):
        super().__init__(name, 32, 0)
        self.PHY_MODE = UVMRegField.type_id.create('PHY_MODE')
        self.DATA_RATE = UVMRegField.type_id.create('DATA_RATE')
        self.NUM_LANES_TX = UVMRegField.type_id.create('NUM_LANES_TX')
        self.NUM_LANES_RX = UVMRegField.type_id.create('NUM_LANES_RX')
        self.PMA_W = UVMRegField.type_id.create('PMA_W')
        self.ALLOW_ASYM = UVMRegField.type_id.create('ALLOW_ASYM')
        self.RSVD = UVMRegField.type_id.create('RSVD')

    def build(self, variant=None):
        params = VARIANTS[variant or DEFAULT_VARIANT]
        self.PHY_MODE.configure(self, 2, 0, 'RO', 1, 2, 1, 1, 0)
        self.DATA_RATE.configure(self, 4, 2, 'RO', 1, 0, 1, 1, 0)
        self.NUM_LANES_TX.configure(self, 4, 6, 'RO', 1, int(params['NUM_LANES']), 1, 1, 0)
        self.NUM_LANES_RX.configure(self, 4, 10, 'RO', 1, int(params['NUM_LANES']), 1, 1, 0)
        self.PMA_W.configure(self, 8, 14, 'RO', 1, 32, 1, 1, 0)
        self.ALLOW_ASYM.configure(self, 1, 22, 'RO', 1, 0, 1, 1, 0)
        self.RSVD.configure(self, 9, 23, 'RO', 1, 0, 1, 1, 0)


ub_param_phy_reg = uvm_object_utils(ub_param_phy_reg)


class ub_param_fec_reg(UVMReg):
    def __init__(self, name="PARAM_FEC"):
        super().__init__(name, 32, 0)
        self.FEC_MODE = UVMRegField.type_id.create('FEC_MODE')
        self.CODEC_NUM = UVMRegField.type_id.create('CODEC_NUM')
        self.RSVD = UVMRegField.type_id.create('RSVD')

    def build(self, variant=None):
        self.FEC_MODE.configure(self, 3, 0, 'RO', 1, 2, 1, 1, 0)
        self.CODEC_NUM.configure(self, 2, 3, 'RO', 1, 1, 1, 1, 0)
        self.RSVD.configure(self, 27, 5, 'RO', 1, 0, 1, 1, 0)


ub_param_fec_reg = uvm_object_utils(ub_param_fec_reg)


class ub_param_dll_reg(UVMReg):
    def __init__(self, name="PARAM_DLL"):
        super().__init__(name, 32, 0)
        self.NUM_VL = UVMRegField.type_id.create('NUM_VL')
        self.FLOW_CTRL_SIZE = UVMRegField.type_id.create('FLOW_CTRL_SIZE')
        self.ACK_GRAIN = UVMRegField.type_id.create('ACK_GRAIN')
        self.CREDIT_EXCL = UVMRegField.type_id.create('CREDIT_EXCL')
        self.RSVD = UVMRegField.type_id.create('RSVD')

    def build(self, variant=None):
        params = VARIANTS[variant or DEFAULT_VARIANT]
        self.NUM_VL.configure(self, 5, 0, 'RO', 1, int(params['NUM_VL']), 1, 1, 0)
        self.FLOW_CTRL_SIZE.configure(self, 8, 5, 'RO', 1, 1, 1, 1, 0)
        self.ACK_GRAIN.configure(self, 8, 13, 'RO', 1, 32, 1, 1, 0)
        self.CREDIT_EXCL.configure(self, 1, 21, 'RO', 1, 1, 1, 1, 0)
        self.RSVD.configure(self, 10, 22, 'RO', 1, 0, 1, 1, 0)


ub_param_dll_reg = uvm_object_utils(ub_param_dll_reg)


class ub_param_retry_reg(UVMReg):
    def __init__(self, name="PARAM_RETRY"):
        super().__init__(name, 32, 0)
        self.RETRY_BUF_DEPTH = UVMRegField.type_id.create('RETRY_BUF_DEPTH')
        self.NUM_RETRY_TH = UVMRegField.type_id.create('NUM_RETRY_TH')
        self.NUM_PHY_REINIT_TH = UVMRegField.type_id.create('NUM_PHY_REINIT_TH')

    def build(self, variant=None):
        self.RETRY_BUF_DEPTH.configure(self, 16, 0, 'RO', 1, 256, 1, 1, 0)
        self.NUM_RETRY_TH.configure(self, 8, 16, 'RO', 1, 15, 1, 1, 0)
        self.NUM_PHY_REINIT_TH.configure(self, 8, 24, 'RO', 1, 4, 1, 1, 0)


ub_param_retry_reg = uvm_object_utils(ub_param_retry_reg)


class ub_param_crd_reg(UVMReg):
    def __init__(self, name="PARAM_CRD"):
        super().__init__(name, 32, 0)
        self.INIT_CRD = UVMRegField.type_id.create('INIT_CRD')
        self.CRD_BP_TH = UVMRegField.type_id.create('CRD_BP_TH')

    def build(self, variant=None):
        self.INIT_CRD.configure(self, 16, 0, 'RO', 1, 640, 1, 1, 0)
        self.CRD_BP_TH.configure(self, 16, 16, 'RO', 1, 1024, 1, 1, 0)


ub_param_crd_reg = uvm_object_utils(ub_param_crd_reg)


class ub_param_init_feature_reg(UVMReg):
    def __init__(self, name="PARAM_INIT_FEATURE"):
        super().__init__(name, 32, 0)
        self.FEATURE_ID = UVMRegField.type_id.create('FEATURE_ID')
        self.RXBUF_VL_SHARE = UVMRegField.type_id.create('RXBUF_VL_SHARE')
        self.VL_ENABLE = UVMRegField.type_id.create('VL_ENABLE')

    def build(self, variant=None):
        self.FEATURE_ID.configure(self, 16, 0, 'RO', 1, 1, 1, 1, 0)
        self.RXBUF_VL_SHARE.configure(self, 1, 16, 'RO', 1, 0, 1, 1, 0)
        self.VL_ENABLE.configure(self, 15, 17, 'RO', 1, 3, 1, 1, 0)


ub_param_init_feature_reg = uvm_object_utils(ub_param_init_feature_reg)


class ub_param_init_vl_reg(UVMReg):
    def __init__(self, name="PARAM_INIT_VL"):
        super().__init__(name, 32, 0)
        self.VL_ENABLE = UVMRegField.type_id.create('VL_ENABLE')
        self.RSVD = UVMRegField.type_id.create('RSVD')

    def build(self, variant=None):
        self.VL_ENABLE.configure(self, 16, 0, 'RO', 1, 3, 1, 1, 0)
        self.RSVD.configure(self, 16, 16, 'RO', 1, 0, 1, 1, 0)


ub_param_init_vl_reg = uvm_object_utils(ub_param_init_vl_reg)


class ub_param_variant_reg(UVMReg):
    def __init__(self, name="PARAM_VARIANT"):
        super().__init__(name, 32, 0)
        self.NUM_VL = UVMRegField.type_id.create('NUM_VL')
        self.SCR_PLACEHOLDER = UVMRegField.type_id.create('SCR_PLACEHOLDER')
        self.RSVD = UVMRegField.type_id.create('RSVD')

    def build(self, variant=None):
        params = VARIANTS[variant or DEFAULT_VARIANT]
        self.NUM_VL.configure(self, 4, 0, 'RO', 1, int(params['NUM_VL']), 1, 1, 0)
        self.SCR_PLACEHOLDER.configure(self, 1, 4, 'RO', 1, int(params['SCR_PLACEHOLDER']), 1, 1, 0)
        self.RSVD.configure(self, 27, 5, 'RO', 1, 0, 1, 1, 0)


ub_param_variant_reg = uvm_object_utils(ub_param_variant_reg)


class ub_cnt_fec_uncorr_reg(UVMReg):
    def __init__(self, name="CNT_FEC_UNCORR"):
        super().__init__(name, 32, 0)
        self.COUNT = UVMRegField.type_id.create('COUNT')

    def build(self, variant=None):
        self.COUNT.configure(self, 32, 0, 'RO', 1, 0, 1, 1, 0)


ub_cnt_fec_uncorr_reg = uvm_object_utils(ub_cnt_fec_uncorr_reg)


class ub_cnt_crc_fail_reg(UVMReg):
    def __init__(self, name="CNT_CRC_FAIL"):
        super().__init__(name, 32, 0)
        self.COUNT = UVMRegField.type_id.create('COUNT')

    def build(self, variant=None):
        self.COUNT.configure(self, 32, 0, 'RO', 1, 0, 1, 1, 0)


ub_cnt_crc_fail_reg = uvm_object_utils(ub_cnt_crc_fail_reg)


class ub_cnt_retry_req_reg(UVMReg):
    def __init__(self, name="CNT_RETRY_REQ"):
        super().__init__(name, 32, 0)
        self.COUNT = UVMRegField.type_id.create('COUNT')

    def build(self, variant=None):
        self.COUNT.configure(self, 32, 0, 'RO', 1, 0, 1, 1, 0)


ub_cnt_retry_req_reg = uvm_object_utils(ub_cnt_retry_req_reg)


class ub_cnt_retry_to_reg(UVMReg):
    def __init__(self, name="CNT_RETRY_TO"):
        super().__init__(name, 32, 0)
        self.COUNT = UVMRegField.type_id.create('COUNT')

    def build(self, variant=None):
        self.COUNT.configure(self, 32, 0, 'RO', 1, 0, 1, 1, 0)


ub_cnt_retry_to_reg = uvm_object_utils(ub_cnt_retry_to_reg)


class ub_cnt_crd_of_reg(UVMReg):
    def __init__(self, name="CNT_CRD_OF"):
        super().__init__(name, 32, 0)
        self.COUNT = UVMRegField.type_id.create('COUNT')

    def build(self, variant=None):
        self.COUNT.configure(self, 32, 0, 'RO', 1, 0, 1, 1, 0)


ub_cnt_crd_of_reg = uvm_object_utils(ub_cnt_crd_of_reg)


class ub_cnt_crd_to_reg(UVMReg):
    def __init__(self, name="CNT_CRD_TO"):
        super().__init__(name, 32, 0)
        self.COUNT = UVMRegField.type_id.create('COUNT')

    def build(self, variant=None):
        self.COUNT.configure(self, 32, 0, 'RO', 1, 0, 1, 1, 0)


ub_cnt_crd_to_reg = uvm_object_utils(ub_cnt_crd_to_reg)


class ub_cnt_train_to_reg(UVMReg):
    def __init__(self, name="CNT_TRAIN_TO"):
        super().__init__(name, 32, 0)
        self.COUNT = UVMRegField.type_id.create('COUNT')

    def build(self, variant=None):
        self.COUNT.configure(self, 32, 0, 'RO', 1, 0, 1, 1, 0)


ub_cnt_train_to_reg = uvm_object_utils(ub_cnt_train_to_reg)


class ub_cnt_bad_vl_reg(UVMReg):
    def __init__(self, name="CNT_BAD_VL"):
        super().__init__(name, 32, 0)
        self.COUNT = UVMRegField.type_id.create('COUNT')

    def build(self, variant=None):
        self.COUNT.configure(self, 32, 0, 'RO', 1, 0, 1, 1, 0)


ub_cnt_bad_vl_reg = uvm_object_utils(ub_cnt_bad_vl_reg)


class ub_cnt_crd_uf_reg(UVMReg):
    def __init__(self, name="CNT_CRD_UF"):
        super().__init__(name, 32, 0)
        self.COUNT = UVMRegField.type_id.create('COUNT')

    def build(self, variant=None):
        self.COUNT.configure(self, 32, 0, 'RO', 1, 0, 1, 1, 0)


ub_cnt_crd_uf_reg = uvm_object_utils(ub_cnt_crd_uf_reg)


class ub_cnt_clr_reg(UVMReg):
    def __init__(self, name="CNT_CLR"):
        super().__init__(name, 32, 0)
        self.FEC_UNCORR = UVMRegField.type_id.create('FEC_UNCORR')
        self.CRC_FAIL = UVMRegField.type_id.create('CRC_FAIL')
        self.RETRY_REQ = UVMRegField.type_id.create('RETRY_REQ')
        self.RETRY_TO = UVMRegField.type_id.create('RETRY_TO')
        self.CRD_OF = UVMRegField.type_id.create('CRD_OF')
        self.CRD_TO = UVMRegField.type_id.create('CRD_TO')
        self.TRAIN_TO = UVMRegField.type_id.create('TRAIN_TO')
        self.BAD_VL = UVMRegField.type_id.create('BAD_VL')
        self.CRD_UF = UVMRegField.type_id.create('CRD_UF')
        self.RSVD = UVMRegField.type_id.create('RSVD')

    def build(self, variant=None):
        self.FEC_UNCORR.configure(self, 1, 0, 'WO', 1, 0, 1, 1, 0)
        self.CRC_FAIL.configure(self, 1, 1, 'WO', 1, 0, 1, 1, 0)
        self.RETRY_REQ.configure(self, 1, 2, 'WO', 1, 0, 1, 1, 0)
        self.RETRY_TO.configure(self, 1, 3, 'WO', 1, 0, 1, 1, 0)
        self.CRD_OF.configure(self, 1, 4, 'WO', 1, 0, 1, 1, 0)
        self.CRD_TO.configure(self, 1, 5, 'WO', 1, 0, 1, 1, 0)
        self.TRAIN_TO.configure(self, 1, 6, 'WO', 1, 0, 1, 1, 0)
        self.BAD_VL.configure(self, 1, 7, 'WO', 1, 0, 1, 1, 0)
        self.CRD_UF.configure(self, 1, 8, 'WO', 1, 0, 1, 1, 0)
        self.RSVD.configure(self, 23, 9, 'RO', 1, 0, 1, 1, 0)


ub_cnt_clr_reg = uvm_object_utils(ub_cnt_clr_reg)


class ub_lmsm_tmr_scale_reg(UVMReg):
    def __init__(self, name="LMSM_TMR_SCALE"):
        super().__init__(name, 32, 0)
        self.SCALE = UVMRegField.type_id.create('SCALE')
        self.RSVD = UVMRegField.type_id.create('RSVD')

    def build(self, variant=None):
        self.SCALE.configure(self, 8, 0, 'RW', 0, 0, 1, 1, 0)
        self.RSVD.configure(self, 24, 8, 'RO', 1, 0, 1, 1, 0)


ub_lmsm_tmr_scale_reg = uvm_object_utils(ub_lmsm_tmr_scale_reg)


class ub_crd_to_dis_reg(UVMReg):
    def __init__(self, name="CRD_TO_DIS"):
        super().__init__(name, 32, 0)
        self.DIS = UVMRegField.type_id.create('DIS')
        self.RSVD = UVMRegField.type_id.create('RSVD')

    def build(self, variant=None):
        self.DIS.configure(self, 1, 0, 'RW', 0, 0, 1, 1, 0)
        self.RSVD.configure(self, 31, 1, 'RO', 1, 0, 1, 1, 0)


ub_crd_to_dis_reg = uvm_object_utils(ub_crd_to_dis_reg)


class ub_pcs_tx_test_reg(UVMReg):
    def __init__(self, name="PCS_TX_TEST"):
        super().__init__(name, 32, 0)
        self.AM_IVL_SCALE = UVMRegField.type_id.create('AM_IVL_SCALE')
        self.RSVD = UVMRegField.type_id.create('RSVD')

    def build(self, variant=None):
        self.AM_IVL_SCALE.configure(self, 8, 0, 'RW', 0, 0, 1, 1, 0)
        self.RSVD.configure(self, 24, 8, 'RO', 1, 0, 1, 1, 0)


ub_pcs_tx_test_reg = uvm_object_utils(ub_pcs_tx_test_reg)


class ub_appd_port_basic_reg(UVMReg):
    def __init__(self, name="APPD_PORT_BASIC"):
        super().__init__(name, 32, 0)
        self.WINDOW = UVMRegField.type_id.create('WINDOW')

    def build(self, variant=None):
        self.WINDOW.configure(self, 32, 0, 'RW', 0, 0, 0, 1, 0)
        # WINDOW placeholder; expand from App. D.5、D.5.1–D.5.6


ub_appd_port_basic_reg = uvm_object_utils(ub_appd_port_basic_reg)


class ub_appd_link_cap_reg(UVMReg):
    def __init__(self, name="APPD_LINK_CAP"):
        super().__init__(name, 32, 0)
        self.WINDOW = UVMRegField.type_id.create('WINDOW')

    def build(self, variant=None):
        self.WINDOW.configure(self, 32, 0, 'RW', 0, 0, 0, 1, 0)
        # WINDOW placeholder; expand from App. D.6.2、D.6.2.1–D.6.2.3


ub_appd_link_cap_reg = uvm_object_utils(ub_appd_link_cap_reg)


class ub_appd_link_log_reg(UVMReg):
    def __init__(self, name="APPD_LINK_LOG"):
        super().__init__(name, 32, 0)
        self.WINDOW = UVMRegField.type_id.create('WINDOW')

    def build(self, variant=None):
        self.WINDOW.configure(self, 32, 0, 'RW', 0, 0, 0, 1, 0)
        # WINDOW placeholder; expand from App. D.6.3


ub_appd_link_log_reg = uvm_object_utils(ub_appd_link_log_reg)


class ub_appd_lmsm_st_reg(UVMReg):
    def __init__(self, name="APPD_LMSM_ST"):
        super().__init__(name, 32, 0)
        self.WINDOW = UVMRegField.type_id.create('WINDOW')

    def build(self, variant=None):
        self.WINDOW.configure(self, 32, 0, 'RW', 0, 0, 0, 1, 0)
        # WINDOW placeholder; expand from App. D.6.21


ub_appd_lmsm_st_reg = uvm_object_utils(ub_appd_lmsm_st_reg)


class ub_appd_port_err_reg(UVMReg):
    def __init__(self, name="APPD_PORT_ERR"):
        super().__init__(name, 32, 0)
        self.WINDOW = UVMRegField.type_id.create('WINDOW')

    def build(self, variant=None):
        self.WINDOW.configure(self, 32, 0, 'RW', 0, 0, 0, 1, 0)
        # WINDOW placeholder; expand from App. D.6.22


ub_appd_port_err_reg = uvm_object_utils(ub_appd_port_err_reg)


class ub_reg_block(UVMRegBlock):
    def __init__(self, name="ub_reg_block"):
        super().__init__(name)
        self.ctrl = ub_ctrl_reg.type_id.create('CTRL') if HAVE_UVM else ub_ctrl_reg('CTRL')
        self.status = ub_status_reg.type_id.create('STATUS') if HAVE_UVM else ub_status_reg('STATUS')
        self.irq_status = ub_irq_status_reg.type_id.create('IRQ_STATUS') if HAVE_UVM else ub_irq_status_reg('IRQ_STATUS')
        self.irq_mask = ub_irq_mask_reg.type_id.create('IRQ_MASK') if HAVE_UVM else ub_irq_mask_reg('IRQ_MASK')
        self.port_cna = ub_port_cna_reg.type_id.create('PORT_CNA') if HAVE_UVM else ub_port_cna_reg('PORT_CNA')
        self.param_phy = ub_param_phy_reg.type_id.create('PARAM_PHY') if HAVE_UVM else ub_param_phy_reg('PARAM_PHY')
        self.param_fec = ub_param_fec_reg.type_id.create('PARAM_FEC') if HAVE_UVM else ub_param_fec_reg('PARAM_FEC')
        self.param_dll = ub_param_dll_reg.type_id.create('PARAM_DLL') if HAVE_UVM else ub_param_dll_reg('PARAM_DLL')
        self.param_retry = ub_param_retry_reg.type_id.create('PARAM_RETRY') if HAVE_UVM else ub_param_retry_reg('PARAM_RETRY')
        self.param_crd = ub_param_crd_reg.type_id.create('PARAM_CRD') if HAVE_UVM else ub_param_crd_reg('PARAM_CRD')
        self.param_init_feature = ub_param_init_feature_reg.type_id.create('PARAM_INIT_FEATURE') if HAVE_UVM else ub_param_init_feature_reg('PARAM_INIT_FEATURE')
        self.param_init_vl = ub_param_init_vl_reg.type_id.create('PARAM_INIT_VL') if HAVE_UVM else ub_param_init_vl_reg('PARAM_INIT_VL')
        self.param_variant = ub_param_variant_reg.type_id.create('PARAM_VARIANT') if HAVE_UVM else ub_param_variant_reg('PARAM_VARIANT')
        self.cnt_fec_uncorr = ub_cnt_fec_uncorr_reg.type_id.create('CNT_FEC_UNCORR') if HAVE_UVM else ub_cnt_fec_uncorr_reg('CNT_FEC_UNCORR')
        self.cnt_crc_fail = ub_cnt_crc_fail_reg.type_id.create('CNT_CRC_FAIL') if HAVE_UVM else ub_cnt_crc_fail_reg('CNT_CRC_FAIL')
        self.cnt_retry_req = ub_cnt_retry_req_reg.type_id.create('CNT_RETRY_REQ') if HAVE_UVM else ub_cnt_retry_req_reg('CNT_RETRY_REQ')
        self.cnt_retry_to = ub_cnt_retry_to_reg.type_id.create('CNT_RETRY_TO') if HAVE_UVM else ub_cnt_retry_to_reg('CNT_RETRY_TO')
        self.cnt_crd_of = ub_cnt_crd_of_reg.type_id.create('CNT_CRD_OF') if HAVE_UVM else ub_cnt_crd_of_reg('CNT_CRD_OF')
        self.cnt_crd_to = ub_cnt_crd_to_reg.type_id.create('CNT_CRD_TO') if HAVE_UVM else ub_cnt_crd_to_reg('CNT_CRD_TO')
        self.cnt_train_to = ub_cnt_train_to_reg.type_id.create('CNT_TRAIN_TO') if HAVE_UVM else ub_cnt_train_to_reg('CNT_TRAIN_TO')
        self.cnt_bad_vl = ub_cnt_bad_vl_reg.type_id.create('CNT_BAD_VL') if HAVE_UVM else ub_cnt_bad_vl_reg('CNT_BAD_VL')
        self.cnt_crd_uf = ub_cnt_crd_uf_reg.type_id.create('CNT_CRD_UF') if HAVE_UVM else ub_cnt_crd_uf_reg('CNT_CRD_UF')
        self.cnt_clr = ub_cnt_clr_reg.type_id.create('CNT_CLR') if HAVE_UVM else ub_cnt_clr_reg('CNT_CLR')
        self.lmsm_tmr_scale = ub_lmsm_tmr_scale_reg.type_id.create('LMSM_TMR_SCALE') if HAVE_UVM else ub_lmsm_tmr_scale_reg('LMSM_TMR_SCALE')
        self.crd_to_dis = ub_crd_to_dis_reg.type_id.create('CRD_TO_DIS') if HAVE_UVM else ub_crd_to_dis_reg('CRD_TO_DIS')
        self.pcs_tx_test = ub_pcs_tx_test_reg.type_id.create('PCS_TX_TEST') if HAVE_UVM else ub_pcs_tx_test_reg('PCS_TX_TEST')
        self.appd_port_basic = ub_appd_port_basic_reg.type_id.create('APPD_PORT_BASIC') if HAVE_UVM else ub_appd_port_basic_reg('APPD_PORT_BASIC')
        self.appd_link_cap = ub_appd_link_cap_reg.type_id.create('APPD_LINK_CAP') if HAVE_UVM else ub_appd_link_cap_reg('APPD_LINK_CAP')
        self.appd_link_log = ub_appd_link_log_reg.type_id.create('APPD_LINK_LOG') if HAVE_UVM else ub_appd_link_log_reg('APPD_LINK_LOG')
        self.appd_lmsm_st = ub_appd_lmsm_st_reg.type_id.create('APPD_LMSM_ST') if HAVE_UVM else ub_appd_lmsm_st_reg('APPD_LMSM_ST')
        self.appd_port_err = ub_appd_port_err_reg.type_id.create('APPD_PORT_ERR') if HAVE_UVM else ub_appd_port_err_reg('APPD_PORT_ERR')

    def build(self, variant=None):
        self.default_map = self.create_map("default_map", 0, 4, "LITTLE_ENDIAN")
        self.ctrl.configure(self) if HAVE_UVM else None
        self.ctrl.build(variant=variant)
        self.default_map.add_reg(self.ctrl, 0x0000, 'RW')
        self.status.configure(self) if HAVE_UVM else None
        self.status.build(variant=variant)
        self.default_map.add_reg(self.status, 0x0004, 'RO')
        self.irq_status.configure(self) if HAVE_UVM else None
        self.irq_status.build(variant=variant)
        self.default_map.add_reg(self.irq_status, 0x0008, 'RW')
        self.irq_mask.configure(self) if HAVE_UVM else None
        self.irq_mask.build(variant=variant)
        self.default_map.add_reg(self.irq_mask, 0x000c, 'RW')
        self.port_cna.configure(self) if HAVE_UVM else None
        self.port_cna.build(variant=variant)
        self.default_map.add_reg(self.port_cna, 0x0010, 'RW')
        self.param_phy.configure(self) if HAVE_UVM else None
        self.param_phy.build(variant=variant)
        self.default_map.add_reg(self.param_phy, 0x0100, 'RO')
        self.param_fec.configure(self) if HAVE_UVM else None
        self.param_fec.build(variant=variant)
        self.default_map.add_reg(self.param_fec, 0x0104, 'RO')
        self.param_dll.configure(self) if HAVE_UVM else None
        self.param_dll.build(variant=variant)
        self.default_map.add_reg(self.param_dll, 0x0108, 'RO')
        self.param_retry.configure(self) if HAVE_UVM else None
        self.param_retry.build(variant=variant)
        self.default_map.add_reg(self.param_retry, 0x010c, 'RO')
        self.param_crd.configure(self) if HAVE_UVM else None
        self.param_crd.build(variant=variant)
        self.default_map.add_reg(self.param_crd, 0x0110, 'RO')
        self.param_init_feature.configure(self) if HAVE_UVM else None
        self.param_init_feature.build(variant=variant)
        self.default_map.add_reg(self.param_init_feature, 0x0114, 'RO')
        self.param_init_vl.configure(self) if HAVE_UVM else None
        self.param_init_vl.build(variant=variant)
        self.default_map.add_reg(self.param_init_vl, 0x0118, 'RO')
        self.param_variant.configure(self) if HAVE_UVM else None
        self.param_variant.build(variant=variant)
        self.default_map.add_reg(self.param_variant, 0x011c, 'RO')
        self.cnt_fec_uncorr.configure(self) if HAVE_UVM else None
        self.cnt_fec_uncorr.build(variant=variant)
        self.default_map.add_reg(self.cnt_fec_uncorr, 0x0200, 'RO')
        self.cnt_crc_fail.configure(self) if HAVE_UVM else None
        self.cnt_crc_fail.build(variant=variant)
        self.default_map.add_reg(self.cnt_crc_fail, 0x0204, 'RO')
        self.cnt_retry_req.configure(self) if HAVE_UVM else None
        self.cnt_retry_req.build(variant=variant)
        self.default_map.add_reg(self.cnt_retry_req, 0x0208, 'RO')
        self.cnt_retry_to.configure(self) if HAVE_UVM else None
        self.cnt_retry_to.build(variant=variant)
        self.default_map.add_reg(self.cnt_retry_to, 0x020c, 'RO')
        self.cnt_crd_of.configure(self) if HAVE_UVM else None
        self.cnt_crd_of.build(variant=variant)
        self.default_map.add_reg(self.cnt_crd_of, 0x0210, 'RO')
        self.cnt_crd_to.configure(self) if HAVE_UVM else None
        self.cnt_crd_to.build(variant=variant)
        self.default_map.add_reg(self.cnt_crd_to, 0x0214, 'RO')
        self.cnt_train_to.configure(self) if HAVE_UVM else None
        self.cnt_train_to.build(variant=variant)
        self.default_map.add_reg(self.cnt_train_to, 0x0218, 'RO')
        self.cnt_bad_vl.configure(self) if HAVE_UVM else None
        self.cnt_bad_vl.build(variant=variant)
        self.default_map.add_reg(self.cnt_bad_vl, 0x021c, 'RO')
        self.cnt_crd_uf.configure(self) if HAVE_UVM else None
        self.cnt_crd_uf.build(variant=variant)
        self.default_map.add_reg(self.cnt_crd_uf, 0x0220, 'RO')
        self.cnt_clr.configure(self) if HAVE_UVM else None
        self.cnt_clr.build(variant=variant)
        self.default_map.add_reg(self.cnt_clr, 0x0224, 'RW')
        self.lmsm_tmr_scale.configure(self) if HAVE_UVM else None
        self.lmsm_tmr_scale.build(variant=variant)
        self.default_map.add_reg(self.lmsm_tmr_scale, 0x0300, 'RW')
        self.crd_to_dis.configure(self) if HAVE_UVM else None
        self.crd_to_dis.build(variant=variant)
        self.default_map.add_reg(self.crd_to_dis, 0x0304, 'RW')
        self.pcs_tx_test.configure(self) if HAVE_UVM else None
        self.pcs_tx_test.build(variant=variant)
        self.default_map.add_reg(self.pcs_tx_test, 0x0308, 'RW')
        self.appd_port_basic.configure(self) if HAVE_UVM else None
        self.appd_port_basic.build(variant=variant)
        self.default_map.add_reg(self.appd_port_basic, 0x1000, 'RW')
        self.appd_link_cap.configure(self) if HAVE_UVM else None
        self.appd_link_cap.build(variant=variant)
        self.default_map.add_reg(self.appd_link_cap, 0x1100, 'RW')
        self.appd_link_log.configure(self) if HAVE_UVM else None
        self.appd_link_log.build(variant=variant)
        self.default_map.add_reg(self.appd_link_log, 0x1200, 'RW')
        self.appd_lmsm_st.configure(self) if HAVE_UVM else None
        self.appd_lmsm_st.build(variant=variant)
        self.default_map.add_reg(self.appd_lmsm_st, 0x1e00, 'RW')
        self.appd_port_err.configure(self) if HAVE_UVM else None
        self.appd_port_err.build(variant=variant)
        self.default_map.add_reg(self.appd_port_err, 0x1f00, 'RW')
        self.lock_model()


ub_reg_block = uvm_object_utils(ub_reg_block)


def create_ub_regmodel(name: str = "ub_reg_block", variant: str | None = None):
    tag = variant or DEFAULT_VARIANT
    if tag not in VARIANTS:
        raise KeyError(f"unknown CSR variant {tag!r}")
    model = ub_reg_block(name) if not HAVE_UVM else ub_reg_block.type_id.create(name)
    if HAVE_UVM:
        # type_id.create path still needs build()
        pass
    if not hasattr(model, 'default_map') or model.default_map is None:
        model.build(variant=tag)
    elif HAVE_UVM:
        model.build(variant=tag)
    model.variant = tag
    return model
