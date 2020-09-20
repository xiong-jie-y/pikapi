"""This is the perception server that accept RGBD camera input 
and output data through ipc (currently zeromq) in the proto message format..
"""
import ctypes
import os
from pikapi.logging import time_measure
from threading import Thread
import threading
from numpy.core.fromnumeric import mean
from pikapi.utils.unity import realsense_vec_to_unity_char_vec
import time

from scipy.spatial.transform.rotation import Rotation
import pikapi.protos.perception_state_pb2 as ps
from pikapi.head_gestures import YesOrNoEstimator
import logging
from typing import Dict, List
import IPython
import cv2
import numpy as np

from pikapi import graph_runner

import click

import pikapi
import pikapi.mediapipe_util as pmu

import pyrealsense2 as rs
from pikapi.utils.realsense import *
from pikapi.core.camera import IMUInfo
from pikapi.recognizers.geometry.face import FaceGeometryRecognizer
from pikapi.recognizers.geometry.hand import HandGestureRecognizer
from pikapi.recognizers.geometry.body import BodyGeometryRecognizer

def visualize_image(image_buf, width, height, buf_ready, end_flag):
    target_image = np.empty((height, width, 3), dtype=np.uint8)
    while True:
        buf_ready.wait()
        target_image[:,:,:] = np.reshape(image_buf, (height, width, 3))
        buf_ready.clear()

        cv2.imshow("Frame", target_image)

        pressed_key = cv2.waitKey(2)
        if pressed_key == ord("a"):
            # import IPython; IPython.embed()
            end_flag.value = True
            break

