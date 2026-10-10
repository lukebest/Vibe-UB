module attributes {pyc.top = @ub_pcs_lane_dist, pyc.frontend.contract = "pycircuit"} {
func.func @ub_pcs_lane_dist(%data_in: i128) -> i128 attributes {arg_names = ["data_in"], result_names = ["data_out"], pyc.base = "ub_pcs_lane_dist", pyc.params = "{\"num_lanes\":4,\"pma_w\":32,\"sym_w\":8,\"test_hooks\":0}", pyc.kind = "module", pyc.inline = "false", pyc.value_params = [], pyc.value_param_types = [], pyc.struct.metrics = "{\"ast_node_count\":163,\"collection_count\":0,\"collection_instance_count\":0,\"estimated_inline_cost\":59,\"hardware_call_count\":2,\"instance_count\":0,\"loop_count\":0,\"module_call_count\":0,\"module_family_collection_count\":0,\"repeat_pressure\":0,\"repeated_body_clusters\":[],\"source_loc\":31,\"state_alloc_count\":0,\"state_call_count\":0}", pyc.struct.collections = "[]"} {
  %v1 = pyc.alias %data_in {pyc.name = "data_in__ub_pcs_lane_dist__L61"} : i128
  %v2 = pyc.extract %v1 {lsb = 0, msb = 7} : i128 -> i8
  %v3 = pyc.extract %v1 {lsb = 32, msb = 39} : i128 -> i8
  %v4 = pyc.extract %v1 {lsb = 64, msb = 71} : i128 -> i8
  %v5 = pyc.extract %v1 {lsb = 96, msb = 103} : i128 -> i8
  %v6 = pyc.extract %v1 {lsb = 8, msb = 15} : i128 -> i8
  %v7 = pyc.extract %v1 {lsb = 40, msb = 47} : i128 -> i8
  %v8 = pyc.extract %v1 {lsb = 72, msb = 79} : i128 -> i8
  %v9 = pyc.extract %v1 {lsb = 104, msb = 111} : i128 -> i8
  %v10 = pyc.extract %v1 {lsb = 16, msb = 23} : i128 -> i8
  %v11 = pyc.extract %v1 {lsb = 48, msb = 55} : i128 -> i8
  %v12 = pyc.extract %v1 {lsb = 80, msb = 87} : i128 -> i8
  %v13 = pyc.extract %v1 {lsb = 112, msb = 119} : i128 -> i8
  %v14 = pyc.extract %v1 {lsb = 24, msb = 31} : i128 -> i8
  %v15 = pyc.extract %v1 {lsb = 56, msb = 63} : i128 -> i8
  %v16 = pyc.extract %v1 {lsb = 88, msb = 95} : i128 -> i8
  %v17 = pyc.extract %v1 {lsb = 120, msb = 127} : i128 -> i8
  %v18 = pyc.concat (%v2, %v3, %v4, %v5, %v6, %v7, %v8, %v9, %v10, %v11, %v12, %v13, %v14, %v15, %v16, %v17) : (i8, i8, i8, i8, i8, i8, i8, i8, i8, i8, i8, i8, i8, i8, i8, i8) -> i128
  func.return %v18 : i128
}

}
