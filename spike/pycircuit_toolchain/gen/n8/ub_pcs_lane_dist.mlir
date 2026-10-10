module attributes {pyc.top = @ub_pcs_lane_dist, pyc.frontend.contract = "pycircuit"} {
func.func @ub_pcs_lane_dist(%data_in: i256) -> i256 attributes {arg_names = ["data_in"], result_names = ["data_out"], pyc.base = "ub_pcs_lane_dist", pyc.params = "{\"num_lanes\":8,\"pma_w\":32,\"sym_w\":8,\"test_hooks\":0}", pyc.kind = "module", pyc.inline = "false", pyc.value_params = [], pyc.value_param_types = [], pyc.struct.metrics = "{\"ast_node_count\":163,\"collection_count\":0,\"collection_instance_count\":0,\"estimated_inline_cost\":59,\"hardware_call_count\":2,\"instance_count\":0,\"loop_count\":0,\"module_call_count\":0,\"module_family_collection_count\":0,\"repeat_pressure\":0,\"repeated_body_clusters\":[],\"source_loc\":31,\"state_alloc_count\":0,\"state_call_count\":0}", pyc.struct.collections = "[]"} {
  %v1 = pyc.alias %data_in {pyc.name = "data_in__ub_pcs_lane_dist__L61"} : i256
  %v2 = pyc.extract %v1 {lsb = 0, msb = 7} : i256 -> i8
  %v3 = pyc.extract %v1 {lsb = 64, msb = 71} : i256 -> i8
  %v4 = pyc.extract %v1 {lsb = 128, msb = 135} : i256 -> i8
  %v5 = pyc.extract %v1 {lsb = 192, msb = 199} : i256 -> i8
  %v6 = pyc.extract %v1 {lsb = 8, msb = 15} : i256 -> i8
  %v7 = pyc.extract %v1 {lsb = 72, msb = 79} : i256 -> i8
  %v8 = pyc.extract %v1 {lsb = 136, msb = 143} : i256 -> i8
  %v9 = pyc.extract %v1 {lsb = 200, msb = 207} : i256 -> i8
  %v10 = pyc.extract %v1 {lsb = 16, msb = 23} : i256 -> i8
  %v11 = pyc.extract %v1 {lsb = 80, msb = 87} : i256 -> i8
  %v12 = pyc.extract %v1 {lsb = 144, msb = 151} : i256 -> i8
  %v13 = pyc.extract %v1 {lsb = 208, msb = 215} : i256 -> i8
  %v14 = pyc.extract %v1 {lsb = 24, msb = 31} : i256 -> i8
  %v15 = pyc.extract %v1 {lsb = 88, msb = 95} : i256 -> i8
  %v16 = pyc.extract %v1 {lsb = 152, msb = 159} : i256 -> i8
  %v17 = pyc.extract %v1 {lsb = 216, msb = 223} : i256 -> i8
  %v18 = pyc.extract %v1 {lsb = 32, msb = 39} : i256 -> i8
  %v19 = pyc.extract %v1 {lsb = 96, msb = 103} : i256 -> i8
  %v20 = pyc.extract %v1 {lsb = 160, msb = 167} : i256 -> i8
  %v21 = pyc.extract %v1 {lsb = 224, msb = 231} : i256 -> i8
  %v22 = pyc.extract %v1 {lsb = 40, msb = 47} : i256 -> i8
  %v23 = pyc.extract %v1 {lsb = 104, msb = 111} : i256 -> i8
  %v24 = pyc.extract %v1 {lsb = 168, msb = 175} : i256 -> i8
  %v25 = pyc.extract %v1 {lsb = 232, msb = 239} : i256 -> i8
  %v26 = pyc.extract %v1 {lsb = 48, msb = 55} : i256 -> i8
  %v27 = pyc.extract %v1 {lsb = 112, msb = 119} : i256 -> i8
  %v28 = pyc.extract %v1 {lsb = 176, msb = 183} : i256 -> i8
  %v29 = pyc.extract %v1 {lsb = 240, msb = 247} : i256 -> i8
  %v30 = pyc.extract %v1 {lsb = 56, msb = 63} : i256 -> i8
  %v31 = pyc.extract %v1 {lsb = 120, msb = 127} : i256 -> i8
  %v32 = pyc.extract %v1 {lsb = 184, msb = 191} : i256 -> i8
  %v33 = pyc.extract %v1 {lsb = 248, msb = 255} : i256 -> i8
  %v34 = pyc.concat (%v2, %v3, %v4, %v5, %v6, %v7, %v8, %v9, %v10, %v11, %v12, %v13, %v14, %v15, %v16, %v17, %v18, %v19, %v20, %v21, %v22, %v23, %v24, %v25, %v26, %v27, %v28, %v29, %v30, %v31, %v32, %v33) : (i8, i8, i8, i8, i8, i8, i8, i8, i8, i8, i8, i8, i8, i8, i8, i8, i8, i8, i8, i8, i8, i8, i8, i8, i8, i8, i8, i8, i8, i8, i8, i8) -> i256
  func.return %v34 : i256
}

}
