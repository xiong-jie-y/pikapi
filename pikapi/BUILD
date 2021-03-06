load("@pybind11_bazel//:build_defs.bzl", "pybind_extension")

pybind_extension(
    name = "graph_runner",
    srcs = [
        "graph_runner.cc",
    ],
    deps = [
        "@mediapipe//mediapipe/examples/desktop:demo_run_graph_main_gpu",
        "@mediapipe//mediapipe/graphs/hand_tracking:multi_hand_mobile_calculators",
        "@mediapipe//mediapipe/graphs/face_mesh:desktop_live_gpu_calculators",
        "//pikapi/modules/face:face_landmark_front_gpu",
        "//pikapi/modules/face:multi_hand_landmark_gpu",
        "//cpp/mp_extensions/calculators/hand_gesture:gesture_recognizer_calculator",
        "@mediapipe//mediapipe/graphs/pose_tracking:upper_body_pose_tracking_gpu_deps",
        "@mediapipe//mediapipe/framework/port:map_util",
        "@mediapipe//mediapipe/graphs/iris_tracking:iris_tracking_gpu_deps",
        "@mediapipe//mediapipe/calculators/core:packet_cloner_calculator",
    ],
)

pybind_extension(
    name = "orientation_estimator",
    srcs = [
        "orientation_estimator.cc",
    ],
    deps = [
        "@eigen_archive//:eigen",
    ],
)

pybind_extension(
    name = "landmark_utils",
    srcs = [
        "landmark_utils.cc",
    ],
    deps = [
        "@eigen_archive//:eigen",
        "@mediapipe//third_party:glog"
    ]
)


pybind_extension(
    name = "_framework_bindings",
    srcs = ["framework_bindings.cc"],
    linkopts = [
        "-lopencv_core",
        "-lopencv_imgproc",
        "-lopencv_highgui",
        "-lopencv_video",
        "-lopencv_features2d",
        "-lopencv_calib3d",
        "-lopencv_imgcodecs",
    ],
    deps = [
        "@mediapipe//mediapipe/calculators/core:pass_through_calculator",
        "@mediapipe//mediapipe/python/pybind:calculator_graph",
        "@mediapipe//mediapipe/python/pybind:image_frame",
        "@mediapipe//mediapipe/python/pybind:matrix",
        "@mediapipe//mediapipe/python/pybind:packet",
        "@mediapipe//mediapipe/python/pybind:packet_creator",
        "@mediapipe//mediapipe/python/pybind:packet_getter",
        "@mediapipe//mediapipe/python/pybind:resource_util",
        "@mediapipe//mediapipe/python/pybind:timestamp",
        "@mediapipe//mediapipe/graphs/pose_tracking:upper_body_pose_tracking_cpu_deps",
        "@mediapipe//mediapipe/graphs/face_mesh:mobile_calculators",
        "@mediapipe//mediapipe/graphs/face_mesh:desktop_live_calculators",
        "//pikapi/modules/face:face_landmark_front_cpu",
        "@mediapipe//mediapipe/graphs/face_mesh/subgraphs:face_renderer_cpu",
        "@mediapipe//mediapipe/calculators/core:constant_side_packet_calculator",
        "@mediapipe//mediapipe/calculators/core:flow_limiter_calculator",
        # "@mediapipe//mediapipe/graphs/face_mesh:desktop_live_gpu_calculators"
        "//cpp/mp_extensions/calculators:tensor_remap_calculator",
    ],
)
