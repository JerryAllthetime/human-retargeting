import zmq
import sys
sys.path.append('utils')
import rebocap_ws_sdk
import numpy as np
from scipy.spatial.transform import Rotation as R
from time import sleep

##### notice: manually copy these link lengths from the SDK
link22_length = 0.04 # meter
link20_length = 0.266
link18_length = 0.257

def get_link(sdk):
    tran, pose24, static_index, tp = sdk.get_last_msg()
    pose24_np = np.array(pose24)#.tobytes()

    X_RecocapWorld = np.eye(4)
    X_RecocapWorld[:3, :3] = R.from_euler("x", -90, degrees=True).as_matrix()

    X_RecocapLink16 = np.eye(4)
    X_RecocapLink16[:3, :3] = R.from_quat(pose24_np[16]).as_matrix()
    X_RecocapLink16[0, 3] = 0.5  # shoulder width 
    X_RecocapLink16[1, 3] = 1.5  # shoulder height 

    X_RecocapLink17 = np.eye(4)
    X_RecocapLink17[:3, :3] = R.from_quat(pose24_np[17]).as_matrix()
    X_RecocapLink17[0, 3] = -0.5  # shoulder width 
    X_RecocapLink17[1, 3] = 1.5  # shoulder height 

    X_Link16Link18 = np.eye(4)
    X_Link16Link18[:3, :3] = R.from_quat(pose24_np[18]).as_matrix()
    X_Link16Link18[0, 3] = 0.26  # upper arm length

    X_Link17Link19 = np.eye(4)
    X_Link17Link19[:3, :3] = R.from_quat(pose24_np[19]).as_matrix()
    X_Link17Link19[0, 3] = -0.26  # upper arm length

    X_Link18Link20 = np.eye(4)
    X_Link18Link20[:3, :3] = R.from_quat(pose24_np[20]).as_matrix()
    X_Link18Link20[0, 3] = 0.27  # lower arm length 

    X_Link19Link21 = np.eye(4)
    X_Link19Link21[:3, :3] = R.from_quat(pose24_np[21]).as_matrix()
    X_Link19Link21[0, 3] = -0.27  # lower arm length 

    X_RecocapLink20 = np.eye(4)

    X_RecocapLink18 = X_RecocapLink16 @ X_Link16Link18
    X_RecocapLink19 = X_RecocapLink17 @ X_Link17Link19

    X_RecocapLink20 = X_RecocapLink18 @ X_Link18Link20
    X_RecocapLink21 = X_RecocapLink19 @ X_Link19Link21

    X_WorldLink20 = np.linalg.inv(X_RecocapWorld) @ X_RecocapLink20
    return X_RecocapLink16,X_RecocapLink17,X_RecocapLink18,X_RecocapLink19,X_RecocapLink20,X_RecocapLink21,X_WorldLink20

counter = 0