@click.command()
@click.option('--camera-id', '-c', default=0, type=int)
@click.option('--run-name', default="general")
@click.option('--relative-depth', is_flag=True)
@click.option('--use-realsense', is_flag=True)
@click.option('--demo-mode', is_flag=True)
def cmd(camera_id, run_name, relative_depth, use_realsense, demo_mode):
    intrinsic_matrix = get_intrinsic_matrix(camera_id)

    face_recognizer = FaceGeometryRecognizer(intrinsic_matrix)
    hand_gesture_recognizer = HandGestureRecognizer(intrinsic_matrix)
    body_recognizer = BodyGeometryRecognizer(intrinsic_matrix)
    import zmq
    context = zmq.Context()
    publisher = context.socket(zmq.PUB)
    publisher.bind("tcp://127.0.0.1:9998")

    # Alignオブジェクト生成
    config = rs.config()
    #config.enable_stream(rs.stream.color, 1280, 720, rs.format.bgr8, 30)
    #config.enable_stream(rs.stream.depth, 1280, 720, rs.format.z16, 30)
    #
    config.enable_stream(rs.stream.color, 640, 360, rs.format.bgr8, 60)
    #
    config.enable_stream(rs.stream.depth, 640, 360, rs.format.z16, 60)
    config.enable_stream(rs.stream.accel, rs.format.motion_xyz32f, 250)
    config.enable_stream(rs.stream.gyro, rs.format.motion_xyz32f, 200)

    pipeline = rs.pipeline()
    profile = pipeline.start(config)
    align_to = rs.stream.color
    align = rs.align(align_to)

    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    logger = logging.getLogger(__name__)

    from pikapi.orientation_estimator import RotationEstimator

    rotation_estimator = RotationEstimator(0.98, True)

    import multiprocessing
    import multiprocessing.sharedctypes
    from multiprocessing.sharedctypes import Value, Array

    end_flag = Value(ctypes.c_bool, False)

    WIDTH = (640 * 2)
    HEIGHT = 360
    buf1 = multiprocessing.sharedctypes.RawArray('B', HEIGHT * WIDTH*3)
    # buf_dict = {"buf": buf1}
    buf_ready = multiprocessing.Event()
    buf_ready.clear()
    p1=multiprocessing.Process(target=visualize_image, args=(buf1,WIDTH, HEIGHT, buf_ready, end_flag), daemon=True)
    p1.start()

    import pikapi.logging
    last_run = time.time()
    from collections import deque
    acc_vectors = deque([])
    

    frame_times = []
    try:
        while(True):
            last_run = time.time()
            current_time = time.time()
            frames = pipeline.wait_for_frames()
            aligned_frames = align.process(frames)
            color_frame = aligned_frames.get_color_frame()
            depth_frame = aligned_frames.get_depth_frame()
            if not depth_frame or not color_frame:
                continue

            # import IPython; IPython.embed()

            # Camera pose estimation.
            acc = frames[2].as_motion_frame().get_motion_data()
            gyro = frames[3].as_motion_frame().get_motion_data()
            timestamp = frames[3].as_motion_frame().get_timestamp()
            # rotation_estimator.process_gyro(
            #     np.array([gyro.x, gyro.y, gyro.z]), timestamp)
            # rotation_estimator.process_accel(np.array([acc.x, acc.y, acc.z]))
            # theta = rotation_estimator.get_theta()
            acc_vectors.append(np.array([acc.x, acc.y, acc.z]))
            if len(acc_vectors) > 200:
                acc_vectors.popleft()
            acc = np.mean(acc_vectors, axis=0)
            imu_info = IMUInfo(acc)

            # print(acc)
            # print(np.array([acc.x, acc.y, acc.z]))

            # print(theta)

            frame = np.asanyarray(color_frame.get_data())
            depth_image = np.asanyarray(depth_frame.get_data())

            # ret, frame = cap.read()
            # if frame is None:
            #     break

            # import IPython; IPython.embed()
            # frame[depth_image > 2500] = 0
            # frame[depth_image == 0] = 0
            # depth_image[depth_image > 2500] = 0
            # depth_image[depth_image == 0] = 0

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Prepare depth image for dispaly.
            depth_image_cp = np.copy(depth_image)
            depth_image_cp[depth_image_cp > 2500] = 0
            depth_image_cp[depth_image_cp == 0] = 0
            depth_colored = cv2.applyColorMap(cv2.convertScaleAbs(
                depth_image_cp, alpha=0.08), cv2.COLORMAP_JET)
            # depth_colored = cv2.convertScaleAbs(depth_image, alpha=0.08)

            if demo_mode:
                target_image = depth_colored
            else:
                target_image = frame
            
            run_on_threads = False
            if run_on_threads:
                result = {}
                face_th = threading.Thread(target=face_recognizer.get_state, \
                        args=(gray, depth_image, target_image, imu_info), kwargs={"result": result})
                face_th.start()
                hand_th = threading.Thread(target=hand_gesture_recognizer.get_state, \
                        args=(gray, depth_image, target_image), kwargs={"result": result})
                hand_th.start()
                body_th = threading.Thread(target=body_recognizer.get_state, \
                        args=(gray, depth_image, target_image), kwargs={"result": result})
                body_th.start()

                face_th.join()
                hand_th.join()
                body_th.join()

                face_state = result['face_state']
                hand_states = result['hand_states']
                body_state = result['body_state']
            else:
                face_state = face_recognizer.get_face_state(
                    gray, depth_image, target_image, imu_info)

                hand_states = \
                    hand_gesture_recognizer.get_hand_states(
                        gray, depth_image, target_image)
                body_state = \
                    body_recognizer.get_body_state(gray, depth_image, target_image)
                # print(pose_landmark_list)

            interval = time.time() - last_run
            estimated_fps = 1.0 / interval
            # print(estimated_fps)
            frame_times.append(interval * 1000)
            cv2.putText(target_image, f"Frame Time{interval * 1000}[ms]", (10, 50), cv2.FONT_HERSHEY_PLAIN, 2.0,
                        (255, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(target_image, f"FPS: {estimated_fps}", (10, 25), cv2.FONT_HERSHEY_PLAIN, 2.0,
                        (255, 255, 255), 1, cv2.LINE_AA)

            if not demo_mode:
                with time_measure("Create Stack"):
                    target_image = np.hstack((target_image, depth_colored))

            
            with time_measure("CopyImage"):
                buf_ready.clear()
                memoryview(buf1).cast('B')[:] = memoryview(target_image).cast('B')[:]
                # buf_dict["buf"] = target_image
                # memoryview(buf1).cast('B')[:] = target_image
                buf_ready.set()
            # print("CopyImage", np.mean(pikapi.logging.time_measure_result["CopyImage"]))
            # print("CreateStack", np.mean(pikapi.logging.time_measure_result["Create Stack"]))

            # if face_recognizer.last_face_image is not None:
            #     cv2.imshow("Face Image", face_recognizer.last_face_image)
            last_run = time.time()

            # print(effective_gesture_texts)
            perc_state = ps.PerceptionState(
                people=[
                    ps.Person(
                        face=face_state,
                        hands=hand_states,
                        body=body_state,
                    )
                ]
            )

            # print(perc_state)
            data = ["PerceptionState".encode('utf-8'), perc_state.SerializeToString()]
            publisher.send_multipart(data)

            if end_flag.value:
                import json
                perf_dict = dict(pikapi.logging.time_measure_result)
                perf_dict['frame_ms'] = frame_times
                json.dump(perf_dict, open(
                    f"{run_name}_performance.json", "w"))
                break

    finally:
        # ストリーミング停止
        pipeline.stop()


def main():
    cmd()


if __name__ == "__main__":
    main()
