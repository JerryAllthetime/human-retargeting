import cv2
import numpy as np
from robotpy_apriltag import AprilTag, AprilTagPoseEstimator, AprilTagDetector
import pyrealsense2 as rs  # type: ignore
import contextlib
from scipy.spatial.transform import Rotation as R

@contextlib.contextmanager
def realsense_pipeline(fps: int = 30):
    """Context manager that yields a RealSense pipeline."""

    # Configure depth and color streams.
    pipeline = rs.pipeline()  # type: ignore
    config = rs.config()  # type: ignore

    pipeline_wrapper = rs.pipeline_wrapper(pipeline)  # type: ignore
    config.resolve(pipeline_wrapper)

    config.enable_stream(rs.stream.depth, rs.format.z16, fps)  # type: ignore
    config.enable_stream(rs.stream.color, rs.format.rgb8, fps)  # type: ignore

    # Start streaming.
    pipeline.start(config)

    yield pipeline

    # Close pipeline when done.
    pipeline.stop()

with realsense_pipeline() as pipeline:
    detector = AprilTagDetector()
    detector.addFamily(fam="tag36h11")
    # detector.addFamily(fam="tag25h9")
    K_path = "3rdparty/xarm6/data/camera/241122074374/K.npy"
    # camera2arm_path = "3rdparty/xarm6/data/camera/241122074374/1206_excalib_capture00/optimized_X_BaseCamera.npy"
    X_ArmCamera1_path = "3rdparty/xarm6/data/camera/241122074374/1206_excalib_capture00/optimized_X_BaseCamera.npy"
    while True:
        # Wait for a coherent pair of frames: depth and color
        frames = pipeline.wait_for_frames()
        color_frame = frames.get_color_frame()
        color_image = np.asanyarray(color_frame.get_data())
        intrinsics = np.load(K_path)
        fx, fy = intrinsics[0, 0], intrinsics[1, 1]
        cx, cy = intrinsics[0, 2], intrinsics[1, 2]
        estimator = AprilTagPoseEstimator(AprilTagPoseEstimator.Config(fx=fx, fy=fy, cx=cx, cy=cy, tagSize=0.178))
        gray = cv2.cvtColor(color_image, cv2.COLOR_BGR2GRAY)
        tags = detector.detect(gray)
        for tag in tags:
            cv2.circle(color_image, (int(tag.getCorner(0).x), int(tag.getCorner(0).y)), 4,(255,0,0), 2)
            cv2.circle(color_image, (int(tag.getCorner(1).x), int(tag.getCorner(1).y)), 4,(255,0,0), 2)
            cv2.circle(color_image, (int(tag.getCorner(2).x), int(tag.getCorner(2).y)), 4,(255,0,0), 2)
            cv2.circle(color_image, (int(tag.getCorner(3).x), int(tag.getCorner(3).y)), 4,(255,0,0), 2)
            cv2.circle(color_image, (int(tag.getCenter().x), int(tag.getCenter().y)), 4,(255,0,0), 2)
            # tag transform in Camera 2
            tag_tf3d = estimator.estimate(tag)
            tag_xyzw = ( 
                tag_tf3d.rotation().getQuaternion().X(), 
                tag_tf3d.rotation().getQuaternion().Y(), 
                tag_tf3d.rotation().getQuaternion().Z(),
                tag_tf3d.rotation().getQuaternion().W()
            )
            tag_position = (
                tag_tf3d.translation().X(),
                tag_tf3d.translation().Y(),
                tag_tf3d.translation().Z()
            )
            # print(tag_xyzw)
            X_CameraTag36 = np.eye(4)
            X_CameraTag36[:3, :3] = R.from_quat(tag_xyzw).as_matrix()
            X_CameraTag36[:3, 3] = tag_position
            X_ArmCamera = np.load(X_ArmCamera1_path) # 241122074374
            X_ArmTag36 = X_ArmCamera @ X_CameraTag36
            print(X_ArmCamera)
            # np.save("data/transform/rightarm_tag36.npy", X_ArmTag36)

        # # 显示检测结果
        cv2.imshow('capture', color_image)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break