def main():
    def print_debug_msg(self: rebocap_ws_sdk.RebocapWsSdk, trans, pose24, static_index, ts):
        global counter

        is_left_on_floor = 0 <= static_index <= 5
        is_right_on_floor = 6 <= static_index <= 11
        no_foot_on_ground = static_index < 0
        if counter % 60 == 0:
            print(f'timestamp:{ts}'
                  f'current coordinate_type: {self.coordinate_type.name}'
                  f'root position:{trans} left_on_floor:{is_left_on_floor}  right_on_floor:{is_right_on_floor}')
            for i in range(24):
                print(f'bone:{rebocap_ws_sdk.REBOCAP_JOINT_NAMES[i]} quaternion w,x,y,z is:{pose24[i]}')
            print('\n\n\n\n', flush=True)
        counter += 1

    # 姿态数据回调
    def pose_msg_callback(self: rebocap_ws_sdk.RebocapWsSdk, tran: list, pose24: list, static_index: int, ts: float):
        print(f'X_RecocapLink20: \n{X_RecocapLink20}\n')
        message = socket.recv()
        # 将 X_RecocapLink20 通过 zmq 发送
        socket.send(X_RecocapLink20.tobytes())
        pass


    # 异常断开，这里处理重连或报错
    def exception_close_callback(self: rebocap_ws_sdk.RebocapWsSdk):
        print("exception_close_callback")
    # server initialize
    context = zmq.Context()
    # # talk to client linux machine
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:5555")
    
    # rebocap initialize
    # 初始化sdk  这里可以选择控件坐标系， 控件坐标系目前已经测试过的有： 1. UE  2. Unity  3. Blender
    # 选择输出角度是否是 global 角度，默认是 local 角度【简单解释，global 角度不受父节点影响 local角度受父节点影响， local角度逐级相乘就是 global 角度
    sdk = rebocap_ws_sdk.RebocapWsSdk(coordinate_type=rebocap_ws_sdk.CoordinateType.DefaultCoordinate, use_global_rotation=False)
    # 设置姿态回调
    sdk.set_pose_msg_callback(pose_msg_callback)
    # 设置异常断开回调
    sdk.set_exception_close_callback(exception_close_callback)
    # 开始连接
    open_ret = sdk.open(7690)
    # 检查连接状态
    if open_ret == 0:
        print("连接成功")
    else:
        print("连接失败", open_ret)
        if open_ret == 1:
            print("连接状态错误")
        elif open_ret == 2:
            print("连接失败")
        elif open_ret == 3:
            print("认证失败")
        else:
            print("未知错误", open_ret)
        exit(1)
    
    memory = []

    import viser 
    sv = viser.ViserServer(port=8085)

    while True:
        global X_WorldLink20
        X_RecocapLink16,X_RecocapLink17,X_RecocapLink18,X_RecocapLink19,X_RecocapLink20,X_RecocapLink21,X_WorldLink20 = get_link(sdk)

        sv.scene.add_frame(
            "Link16", wxyz=R.from_matrix(X_RecocapLink16[:3, :3]).as_quat()[[3, 0, 1, 2]], position=X_RecocapLink16[:3, 3]
        )
        sv.scene.add_frame(
            "Link17", wxyz=R.from_matrix(X_RecocapLink17[:3, :3]).as_quat()[[3, 0, 1, 2]], position=X_RecocapLink17[:3, 3]
        )
        sv.scene.add_frame(
            "Link18", wxyz=R.from_matrix(X_RecocapLink18[:3, :3]).as_quat()[[3, 0, 1, 2]], position=X_RecocapLink18[:3, 3]
        )
        sv.scene.add_frame(
            "Link19", wxyz=R.from_matrix(X_RecocapLink19[:3, :3]).as_quat()[[3, 0, 1, 2]], position=X_RecocapLink19[:3, 3]
        )
        sv.scene.add_frame(
            "Link20", wxyz=R.from_matrix(X_RecocapLink20[:3, :3]).as_quat()[[3, 0, 1, 2]], position=X_RecocapLink20[:3, 3]
        )
        sv.scene.add_frame(
            "World_Link20", wxyz=R.from_matrix(X_WorldLink20[:3, :3]).as_quat()[[3, 0, 1, 2]], position=X_WorldLink20[:3, 3]
        )
        sv.scene.add_frame(
            "Link21", wxyz=R.from_matrix(X_RecocapLink21[:3, :3]).as_quat()[[3, 0, 1, 2]], position=X_RecocapLink21[:3, 3]
        )

        '''
        # (24, 4), xyzw
        # print(np.array(pose24))
        print(pose24_np.shape)
        # pose24_np = np.array([pose24_np[:,3],pose24_np[:,0],pose24_np[:,1],pose24_np[:,2]])
        # pose24_np = np.transpose(pose24_np)
        print(pose24_np.shape)
        link22_pose_quat = pose24_np[22]
        link20_pose_quat = pose24_np[20]
        link18_pose_quat = pose24_np[18]
        link9_pose_quat  = pose24_np[9]
        link13_pose_quat = pose24_np[13]
        link16_pose_quat = pose24_np[16]


        link22_pose_rotmat = R.from_quat(link22_pose_quat).as_matrix()
        link20_pose_rotmat = R.from_quat(link20_pose_quat).as_matrix()
        link18_pose_rotmat = R.from_quat(link18_pose_quat).as_matrix()
        link9_pose_rotmat = R.from_quat(link9_pose_quat).as_matrix()
        link13_pose_rotmat = R.from_quat(link13_pose_quat).as_matrix()
        link16_pose_rotmat = R.from_quat(link16_pose_quat).as_matrix()

        # link9_pose_rotmat[:,1] = link9_pose_rotmat[:,1] * -1.0
        # link9_pose_rotmat[:,2] = link9_pose_rotmat[:,2] * -1.0 

        # link13_pose_rotmat[:,1] = link13_pose_rotmat[:,1] * -1.0
        # link13_pose_rotmat[:,2] = link13_pose_rotmat[:,2] * -1.0 

        link18_pose_rotmat_in_link16 = link18_pose_rotmat
        link20_pose_rotmat_in_link16 = link18_pose_rotmat_in_link16.dot(link20_pose_rotmat)
        link22_pose_rotmat_in_link16 = link20_pose_rotmat_in_link16.dot(link22_pose_rotmat)
        


        link16_EE_position = [0,0,1.0]

        link18_EE_position = link16_EE_position + link18_pose_rotmat_in_link16[:,0] * link18_length 
        link20_EE_position = link18_EE_position + link20_pose_rotmat_in_link16[:,0] * link20_length
        link22_EE_position = link20_EE_position + link22_pose_rotmat_in_link16[:,0] * link22_length
        
        print(f"18: {link18_EE_position}")
        print(f"20: {link20_EE_position}")
        print(f"22: {link22_EE_position}")

        initAxis(link16_EE_position,link16_pose_rotmat)
        #initAxis(link18_EE_position,link20_pose_rotmat_in_link16)
        #initAxis(link20_EE_position,link22_pose_rotmat_in_link16)

       
        p.stepSimulation()

        # socket.send(pose24_np)
        # memory.append(pose24[20])
        # print("Sent")
        '''
    # print(f"memory:{memory}")

if __name__ == "__main__":
    main()